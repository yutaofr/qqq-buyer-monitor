#!/usr/bin/env python3
"""v11 POC Phase 5: The Blackout Audit (Market Reality Simulation)."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_blackout_audit():
    # 1. Load Ground Truth Data
    audit_path = "data/v11_poc_phase2_audit_results.csv"
    price_path = "data/v11_price_vix_history.csv"
    macro_path = "data/macro_historical_dump.csv"
    
    df_a = pd.read_csv(audit_path)
    df_p = pd.read_csv(price_path)
    df_m = pd.read_csv(macro_path)
    
    df = pd.merge(df_a, df_p, on="observation_date")
    df = pd.merge(df, df_m[["observation_date", "credit_spread_bps", "liquidity_roc_pct_4w", "credit_acceleration_pct_10d"]], on="observation_date")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # 2. Exogenous Adaptive Memory (Driven by Liquidity ROC Accel)
    # Define hl = f(liquidity_inflection)
    df["liq_accel"] = df["liquidity_roc_pct_4w"].diff(5)
    # If liq_accel is high (intervention), halflife shrinks
    df["adaptive_hl"] = (2520 - (df["liq_accel"].clip(0, 20) * 100)).clip(252, 2520)

    # 3. Liquidity Blackout Logic (The "Order Book Vacuum")
    df["daily_ret"] = df["qqq_close"].pct_change()
    # Trigger: VIX > 60 or Ret < -7%
    df["blackout_trigger"] = (df["vix"] > 60) | (df["daily_ret"] < -0.07)
    
    # Propagate blackout for 3 days
    df["in_blackout"] = df["blackout_trigger"].rolling(3).max().fillna(0).astype(bool)

    # 4. C-Score and Confidence (From Priority 3)
    df["rho"] = df["credit_spread_bps"].rolling(20).corr(df["vix"]).abs()
    df["c_score"] = df["rho"].fillna(0)
    df["confidence"] = (1 - df["c_score"]**2).clip(0, 1)

    # 5. The Kill-Switch (The Reversal Operator)
    # Condition: Severe BUST + Spread Accel turning down
    df["spread_accel_change"] = df["credit_acceleration_pct_10d"].diff(5)
    df["kill_switch_active"] = (df["BUST"] > 0.8) & (df["spread_accel_change"] < -10)
    
    # 6. Bucket B Sizing with Blackout & Kill-Switch
    # Standard: Size = Prob * Confidence
    # Kill-Switch: Size = Prob (Override Confidence)
    df["raw_p_hunt"] = df["CAPITULATION"] + df["RECOVERY"]
    df["final_p_hunt"] = np.where(df["kill_switch_active"], df["raw_p_hunt"], df["raw_p_hunt"] * df["confidence"])
    
    # 7. Simulation: 2020 Blackout Window
    mask_2020 = (df["observation_date"] >= "2020-03-01") & (df["observation_date"] <= "2020-04-30")
    sub = df[mask_2020].copy()
    
    # Simulation Constraints:
    # If in_blackout == True, ANY instruction to sell or convert A->Cash is IGNORED.
    # Instruction to Buy is only allowed if Cash is available.
    
    results = []
    cash_reserve = 100.0 # Initial idle cash for Bucket B
    position_value = 0.0
    
    for i, row in sub.iterrows():
        # Target deployment amount
        vix_rank = 0.8 # Simplified for POC
        target_deploy = cash_reserve * row["final_p_hunt"] * vix_rank
        
        # execution price with exponential slippage
        slip_pct = (5 * np.exp(row["vix"] / 20.0)) / 10000.0
        exec_price = row["qqq_close"] * (1 + slip_pct)
        
        status = "NORMAL"
        if row["in_blackout"]:
            status = "BLACKOUT (Orders Frozen)"
            # In blackout, we CANNOT deploy more because we assume clearing/funding is stuck
            # unless it's a Kill-Switch moment where we assume pre-positioned orders
            if not row["kill_switch_active"]:
                deployed = 0
            else:
                status = "KILL-SWITCH (Flash Deployment)"
                deployed = target_deploy
        else:
            deployed = target_deploy
            
        cash_reserve -= deployed
        position_value += (deployed / exec_price) * row["qqq_close"] # Update mark-to-market
        
        results.append({
            "Date": row["observation_date"].date(),
            "VIX": round(row["vix"], 2),
            "Status": status,
            "Hunt_P": round(row["final_p_hunt"], 4),
            "Deployed": round(deployed, 2),
            "Cash_Left": round(cash_reserve, 2),
            "Price": round(row["qqq_close"], 2)
        })

    audit_df = pd.DataFrame(results)
    print("\n--- v11 POC Phase 5 (Blackout Audit) ---")
    print(audit_df.to_string(index=False))
    
    # Final Metric: Cost vs VWAP
    benchmark_vwap = sub["qqq_close"].mean()
    deployed_sum = audit_df["Deployed"].sum()
    if deployed_sum > 0:
        avg_cost = (audit_df["Deployed"] * audit_df["Price"]).sum() / deployed_sum
        alpha_bps = (benchmark_vwap - avg_cost) / benchmark_vwap * 10000
        print(f"\nPhase 5 Alpha: {alpha_bps:.2f} bps")
        print(f"Total Deployment: {deployed_sum:.2f}% of Initial Reserve")
    else:
        print("\nPhase 5: No deployment triggered. Survival Mode Only.")

if __name__ == "__main__":
    run_blackout_audit()
