"""
M4 Backtesting script for QQQ Buy-Signal Monitor.

Runs the Tier-1 signals over historical data (2022-2025) to evaluate
if the "TRIGGERED" and "WATCH" moments align with actual market bottoms.
Since historical options Open Interest / Gamma data is rarely available
for free, this backtest focuses purely on the Tier-1 (Spot + Sentiment) engine.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from src.models import MarketData, Signal, Tier2Result
from src.engine.tier1 import calculate_tier1
from src.engine.aggregator import aggregate

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
START_DATE = "1999-03-10"  # QQQ inception date
END_DATE = date.today().strftime("%Y-%m-%d")



def run_backtest() -> None:
    print(f"Fetching historical data from {START_DATE} to {END_DATE}...")

    # Fetch QQQ price baseline
    qqq = yf.Ticker("QQQ").history(start=START_DATE, end=END_DATE)
    if qqq.empty:
        print("Failed to fetch QQQ historical data.")
        return

    # Fetch VIX
    vix = yf.Ticker("^VIX").history(start=START_DATE, end=END_DATE)
    
    # We cannot easily fetch historical Fear & Greed, so we'll proxy it using VIX
    # High VIX = Fear. For this backtest we map VIX to a synthetic F&G score.
    # VIX 30 -> F&G 10 (Extreme Fear)
    # VIX 15 -> F&G 50 (Neutral)
    
    # Breadth proxy (using QQQ distance from 50MA as done in breadth.py)
    
    print("Pre-computing moving averages and proxies...")
    df = pd.DataFrame(index=qqq.index)
    df["Close"] = qqq["Close"]
    df["MA200"] = df["Close"].rolling(200, min_periods=50).mean()
    df["MA50"] = df["Close"].rolling(50, min_periods=20).mean()
    df["High52w"] = df["Close"].rolling(252, min_periods=50).max()
    
    # Forward fill VIX to match QQQ dates. VIX index might not match QQQ exactly due to holidays
    # Ensure they share the timezone-naive date format for alignment
    qqq_dates = [d.date() for d in qqq.index]
    vix_dates = [d.date() for d in vix.index]
    
    # Create a clean VIX series aligned by date
    vix_clean = pd.Series(vix["Close"].values, index=pd.to_datetime(vix_dates))
    df.index = pd.to_datetime(qqq_dates)
    
    df["VIX"] = vix_clean.reindex(df.index).ffill().bfill() # bfill handles any NaN at the very start
    df["Volume"] = pd.Series(qqq["Volume"].values, index=df.index)

    signals = []
    prices = []
    dates = []
    tier1_scores = []
    
    print(f"Simulating daily signals for {len(df)} trading days...")
    
    for dt, row in df.iterrows():
        # Need enough history to have valid MA200 and High52w
        if pd.isna(row["MA200"]) or pd.isna(row["High52w"]) or pd.isna(row["VIX"]):
            continue
            
        # Synthetic Fear & Greed from VIX (for backtesting only)
        # VIX > 30 -> F&G < 20 (Fear)
        # VIX < 15 -> F&G > 60 (Greed)
        vix_val = float(row["VIX"])
        fg_synthetic = max(0.0, min(100.0, 100.0 - (vix_val - 10) * 4))
        
        # Synthetic breadth pct_above_50d from QQQ vs MA50
        dev_50 = (row["Close"] - row["MA50"]) / row["MA50"]
        if pd.isna(dev_50):
            pct_50 = 0.5
        elif dev_50 > 0.05: pct_50 = 0.65
        elif dev_50 < -0.05: pct_50 = 0.20
        else: pct_50 = 0.40
        
        # Build MarketData
        lookback_df_60 = df[df.index <= dt].tail(60).copy()
        
        mdata = MarketData(
            date=dt.date(),
            price=float(row["Close"]),
            ma200=float(row["MA200"]),
            high_52w=float(row["High52w"]),
            vix=vix_val,
            fear_greed=int(fg_synthetic),
            adv_dec_ratio=0.5, # Neutral fallback for breadth ratio in backtest
            pct_above_50d=pct_50,
            options_df=None, # Tier 2 is disabled for historical backtest due to lack of historical option metrics
            credit_spread=None,
            forward_pe=None,
            history_window=pd.DataFrame({
                "price": lookback_df_60["Close"],
                "vix": lookback_df_60["VIX"],
                "breadth": 0.5 
            })
        )
        
        t1 = calculate_tier1(mdata)
        
        # --- Synthetic Tier 2: Volume Profile Put Wall ---
        # Look back 21 trading days (approx 1 month)
        lookback_df = df[df.index <= dt].tail(21)
        synthetic_put_wall = None
        support_broken = False
        t2_adj = 0
        
        if len(lookback_df) == 21:
            # Create price bins (e.g. $5 wide) and sum volume
            # We only look for support *below* the current price
            current_price = row["Close"]
            # Find the max volume node in the recent past that is lower than current price
            # or if current price is breaking through the max node.
            
            # Simple VPVR: bin the closing prices
            bins = pd.cut(lookback_df["Close"], bins=15)
            vpvr = lookback_df.groupby(bins, observed=False)["Volume"].sum()
            
            if not vpvr.empty:
                # Find the bin with the highest volume (Point of Control)
                poc_bin = vpvr.idxmax()
                poc_price = poc_bin.mid
                
                synthetic_put_wall = float(poc_price)
                
                # If current price breaks significantly below the Point of Control
                # treat it as support broken (Put Wall breached)
                dist_pct = (current_price - synthetic_put_wall) / synthetic_put_wall
                if dist_pct < -0.01: # 1% penetration
                    support_broken = True
                    t2_adj = -30
        
        t2 = Tier2Result(
            adjustment=t2_adj,
            put_wall=synthetic_put_wall,
            call_wall=None,
            gamma_flip=None,
            support_confirmed=False,
            support_broken=support_broken,
            upside_open=False,
            gamma_positive=False,
            gamma_source="vpvr_proxy",
            put_wall_distance_pct=None,
            call_wall_distance_pct=None
        )
        
        # Aggregate
        result = aggregate(dt.date(), row["Close"], t1, t2)
        sig = result.signal
            
        dates.append(dt)
        prices.append(row["Close"])
        signals.append((sig, result.final_score))
        tier1_scores.append(t1.score)

    print("\n--- Backtest Summary ---")
    
    triggered_dates = [d for d, s in zip(dates, signals) if s[0] == Signal.TRIGGERED]
    watch_dates = [d for d, s in zip(dates, signals) if s[0] == Signal.WATCH]
    
    print(f"Total trading days evaluated: {len(dates)}")
    print(f"Days in TRIGGERED state: {len(triggered_dates)} ({(len(triggered_dates)/len(dates))*100:.1f}%)")
    print(f"Days in WATCH state: {len(watch_dates)} ({(len(watch_dates)/len(dates))*100:.1f}%)")
    print(f"Days in NO_SIGNAL state: {len(dates) - len(triggered_dates) - len(watch_dates)}")
    
    # Calculate how many TRIGGERED were vetoed down to WATCH
    vetoed = 0
    for s, t1_score in zip(signals, tier1_scores):
        if t1_score >= 70 and s[0] != Signal.TRIGGERED:
            vetoed += 1
    print(f"Days TRIGGERED but VETOED by Tier-2 (Support Broken): {vetoed}")
    
    # Detailed output for TRIGGERED clusters
    print("\nTRIGGERED events (clustered by month):")
    clusters = {}
    for d in triggered_dates:
        month = d.strftime("%Y-%m")
        clusters[month] = clusters.get(month, 0) + 1
        
    for month, count in sorted(clusters.items()):
        print(f"  {month}: {count} days")

    # Plot
    plt.figure(figsize=(14, 7))
    plt.plot(dates, prices, label="QQQ Price", color="black", linewidth=1.5)
    
    # Mark WATCH signals
    watch_x = [d for d, s in zip(dates, signals) if s[0] == Signal.WATCH]
    watch_y = [p for p, s in zip(prices, signals) if s[0] == Signal.WATCH]
    plt.scatter(watch_x, watch_y, color="orange", label="WATCH (Score >= 40)", alpha=0.5, s=20)
    
    # Mark TRIGGERED signals
    trigger_x = [d for d, s in zip(dates, signals) if s[0] == Signal.TRIGGERED]
    trigger_y = [p for p, s in zip(prices, signals) if s[0] == Signal.TRIGGERED]
    plt.scatter(trigger_x, trigger_y, color="green", label="TRIGGERED", marker="^", s=80, zorder=5)

    plt.title("QQQ Buy-Signal Monitor Backtest (1999-2025, with synthetic Tier-2 VPVR Put Wall)")
    plt.xlabel("Date")
    plt.ylabel("QQQ Price")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plot_path = "data/backtest_results_tier2.png"
    plt.savefig(plot_path)
    print(f"\nSaved backtest chart to {plot_path}")

if __name__ == "__main__":
    run_backtest()
