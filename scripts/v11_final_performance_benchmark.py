#!/usr/bin/env python3
"""v11 Final Performance Benchmark: Legacy (10d) vs Multiscale (v11.5).
Quantifies the impact of optimal horizons on all pipeline stages.
"""
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path
from sklearn.metrics import accuracy_score

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def evaluate_performance(df, mode="LEGACY"):
    """
    Simulates decision making for a specific architecture mode.
    LEGACY: All windows = 10d
    MULTISCALE: A=252d, B_VIX=126d, B_Breadth=5d, C=252d
    """
    results = {}
    
    # --- Class A: Regime Inference ---
    if mode == "LEGACY":
        # Using 10d for all
        a_signal = -df["real_yield_10y_pct"].diff(10).rolling(252).rank(pct=True)
    else:
        # Using 252d for structural anchor
        a_signal = -df["real_yield_10y_pct"].diff(252).rolling(252).rank(pct=True)
    
    # Accuracy in identifying Stress (Simplified logic: Signal < 0.2 means High Stress)
    df["is_stress"] = df["regime"].isin(["BUST", "LATE_CYCLE"]).astype(int)
    pred_stress = (a_signal < 0.25).astype(int)
    results["regime_accuracy"] = accuracy_score(df["is_stress"], pred_stress)
    
    # Brier Score Proxy (Mean Squared Error of probability)
    # We use the raw rank as a probability proxy for stress
    results["brier_score"] = np.mean((a_signal - (1.0 - df["is_stress"]))**2)

    # --- Class B: Deployment Pacing ---
    if mode == "LEGACY":
        b_signal = df["vix"].diff(10).rolling(252).rank(pct=True)
    else:
        # VIX optimal is 126d for pacing
        b_signal = df["vix"].diff(126).rolling(252).rank(pct=True)
        
    # Pacing efficiency: Correlation with forward 3d return
    fwd_return = df["qqq_close"].shift(-3) / df["qqq_close"] - 1.0
    results["pacing_correlation"] = b_signal.corr(fwd_return)

    # --- Class C: Fidelity Guard ---
    if mode == "LEGACY":
        c_signal = df["breadth_proxy"].diff(10).rolling(252).rank(pct=True)
    else:
        # Breadth drift optimal is 252d
        c_signal = df["breadth_proxy"].diff(252).rolling(252).rank(pct=True)
    
    # Drift detection: Correlation with structural relative strength
    results["drift_correlation"] = c_signal.corr(df["breadth_proxy"])
    
    return results

def run_benchmark():
    data_path = Path("data/v11_poc_phase1_results.csv")
    macro_path = Path("data/macro_historical_dump.csv")
    df = pd.read_csv(data_path)
    macro_df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])
    
    # Enrichment
    factors = ["real_yield_10y_pct", "vix"]
    for f in factors:
        if f not in df.columns:
            df = pd.merge(df, macro_df[["observation_date", f]], on="observation_date", how="left")
    
    df = df.sort_values("observation_date").dropna(subset=["real_yield_10y_pct", "vix", "regime"])
    
    legacy_res = evaluate_performance(df, mode="LEGACY")
    multi_res = evaluate_performance(df, mode="MULTISCALE")
    
    print("\n" + "="*70)
    print(f"{'Metric':<30} | {'Legacy (10d)':<15} | {'Multiscale (v11.5)':<15}")
    print("-" * 70)
    metrics = [
        ("Regime Accuracy (Stress)", "regime_accuracy", "{:.2%}"),
        ("Brier Score (Lower is better)", "brier_score", "{:.4f}"),
        ("Pacing Correlation (Fwd 3d)", "pacing_correlation", "{:+.4f}"),
        ("Drift Sensitivity (Annual)", "drift_correlation", "{:+.4f}")
    ]
    
    for label, key, fmt in metrics:
        l_val = legacy_res[key]
        m_val = multi_res[key]
        print(f"{label:<30} | {fmt.format(l_val):<15} | {fmt.format(m_val):<15}")
    print("="*70)

if __name__ == "__main__":
    run_benchmark()
