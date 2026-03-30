#!/usr/bin/env python3
"""v11 POC Priority 2: Reality Check (Slippage & Margin)."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_reality_check():
    # Load combined data from previous steps
    # We use the audit results which contain the Bayesian probabilities
    audit_path = "data/v11_poc_phase2_audit_results.csv"
    price_path = "data/v11_price_vix_history.csv"
    
    df_a = pd.read_csv(audit_path)
    df_p = pd.read_csv(price_path)
    df = pd.merge(df_a, df_p, on="observation_date")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # 1. Implementation of Exponential Slippage Model
    # Baseline slippage: 5 bps
    df["slippage_bps"] = 5 * np.exp(df["vix"] / 20.0)
    df["slippage_pct"] = df["slippage_bps"] / 10000.0

    # 2. Deployment Logic (Bucket B)
    # Using the refined Multiplicative Law
    # Size_B = P(CAP+REC) * Opp_Score * 0.5_Kelly
    # For POC, we use a proxy for Opp_Score based on VIX rank
    df["vix_rank"] = df["vix"].rolling(252*20, min_periods=252).rank(pct=True)
    df["base_prob"] = df["CAPITULATION"] + df["RECOVERY"]
    df["target_size"] = df["base_prob"] * df["vix_rank"] * 0.5

    # 3. Simulate Scenarios with Slippage
    scenarios = {
        "COVID_2020": ("2020-02-01", "2020-06-30"),
        "QT_2022": ("2022-01-01", "2022-12-31")
    }

    results = []
    for name, (start, end) in scenarios.items():
        sub = df[(df["observation_date"] >= start) & (df["observation_date"] <= end)].copy()
        if sub.empty: continue
        
        # Benchmark: VWAP
        benchmark_cost = sub["qqq_close"].mean()
        
        # Bucket B: Weighted entry with slippage penalty
        # Execution Price = Market Close * (1 + slippage_pct)
        sub["execution_price"] = sub["qqq_close"] * (1 + sub["slippage_pct"])
        
        sub["weighted_cost"] = sub["execution_price"] * sub["target_size"]
        total_size = sub["target_size"].sum()
        
        if total_size > 0:
            avg_cost = sub["weighted_cost"].sum() / total_size
            alpha_bps = (benchmark_cost - avg_cost) / benchmark_cost * 10000
            
            # Impact of slippage on Alpha
            theoretical_avg_cost = (sub["qqq_close"] * sub["target_size"]).sum() / total_size
            slippage_impact_bps = (avg_cost - theoretical_avg_cost) / theoretical_avg_cost * 10000
            
            results.append({
                "Scenario": name,
                "VWAP": round(benchmark_cost, 2),
                "Real_Cost": round(avg_cost, 2),
                "Alpha_Bps": round(alpha_bps, 2),
                "Slip_Impact_Bps": round(slippage_impact_bps, 2),
                "Max_Slip_Bps": round(sub["slippage_bps"].max(), 2)
            })

    results_df = pd.DataFrame(results)
    print("\n--- v11 POC Priority 2 (Reality Check) Results ---")
    print(results_df.to_string(index=False))
    
    logger.info("Reality Check Complete. Alpha survives if positive.")

if __name__ == "__main__":
    run_reality_check()
