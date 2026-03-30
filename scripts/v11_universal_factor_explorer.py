#!/usr/bin/env python3
"""v11 Research: The Final Universal Sweep.
Scans EVERY available column in the dataset across 5 time horizons.
Ensures no 'Ghost Factor' is left behind.
"""
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def calculate_variant(df, factor, window):
    """Calculates a normalized momentum signal for any factor."""
    try:
        # Directional mapping: Lower is stress for these
        low_is_stress = ["erp", "liquidity", "yield", "pe", "breadth", "qqq", "vix3m"]
        direction = -1.0 if any(x in factor.lower() for x in low_is_stress) else 1.0
        
        # Calculate EWMA smoothed diff
        smoothed = df[factor].ewm(span=window).mean()
        diff = direction * smoothed.diff(window)
        # Z-Score normalization
        z_score = (diff - diff.rolling(252).mean()) / diff.rolling(252).std()
        return z_score
    except:
        return None

def audit_worker(args):
    df_eval, factor, window, target_col = args
    signal = calculate_variant(df_eval, factor, window)
    if signal is None: return None
    
    eval_df = pd.DataFrame({"signal": signal, "regime": df_eval[target_col]}).dropna()
    if len(eval_df) < 500: return None
    
    # Target: Stress regimes (BUST, LATE_CYCLE)
    eval_df["is_stress"] = eval_df["regime"].isin(["BUST", "LATE_CYCLE"]).astype(int)
    # 10-day Lead Correlation
    correlation = eval_df["signal"].corr(eval_df["is_stress"].shift(-10))
    
    return {
        "factor": factor,
        "window": window,
        "correlation": correlation,
        "samples": len(eval_df)
    }

def run_final_sweep():
    # 1. Load ALL available data
    data_path = Path("data/v11_poc_phase1_results.csv")
    macro_path = Path("data/macro_historical_dump.csv")
    df = pd.read_csv(data_path)
    macro_df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])
    
    # Universal Merge: Get every single numerical column from macro_df
    numeric_cols = macro_df.select_dtypes(include=[np.number]).columns.tolist()
    # Add price-based tactical columns
    tactical_cols = ["vix", "drawdown_pct", "breadth_proxy"]
    all_factors = list(set(numeric_cols + tactical_cols))
    
    # Merge and resolve names
    df = pd.merge(df, macro_df[["observation_date"] + numeric_cols], on="observation_date", how="left", suffixes=("", "_raw"))
    df = df.sort_values("observation_date")
    
    # 2. Grid Search (Every Factor x 5 Horizons)
    windows = [10, 21, 63, 126, 252]
    tasks = []
    
    # Filter out columns that are redundant or not factors (like build_version placeholders)
    blacklist = ["Unnamed", "build_version", "funding_stress_flag", "pca", "hwm"]
    final_factor_list = [f for f in all_factors if not any(b in f for b in blacklist) and f in df.columns]
    
    logger.info(f"Launching FINAL SWEEP for {len(final_factor_list)} factors across {len(windows)} windows...")
    
    with ProcessPoolExecutor() as executor:
        for f in final_factor_list:
            if df[f].notna().sum() > 500:
                for w in windows:
                    tasks.append((df, f, w, "regime"))
        
        results = list(executor.map(audit_worker, tasks))
    
    # 3. Final Report
    res_df = pd.DataFrame([r for r in results if r is not None])
    res_df = res_df.sort_values("correlation", ascending=False)
    
    print("\n" + "="*85)
    print(f"{'Factor (The Final List)':<30} | {'Best Window':<12} | {'Max Corr':<8}")
    print("-" * 85)
    
    # Show Top 1 for each factor to find their "Optimal Version"
    summary = res_df.loc[res_df.groupby("factor")["correlation"].idxmax()].sort_values("correlation", ascending=False)
    for _, row in summary.iterrows():
        print(f"{row['factor']:<30} | {int(row['window']):<11}d | {row['correlation']:+.4f}")
    print("="*85)

if __name__ == "__main__":
    run_final_sweep()
