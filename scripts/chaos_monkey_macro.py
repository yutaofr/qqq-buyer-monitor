"""Chaos Monkey script for macro data corruption tests."""
import pandas as pd
import numpy as np
import argparse
from pathlib import Path

def apply_chaos(df: pd.DataFrame, drop_prob: float = 0.05, delay_prob: float = 0.10, max_delay: int = 30) -> pd.DataFrame:
    """
    Apply chaos to a macro dataset to test system robustness.
    - drop_prob: Probability of losing an observation completely.
    - delay_prob: Probability of a publication delay.
    - max_delay: Maximum days of delay.
    """
    corrupted = df.copy()
    
    # 1. Random drops (PIT safety test)
    # We drop the actual value but keep the row if it's a combined dataset, 
    # simulating a missing component.
    mask_drop = np.random.rand(len(corrupted)) < drop_prob
    # Assuming columns that aren't dates are targets
    value_cols = [c for c in corrupted.columns if c not in ["observation_date", "effective_date", "published_date"]]
    for col in value_cols:
        corrupted.loc[mask_drop, col] = np.nan
        
    # 2. Random delays (published_date shift)
    if "published_date" in corrupted.columns:
        mask_delay = np.random.rand(len(corrupted)) < delay_prob
        delays = np.random.randint(10, max_delay + 1, size=mask_delay.sum())
        corrupted.loc[mask_delay, "published_date"] = corrupted.loc[mask_delay, "published_date"] + pd.to_timedelta(delays, unit='D')
        
    return corrupted

def main():
    parser = argparse.ArgumentParser(description="Macro Chaos Monkey")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--drop-prob", type=float, default=0.05)
    parser.add_argument("--delay-prob", type=float, default=0.10)
    args = parser.parse_args()
    
    df = pd.read_csv(args.input, parse_dates=["observation_date"])
    if "published_date" in df.columns:
        df["published_date"] = pd.to_datetime(df["published_date"])
        
    corrupted = apply_chaos(df, drop_prob=args.drop_prob, delay_prob=args.delay_prob)
    corrupted.to_csv(args.output, index=False)
    print(f"Chaos applied. Dropped ~{args.drop_prob*100}%, Delayed ~{args.delay_prob*100}%")

if __name__ == "__main__":
    main()
