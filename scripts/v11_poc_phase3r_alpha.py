#!/usr/bin/env python3
"""v11 POC Phase 3R: Revised Alpha Audit (The Multiplicative Law & Blood-Chip)."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_phase3r():
    audit_results_path = "data/v11_poc_phase2_audit_results.csv"
    price_vix_path = "data/v11_price_vix_history.csv"
    macro_path = "data/macro_historical_dump.csv"
    
    if not all(Path(p).exists() for p in [audit_results_path, price_vix_path, macro_path]):
        logger.error("Required data missing.")
        return

    # Load All Data
    audit_df = pd.read_csv(audit_results_path)
    price_df = pd.read_csv(price_vix_path)
    macro_df = pd.read_csv(macro_path)
    
    for df in [audit_df, price_df, macro_df]:
        df["observation_date"] = pd.to_datetime(df["observation_date"])
    
    # Unified Dataset
    df = pd.merge(audit_df, price_df[["observation_date", "qqq_close", "vix", "drawdown_pct"]], on="observation_date")
    df = pd.merge(df, macro_df[["observation_date", "credit_acceleration_pct_10d", "liquidity_roc_pct_4w", "erp_pct"]], on="observation_date")
    df = df.sort_values("observation_date")

    # 1. Opportunity Score (Based on VIX and Drawdown Rank)
    # Scaled to [0, 1]
    df["vix_rank"] = df["vix"].rolling(252*20, min_periods=252).rank(pct=True)
    df["dd_rank"] = df["drawdown_pct"].abs().rolling(252*20, min_periods=252).rank(pct=True)
    df["opportunity_score"] = (df["vix_rank"] * 0.6 + df["dd_rank"] * 0.4).fillna(0)

    # 2. Revised Bucket B Sizing (The Multiplicative Law)
    # Size_B = P(CAP + REC) * Opp_Score * 0.5_Kelly_Cap (fixed at 0.5 for POC)
    df["base_prob"] = df["CAPITULATION"] + df["RECOVERY"]
    df["size_b_standard"] = df["base_prob"] * df["opportunity_score"] * 0.5

    # 3. Blood-Chip (DEPLOY_FAST) Logic
    # Trigger: BUST is high, but acceleration is dropping and liquidity is high
    df["accel_ma10"] = df["credit_acceleration_pct_10d"].rolling(10).mean()
    df["is_accel_dropping"] = df["credit_acceleration_pct_10d"] < df["accel_ma10"]
    df["is_liquidity_surging"] = df["liquidity_roc_pct_4w"] > 5.0 # 5% per 4w is aggressive expansion
    
    df["blood_chip_active"] = (df["BUST"] > 0.5) & df["is_accel_dropping"] & df["is_liquidity_surging"]
    
    # Final Decision: Max of standard size and blood-chip override
    # If Blood-Chip is active, size is 1.0 (Full QQQ spot)
    df["bucket_b_final_size"] = np.where(df["blood_chip_active"], 1.0, df["size_b_standard"])

    # 4. LATE_CYCLE Hard Constraint (ERP < 15th percentile)
    # erp_pct in macro_df is the value, we need rank
    df["erp_rank"] = df["erp_pct"].rolling(252*20, min_periods=252).rank(pct=True)
    df["is_late_cycle"] = df["erp_rank"] <= 0.15
    df["bucket_b_final_size"] = np.where(df["is_late_cycle"], df["bucket_b_final_size"].clip(0, 0.8), df["bucket_b_final_size"])

    # 5. Simulation
    scenarios = {
        "COVID_CRASH_2020": ("2020-02-01", "2020-06-30"),
        "QT_BEAR_2022": ("2022-01-01", "2022-12-31")
    }

    results = []
    for name, (start, end) in scenarios.items():
        sub = df[(df["observation_date"] >= start) & (df["observation_date"] <= end)].copy()
        if sub.empty: continue
        
        benchmark_vwap = sub["qqq_close"].mean()
        
        # Simulated Entry
        sub["weighted_cost"] = sub["qqq_close"] * sub["bucket_b_final_size"]
        total_size = sub["bucket_b_final_size"].sum()
        
        if total_size > 0:
            avg_cost = sub["weighted_cost"].sum() / total_size
            alpha_bps = (benchmark_vwap - avg_cost) / benchmark_vwap * 10000
            
            # Count Blood-Chip Days
            bc_days = sub["blood_chip_active"].sum()
            
            results.append({
                "Scenario": name,
                "VWAP": round(benchmark_vwap, 2),
                "Bucket_B_Cost": round(avg_cost, 2),
                "Alpha_Bps": round(alpha_bps, 2),
                "BloodChip_Days": bc_days,
                "Max_Size": round(sub["bucket_b_final_size"].max(), 2)
            })

    results_df = pd.DataFrame(results)
    print("\n--- v11 POC Phase 3R (Revised) Simulation Results ---")
    print(results_df.to_string(index=False))
    
    results_df.to_csv("data/v11_poc_phase3r_results.csv", index=False)
    logger.info("3R Audit Complete.")

if __name__ == "__main__":
    run_phase3r()
