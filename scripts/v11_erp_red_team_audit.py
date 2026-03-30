#!/usr/bin/env python3
"""v11 Red Team Audit: Deep Dive into ERP Momentum.
Testing different window sizes and smoothing techniques to reconcile discrepancies.
"""
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def evaluate_regime_sensitivity(args):
    """Evaluates how well a specific ERP momentum variant aligns with Stress Regimes."""
    df_eval, feature, target_col = args
    # Focus on BUST and LATE_CYCLE detection
    stress_regimes = ["BUST", "LATE_CYCLE"]
    
    clean_df = df_eval[[feature, target_col]].dropna()
    if len(clean_df) < 500: return None
    
    # Calculate Correlation specifically during 'Stress' transitions
    # (Leading signal check: feature at t-5 vs regime at t)
    clean_df["target_is_stress"] = clean_df[target_col].isin(stress_regimes).astype(int)
    correlation = clean_df[feature].corr(clean_df["target_is_stress"].shift(-5))
    
    return {
        "variant": feature,
        "stress_correlation_lead_5d": correlation,
        "sample_count": len(clean_df)
    }

def run_audit():
    data_path = Path("data/v11_poc_phase1_results.csv")
    macro_path = Path("data/macro_historical_dump.csv")
    df = pd.read_csv(data_path)
    macro_df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])
    
    if "erp_pct" not in df.columns:
        df = pd.merge(df, macro_df[["observation_date", "erp_pct"]], on="observation_date", how="left")
    
    df = df.sort_values("observation_date")
    erp = df["erp_pct"]
    
    for w in [10, 21, 63]:
        diff = -erp.diff(w) # Falling ERP = Positive Stress Signal
        df[f"erp_m_raw_{w}d"] = (diff - diff.rolling(252).mean()) / diff.rolling(252).std()
        
        smoothed_erp = erp.ewm(span=w//2).mean()
        s_diff = -smoothed_erp.diff(w)
        df[f"erp_m_smooth_{w}d"] = (s_diff - s_diff.rolling(252).mean()) / s_diff.rolling(252).std()
    
    features_to_test = [c for c in df.columns if "erp_m_" in c]
    logger.info(f"Auditing {len(features_to_test)} ERP Momentum variants...")
    
    with ProcessPoolExecutor() as executor:
        tasks = [(df, f, "regime") for f in features_to_test]
        results = list(executor.map(evaluate_regime_sensitivity, tasks))
    
    print("\n" + "="*60)
    print(f"{'ERP Variant':<25} | {'Stress Correlation (5d Lead)':<30}")
    print("-" * 60)
    for res in results:
        if res:
            print(f"{res['variant']:<25} | {res['stress_correlation_lead_5d']:+.4f}")
    print("="*60)

if __name__ == "__main__":
    run_audit()
