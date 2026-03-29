#!/usr/bin/env python3
"""v11 POC Phase 3: Incremental Alpha Simulation (Bucket B)."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_phase3():
    audit_results_path = "data/v11_poc_phase2_audit_results.csv"
    price_vix_path = "data/v11_price_vix_history.csv"
    
    if not Path(audit_results_path).exists() or not Path(price_vix_path).exists():
        logger.error("Phase 2 results missing. Run scripts/v11_poc_phase2_audit.py first.")
        return

    # Load Audit Probabilities
    audit_df = pd.read_csv(audit_results_path)
    audit_df["observation_date"] = pd.to_datetime(audit_df["observation_date"])
    
    # Load Prices
    price_df = pd.read_csv(price_vix_path)
    price_df["observation_date"] = pd.to_datetime(price_df["observation_date"])
    
    # Merge
    df = pd.merge(audit_df, price_df[["observation_date", "qqq_close", "vix"]], on="observation_date", how="inner")
    df = df.sort_values("observation_date")

    # 1. Bucket B Sizing Strategy
    # Size_B = P(CAPITULATION) * Opp_Score * 0.5_Kelly (simplified)
    # Opportunity Score Proxy: VIX_pct > 0.8 or High Drawdown
    # For POC, let's use P(CAPITULATION) + P(RECOVERY) as the deployment signal
    
    df["deployment_score"] = df["CAPITULATION"] + (df["RECOVERY"] * 0.3)
    df["bucket_b_size"] = df["deployment_score"].clip(0, 1) # Target size as fraction of new cash
    
    # Simulate two major scenarios: 2020 and 2022
    scenarios = {
        "COVID_CRASH_2020": ("2020-02-01", "2020-06-30"),
        "QT_BEAR_2022": ("2022-01-01", "2022-12-31")
    }

    results = []
    for name, (start, end) in scenarios.items():
        sub = df[(df["observation_date"] >= start) & (df["observation_date"] <= end)].copy()
        if sub.empty: continue
        
        # Benchmark: Simple VWAP entry over the period
        benchmark_vwap = sub["qqq_close"].mean() 
        
        # Bucket B: Time-weighted entry based on deployment_score
        # We assume buying fixed amount of cash daily weighted by bucket_b_size
        sub["weighted_cost"] = sub["qqq_close"] * sub["bucket_b_size"]
        total_size = sub["bucket_b_size"].sum()
        
        if total_size > 0:
            bucket_b_avg_cost = sub["weighted_cost"].sum() / total_size
            alpha_bps = (benchmark_vwap - bucket_b_avg_cost) / benchmark_vwap * 10000
            
            # Max Size Reached
            max_size = sub["bucket_b_size"].max()
            
            results.append({
                "Scenario": name,
                "Benchmark_VWAP": round(benchmark_vwap, 2),
                "Bucket_B_Avg_Cost": round(bucket_b_avg_cost, 2),
                "Alpha_Bps": round(alpha_bps, 2),
                "Max_Deployment_Score": round(max_size, 3)
            })
        else:
            logger.warning(f"No deployment triggered for {name}")

    # 2. Output and Observations
    results_df = pd.DataFrame(results)
    print("\n--- Bucket B Incremental Alpha Simulation Results ---")
    print(results_df.to_string(index=False))
    
    # Save Report
    output_path = "data/v11_poc_phase3_alpha_results.csv"
    results_df.to_csv(output_path, index=False)
    logger.info(f"\nPhase 3 results saved to {output_path}")

if __name__ == "__main__":
    run_phase3()
