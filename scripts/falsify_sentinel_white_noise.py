"""V12.1 Falsification Test: Real Data vs. White Noise."""
import pandas as pd
import numpy as np
import os
from src.backtest import run_v11_audit

def run_falsification():
    dataset_path = "data/macro_historical_dump.csv"
    regime_path = "data/v11_poc_phase1_results.csv"
    
    if not os.path.exists(dataset_path) or not os.path.exists(regime_path):
        print("Required data files missing. Skipping test.")
        return

    # 1. Run with REAL data
    print("\n--- Running Audit with REAL Data ---")
    real_summary = run_v11_audit(
        dataset_path=dataset_path,
        regime_path=regime_path,
        evaluation_start="2020-01-01", # Focus on high-volatility period
        artifact_dir="artifacts/falsification/real"
    )
    real_ir = real_summary["sentinel_audit"]["mean_diff"] # Alpha IR from L4
    
    # 2. Run with WHITE NOISE Volume
    print("\n--- Running Audit with WHITE NOISE Volume ---")
    # Load QQQ history to inject noise
    cache_path = "data/qqq_history_cache.csv"
    price_df = pd.read_csv(cache_path, index_col=0)
    
    noise_df = price_df.copy()
    # Replace Volume with same-mean, same-std white noise
    vol_mean = price_df["Volume"].mean()
    vol_std = price_df["Volume"].std()
    noise_df["Volume"] = np.random.normal(vol_mean, vol_std, size=len(price_df))
    noise_df["Volume"] = noise_df["Volume"].clip(lower=1000) # Keep physical
    
    noise_cache_path = "data/qqq_history_noise.csv"
    noise_df.to_csv(noise_cache_path)
    
    # We need to temporarily hack _load_price_history or pass the frame
    # For a clean test, we'll patch the cache path in backtest
    import src.backtest as bt
    original_cache = "data/qqq_history_cache.csv"
    
    try:
        # Patch the cache path used in run_v11_audit
        # This is a bit hacky but keeps the backtest script intact
        # We need to overwrite the file since it's hardcoded in the function call
        os.rename(original_cache, "data/qqq_history_real_backup.csv")
        os.rename(noise_cache_path, original_cache)
        
        noise_summary = run_v11_audit(
            dataset_path=dataset_path,
            regime_path=regime_path,
            evaluation_start="2020-01-01",
            artifact_dir="artifacts/falsification/noise"
        )
        noise_ir = noise_summary["sentinel_audit"]["mean_diff"]
        
    finally:
        # Restore files
        if os.path.exists("data/qqq_history_real_backup.csv"):
            if os.path.exists(original_cache): os.remove(original_cache)
            os.rename("data/qqq_history_real_backup.csv", original_cache)

    print("\n============================================")
    print(f"REAL Data IR Alpha:  {real_ir:.4f}")
    print(f"WHITE NOISE IR Alpha: {noise_ir:.4f}")
    
    if real_ir > noise_ir:
        print("RESULT: PASSED (Sentinel captures real signal)")
    else:
        print("RESULT: FAILED (Sentinel is fitting noise)")
    print("============================================")

if __name__ == "__main__":
    run_falsification()
