
import pandas as pd
import numpy as np
from pathlib import Path
from src.research.signal_expectations import _expected_target_beta

def verify():
    print("--- V11 Data Integrity Verification ---")
    
    # 1. Load Library
    lib_path = Path("data/v11_feature_library.csv")
    if not lib_path.exists():
        print(f"ERROR: {lib_path} missing")
        return
    
    df = pd.read_csv(lib_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date")
    
    # 2. Check Date Range
    start_date = df["observation_date"].min()
    end_date = df["observation_date"].max()
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    if start_date.year < 1990:
        print(f"CRITICAL ERROR: Date alignment issue detected (Found year {start_date.year})")
    
    # 3. Check Price & Alignment
    print("\nPrice Snapshot (First 5 rows):")
    print(df[["observation_date", "qqq_close"]].head())
    print("\nPrice Snapshot (Last 5 rows):")
    print(df[["observation_date", "qqq_close"]].tail())
    
    if (df["qqq_close"] <= 0).any():
        print("ERROR: Non-positive prices found")

    # 4. Simulate Expected Beta (Macro-Cycle Logic)
    # Features for Beta calculation
    df["ma200"] = df["qqq_close"].rolling(200, min_periods=1).mean()
    df["price_vs_ma200"] = (df["qqq_close"] / df["ma200"]) - 1.0
    df["rolling_drawdown"] = (df["qqq_close"] / df["qqq_close"].expanding().max()) - 1.0
    
    test_betas = []
    for _, row in df.iterrows():
        beta = _expected_target_beta(
            credit_spread=float(row.get("credit_spread_bps", 400.0)),
            credit_accel=float(row.get("credit_acceleration_pct_10d", 0.0)),
            liquidity_roc=float(row.get("liquidity_roc_pct_4w", 0.0)),
            funding_stress=bool(row.get("funding_stress_flag", False)),
            erp=3.5, 
            breadth=float(row.get("breadth_proxy", 0.5)),
            price_vs_ma200=float(row.get("price_vs_ma200", 0.0)),
            rolling_drawdown=abs(row["rolling_drawdown"]),
        )
        test_betas.append(beta)
    
    df["test_expected_beta"] = test_betas
    
    # 5. Check Beta Variance
    unique_betas = df["test_expected_beta"].unique()
    print(f"\nUnique Expected Betas detected: {unique_betas}")
    if len(unique_betas) <= 1:
        print("ERROR: Expected Beta is constant!")
    
    # 6. Check specifically around 2020 crash for the shift
    crash_window = df[(df["observation_date"] >= "2020-02-20") & (df["observation_date"] <= "2020-03-31")]
    print("\n2020 Crash Expected Beta Transition:")
    print(crash_window[["observation_date", "qqq_close", "test_expected_beta"]].head(15))

if __name__ == "__main__":
    verify()
