#!/usr/bin/env python3
"""v11 POC Phase 5R: Final Realism Audit (The Marks Re-dissection)."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_final_realism_audit():
    # 1. Load Ground Truth Data (Credit, VIX, VIX3M, Price)
    audit_path = "data/v11_poc_phase2_audit_results.csv"
    evidence_path = "data/v11_full_evidence_history.csv"
    macro_path = "data/macro_historical_dump.csv"
    
    df_a = pd.read_csv(audit_path)
    df_e = pd.read_csv(evidence_path)
    df_m = pd.read_csv(macro_path)
    
    df = pd.merge(df_a, df_e, on="observation_date")
    df = pd.merge(df, df_m[["observation_date", "credit_spread_bps", "credit_acceleration_pct_10d"]], on="observation_date")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # 2. Exogenous Adaptive Memory (Ex-VIX)
    # hl_t = base_hl * exp(-kappa * malignant_expansion)
    baseline_ema = df["credit_spread_bps"].ewm(span=20, adjust=False).mean()
    malignant_expansion = ((df["credit_spread_bps"] - baseline_ema) / baseline_ema).clip(lower=0)
    kappa = 5.0
    df["adaptive_hl_years"] = (10.0 * np.exp(-kappa * malignant_expansion)).clip(lower=0.5)

    # 3. Liquidity Blackout & Kill-Switch
    df["daily_ret"] = df["qqq_close"].pct_change()
    df["blackout_trigger"] = (df["vix"] > 60) | (df["daily_ret"] < -0.07)
    df["in_blackout"] = df["blackout_trigger"].rolling(3).max().fillna(0).astype(bool)

    # Kill-Switch: TS Reversion + Divergence
    df["ts_spread"] = df["vix3m"] - df["vix"]
    df["ts_reversion_3d"] = df["ts_spread"].diff(3)
    df["vix_momentum"] = df["vix"].diff(1)
    # Price 2nd derivative (acceleration)
    df["p_accel"] = df["qqq_close"].diff(1).diff(1)
    
    df["kill_switch"] = (df["in_blackout"]) & \
                        (df["vix_momentum"] < 0) & \
                        (df["ts_reversion_3d"] > 3.0) & \
                        (df["p_accel"] > 0)

    # 4. C-Score Confidance (with Kill-Switch Override)
    df["rho"] = df["credit_spread_bps"].rolling(20).corr(df["vix"]).abs()
    df["confidence"] = (1 - df["rho"]**2).clip(0, 1)
    
    # 5. Money Market Scaling (Rf = 4.5% annual)
    rf_daily = (1 + 0.045)**(1/252) - 1

    # 6. Simulation: 2020 Crash
    mask_2020 = (df["observation_date"] >= "2020-03-01") & (df["observation_date"] <= "2020-04-30")
    sub = df[mask_2020].copy()
    
    results = []
    bucket_b_cash = 100.0 # Reserve in Money Market
    position_shares = 0.0
    
    for i, row in sub.iterrows():
        # Daily Interest Accrual
        bucket_b_cash *= (1 + rf_daily)
        
        # Sizing
        p_hunt = row["CAPITULATION"] + row["RECOVERY"]
        target_size = bucket_b_cash * p_hunt * row["confidence"]
        
        # Kill-Switch Override: Max Deployment if triggered
        if row["kill_switch"]:
            target_size = bucket_b_cash * 0.8 # Release 80% of reserve
            status = "KILL-SWITCH (Attack!)"
        elif row["in_blackout"]:
            target_size = 0.0
            status = "BLACKOUT (Frozen)"
        else:
            status = "NORMAL"
            
        # Slippage model
        slip_pct = (5 * np.exp(row["vix"] / 20.0)) / 10000.0
        exec_price = row["qqq_close"] * (1 + slip_pct)
        
        if target_size > 0:
            deployed = min(target_size, bucket_b_cash)
            position_shares += deployed / exec_price
            bucket_b_cash -= deployed
        else:
            deployed = 0
            
        results.append({
            "Date": row["observation_date"].date(),
            "VIX": round(row["vix"], 2),
            "TS_Spread": round(row["ts_spread"], 2),
            "Status": status,
            "Deployed": round(deployed, 2),
            "Cash": round(bucket_b_cash, 2),
            "Price": round(row["qqq_close"], 2)
        })

    audit_df = pd.DataFrame(results)
    print("\n--- v11 POC Phase 5R (Ultimate Realism) ---")
    print(audit_df.to_string(index=False))
    
    # Performance Metric
    benchmark_vwap = sub["qqq_close"].mean()
    deployed_sum = audit_df["Deployed"].sum()
    if deployed_sum > 0:
        avg_cost = (audit_df["Deployed"] * audit_df["Price"]).sum() / deployed_sum
        alpha_bps = (benchmark_vwap - avg_cost) / benchmark_vwap * 10000
        print(f"\nFinal Alpha: {alpha_bps:.2f} bps")
    else:
        print("\nFinal Result: No Deployment. Engine still too conservative.")

if __name__ == "__main__":
    run_final_realism_audit()
