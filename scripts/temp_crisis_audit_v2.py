import pandas as pd
import numpy as np
from src.engine.v11.conductor import V11Conductor
import logging
from datetime import datetime

logging.basicConfig(level=logging.ERROR) # Lower log level to avoid spam

def run_performance_audit(start_date, end_date, window_label):
    conductor = V11Conductor()
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    price_df = pd.read_csv("data/qqq_history_cache.csv", parse_dates=["Date"]).set_index("Date")
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_convert(None).normalize()
    
    mask = (macro_df.index >= start_date) & (macro_df.index <= end_date)
    window_macro = macro_df.loc[mask]
    dates = window_macro.index.sort_values()
    results = []
    
    for date in dates:
        t0_data = macro_df.loc[:date].iloc[-252:]
        signal = conductor.daily_run(t0_data)
        results.append({
            "date": date,
            "price": price_df.loc[date, "Close"] if date in price_df.index else np.nan,
            "target_beta": signal["target_beta"],
        })
        
    df = pd.DataFrame(results).set_index("date").dropna(subset=["price"])
    df["ret"] = df["price"].pct_change()
    df["strat_ret"] = df["ret"] * df["target_beta"].shift(1)
    df["bh_nav"] = (1 + df["ret"].fillna(0)).cumprod()
    df["strat_nav"] = (1 + df["strat_ret"].fillna(0)).cumprod()
    
    bh_mdd = (df["bh_nav"] / df["bh_nav"].expanding().max() - 1).min()
    strat_mdd = (df["strat_nav"] / df["strat_nav"].expanding().max() - 1).min()
    peak_date = df["price"].idxmax()
    bottom_date = df["price"].idxmin()
    beta_at_peak = df.loc[peak_date, "target_beta"]
    beta_at_bottom = df.loc[bottom_date, "target_beta"]
    
    print(f"\nAUDIT WINDOW: {window_label}")
    print(f"MDD (B&H): {bh_mdd:.2%}, MDD (V11): {strat_mdd:.2%}")
    print(f"Beta at Peak ({peak_date.date()}): {beta_at_peak:.2f}")
    print(f"Beta at Bottom ({bottom_date.date()}): {beta_at_bottom:.2f}")

if __name__ == "__main__":
    import sys
    window = sys.argv[1]
    if window == "2020":
        run_performance_audit("2020-01-01", "2020-06-30", "2020 COVID CRASH")
    elif window == "2022":
        run_performance_audit("2022-01-01", "2022-12-31", "2022 INFLATION BEAR")
    elif window == "2025":
        run_performance_audit("2025-01-01", "2025-05-30", "2025/04 RECENT STRESS")
