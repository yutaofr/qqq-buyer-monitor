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
from src.engine.tier2 import evaluate_tier2_rules
from src.engine.aggregator import aggregate
from src.utils.stats import calculate_zscore

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
    
    # Fetch MOVE Index
    move = yf.Ticker("^MOVE").history(start=START_DATE, end=END_DATE)
    
    # Fetch XLP for Sector Rotation
    xlp = yf.Ticker("XLP").history(start=START_DATE, end=END_DATE)
    
    # Fetch WALCL from FRED (proxy for Liquidity)
    from src.collector.macro import fetch_fred_csv
    walcl_df = fetch_fred_csv("WALCL")
    
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
    df.index = pd.to_datetime(qqq_dates)
    vix_dates = [d.date() for d in vix.index]
    
    # Create a clean VIX series aligned by date
    vix_clean = pd.Series(vix["Close"].values, index=pd.to_datetime(vix_dates))
    df["VIX"] = vix_clean.reindex(df.index).ffill().bfill() # bfill handles any NaN at the very start
    df["Volume"] = pd.Series(qqq["Volume"].values, index=df.index)
    
    # MOVE index alignment
    move_clean = pd.Series(move["Close"].values, index=pd.to_datetime([d.date() for d in move.index]))
    df["MOVE"] = move_clean.reindex(df.index).ffill()
    
    # XLP alignment
    xlp_clean = pd.Series(xlp["Close"].values, index=pd.to_datetime([d.date() for d in xlp.index]))
    df["XLP"] = xlp_clean.reindex(df.index).ffill()
    # Sector Rotation (XLP/QQQ 20D)
    df["XLP_QQQ_Ratio"] = df["XLP"] / df["Close"]
    df["SectorRotation"] = df["XLP_QQQ_Ratio"].pct_change(20) * 100
    
    # WALCL alignment and ROC
    if walcl_df is not None and not walcl_df.empty:
        walcl_clean = pd.Series(walcl_df["WALCL"].values, index=pd.to_datetime(walcl_df.index))
        df["WALCL"] = walcl_clean.reindex(df.index).ffill()
        # 4-week ROC (20 trading days roughly)
        df["LiqROC"] = df["WALCL"].pct_change(20) * 100
    else:
        df["WALCL"] = 0.0
        df["LiqROC"] = 0.0
    
    # Pre-calculate rolling drawdowns for Z-score analysis
    peaks = df["Close"].expanding().max()
    df["Drawdown"] = (peaks - df["Close"]) / peaks
    
    # Add OHLCV for MFI
    df["High"] = qqq["High"].values
    df["Low"] = qqq["Low"].values

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
        lookback_df_120 = df[df.index <= dt].tail(120).copy()
        
        # Calculate v4.0 Z-Scores
        vix_zs = calculate_zscore(vix_val, lookback_df_120["VIX"])
        dd_zs = calculate_zscore(float(row["Drawdown"]), lookback_df_120["Drawdown"])
        
        mdata = MarketData(
            date=dt.date(),
            price=float(row["Close"]),
            ma200=float(row["MA200"]),
            high_52w=float(row["High52w"]),
            vix=vix_val,
            fear_greed=int(fg_synthetic),
            adv_dec_ratio=0.5, # Neutral fallback for breadth ratio in backtest
            pct_above_50d=pct_50,
            options_df=None, # Tier 2 is disabled for historical backtest
            credit_spread=None,
            forward_pe=None,
            history_window=pd.DataFrame({
                "price": lookback_df_120["Close"],
                "vix": lookback_df_120["VIX"],
                "breadth": 0.5 
            }),
            vix_zscore=vix_zs,
            drawdown_zscore=dd_zs,
            net_liquidity=float(row.get("WALCL", 0)) / 1000.0, # Scaled to Billions for realism
            liquidity_roc=float(row.get("LiqROC", 0)),
            move_index=float(row.get("MOVE", 0)) if not pd.isna(row.get("MOVE")) else None,
            ohlcv_history=lookback_df_120,
            sector_rotation=float(row.get("SectorRotation", 0))
        )
        
        t1 = calculate_tier1(mdata)
        
        # --- Synthetic Tier 2: Volume Profile Put Wall ---
        # Look back 21 trading days (approx 1 month)
        lookback_df = df[df.index <= dt].tail(21)
        synthetic_put_wall = None
        
        if len(lookback_df) == 21:
            # Create price bins (e.g. $5 wide) and sum volume
            # We only look for support *below* the current price
            
            # Simple VPVR: bin the closing prices
            bins = pd.cut(lookback_df["Close"], bins=15)
            vpvr = lookback_df.groupby(bins, observed=False)["Volume"].sum()
            
            if not vpvr.empty:
                # Find the bin with the highest volume (Point of Control)
                poc_bin = vpvr.idxmax()
                poc_price = poc_bin.mid
                synthetic_put_wall = float(poc_price)
        
        t2 = evaluate_tier2_rules(
            price=row["Close"],
            put_wall=synthetic_put_wall,
            call_wall=None,
            gamma_flip=None,
            gamma_source="vpvr_proxy"
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
    
    vetoed = 0
    for s, t1_score in zip(signals, tier1_scores):
        if t1_score >= 70 and s[0] != Signal.TRIGGERED:
            vetoed += 1
    print(f"Days TRIGGERED but VETOED by Tier-2 (Support Broken): {vetoed}")
    
    print("\n--- Missed Opportunities Analysis ---")
    # Identify local market bottoms (lowest price in +/- 20 trading days) with at least 10% drawdown
    df["LocalMin"] = df["Close"] == df["Close"].rolling(41, center=True, min_periods=1).min()
    df["SignificantDrawdown"] = (df["High52w"] - df["Close"]) / df["High52w"] >= 0.10
    bottom_days = []
    for d, row in df.iterrows():
        if row["LocalMin"] and row["SignificantDrawdown"] and d in dates:
            bottom_days.append(d)
            
    missed_opportunities = []
    for bottom_date in bottom_days:
        try:
            idx = dates.index(bottom_date)
            # Look at a window of +/- 10 trading days around the actual bottom
            start_idx = max(0, idx - 10)
            end_idx = min(len(dates), idx + 11)
            window_signals = [s[0] for s in signals[start_idx:end_idx]]
            
            # If neither TRIGGERED nor WATCH was generated in this window, it's a completely missed opportunity
            if Signal.TRIGGERED not in window_signals and Signal.WATCH not in window_signals:
                missed_opportunities.append(bottom_date)
        except ValueError:
            pass
            
    print(f"Significant Market Bottoms (>10% drawdown): {len(bottom_days)}")
    print(f"Missed Opportunities (No WATCH/TRIGGERED within ±10 days): {len(missed_opportunities)}")
    if missed_opportunities:
        print("Missed opportunity dates:")
        for mo in missed_opportunities:
            actual_price = df.loc[pd.to_datetime(mo), "Close"]
            print(f"  {mo.strftime('%Y-%m-%d')} (Price: ${actual_price:.2f})")
    
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
