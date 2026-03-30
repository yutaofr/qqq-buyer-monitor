import pandas as pd
import numpy as np
from src.engine.v11.conductor import V11Conductor
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def run_performance_audit(start_date, end_date, window_label):
    conductor = V11Conductor()
    
    # Load data
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    price_df = pd.read_csv("data/qqq_history_cache.csv", parse_dates=["Date"]).set_index("Date")
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_convert(None).normalize()
    
    # Filter for window
    mask = (macro_df.index >= start_date) & (macro_df.index <= end_date)
    window_macro = macro_df.loc[mask]
    
    dates = window_macro.index.sort_values()
    results = []
    
    current_beta = 1.0 # Initial state
    
    for date in dates:
        # Get T-0 data for this date
        t0_data = macro_df.loc[:date].iloc[-252:] # Rolling window for seeder
        
        # Inference
        signal = conductor.daily_run(t0_data)
        
        results.append({
            "date": date,
            "price": price_df.loc[date, "Close"] if date in price_df.index else np.nan,
            "target_beta": signal["target_beta"],
            "regime": signal["probabilities"], # Store full dist for debug
            "lock": signal["signal"]["lock_active"],
            "entropy": signal["entropy"]
        })
        
    df = pd.DataFrame(results).set_index("date").dropna(subset=["price"])
    df["ret"] = df["price"].pct_change()
    df["strat_ret"] = df["ret"] * df["target_beta"].shift(1)
    
    # Cumulative Nav
    df["bh_nav"] = (1 + df["ret"].fillna(0)).cumprod()
    df["strat_nav"] = (1 + df["strat_ret"].fillna(0)).cumprod()
    
    # Metrics
    bh_mdd = (df["bh_nav"] / df["bh_nav"].expanding().max() - 1).min()
    strat_mdd = (df["strat_nav"] / df["strat_nav"].expanding().max() - 1).min()
    
    # Tipping points
    peak_date = df["price"].idxmax()
    bottom_date = df["price"].idxmin()
    
    beta_at_peak = df.loc[peak_date, "target_beta"]
    beta_at_bottom = df.loc[bottom_date, "target_beta"]
    
    print(f"\nAUDIT WINDOW: {window_label} ({start_date} -> {end_date})")
    print("-" * 50)
    print(f"Max Drawdown (B&H): {bh_mdd:.2%}")
    print(f"Max Drawdown (V11): {strat_mdd:.2%}")
    print(f"Beta at Price Peak ({peak_date.date()}): {beta_at_peak:.2f}")
    print(f"Beta at Price Bottom ({bottom_date.date()}): {beta_at_bottom:.2f}")
    
    # Precision of recovery: How many days after bottom did Beta increase?
    post_bottom = df.loc[bottom_date:]
    recovery_trigger = post_bottom[post_bottom["target_beta"] > beta_at_bottom]
    if not recovery_trigger.empty:
        recovery_date = recovery_trigger.index[0]
        delay = (recovery_date - bottom_date).days
        print(f"Recovery Trigger Delay: {delay} days (Beta -> {recovery_trigger.iloc[0]['target_beta']:.2f})")
    
    return df

def main():
    # 1. 2020 COVID
    run_performance_audit("2020-01-01", "2020-06-30", "2020 COVID CRASH")
    
    # 2. 2022 Inflation
    run_performance_audit("2022-01-01", "2022-12-31", "2022 INFLATION BEAR")
    
    # 3. 2025/04 Recent Stress
    run_performance_audit("2025-01-01", "2025-05-30", "2025/04 RECENT STRESS")

if __name__ == "__main__":
    main()
