#!/usr/bin/env python3
"""v11 POC Phase 6: The Clearing House Meat Grinder Audit.
Simulates cross-margin contagion and dual-anchor Z-score kill-switch.
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_meat_grinder_audit():
    # 1. Load Ground Truth
    audit_path = "data/v11_poc_phase2_audit_results.csv"
    evidence_path = "data/v11_full_evidence_history.csv"
    macro_path = "data/macro_historical_dump.csv"
    
    df_a = pd.read_csv(audit_path)
    df_e = pd.read_csv(evidence_path)
    df_m = pd.read_csv(macro_path)
    
    df = pd.merge(df_a, df_e, on="observation_date")
    df = pd.merge(df, df_m[["observation_date", "credit_spread_bps"]], on="observation_date")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # 2. Dual-Anchor Z-Score Kill-Switch
    df["ts_spread"] = df["vix3m"] - df["vix"]
    df["delta_ts"] = df["ts_spread"].diff(3) # 3-day momentum
    
    # Fast window: 20d, Slow window: 252d
    df["mu_fast"] = df["delta_ts"].rolling(20).mean()
    df["std_fast"] = df["delta_ts"].rolling(20).std()
    df["mu_slow"] = df["delta_ts"].rolling(252).mean()
    df["std_slow"] = df["delta_ts"].rolling(252).std()
    
    df["z_fast"] = (df["delta_ts"] - df["mu_fast"]) / df["std_fast"]
    df["z_slow"] = (df["delta_ts"] - df["mu_slow"]) / df["std_slow"]
    
    df["vix_momentum"] = df["vix"].diff(1)
    df["kill_switch_active"] = (df["z_fast"] > 2.0) & (df["z_slow"] > 3.0) & (df["vix_momentum"] < 0)

    # 3. Prime Brokerage Simulator (Margin Contagion)
    # Scenario: $1M Account. Bucket A holds $700k QQQ. Bucket B holds $300k T-Bills.
    initial_a_exposure = 700000.0
    initial_b_cash = 300000.0
    initial_a_price = 220.0 # Feb 2020 price
    shares_a = initial_a_exposure / initial_a_price
    
    mask_2020 = (df["observation_date"] >= "2020-03-01") & (df["observation_date"] <= "2020-04-15")
    sub = df[mask_2020].copy()
    
    results = []
    bucket_b_cash = initial_b_cash
    position_b_notional = 0.0
    
    for i, row in sub.iterrows():
        # A. Calculate Account NAV
        val_a = shares_a * row["qqq_close"]
        nav = val_a + bucket_b_cash
        
        # B. Clearing House Logic: Dynamic MMR for Bucket A
        # Base 15%. Spikes with VIX.
        dynamic_mmr_a = 0.15 * (1 + (row["vix"] / 30.0))
        dynamic_mmr_a = min(dynamic_mmr_a, 0.80) # Cap at 80% for stock
        locked_margin_a = val_a * dynamic_mmr_a
        
        # C. T-Bill Haircut
        haircut = 0.05 if row["vix"] > 60 else 0.01
        discounted_tbill = bucket_b_cash * (1 - haircut)
        
        # D. TRUE Buying Power (The Residual)
        # Margin call buffer: 1.2
        true_buying_power = nav - (locked_margin_a * 1.2)
        true_buying_power = max(0, min(true_buying_power, discounted_tbill))
        
        # E. Execution: Futures Synthetic
        # 1 NQ = $15000 * 20 = $300,000 Notional. IM = $18,000 * (1 + VIX/100)
        nq_price = row["qqq_close"] * 65 # Proxy for NQ basis
        im_per_contract = 18000 * (1 + row["vix"] / 100.0)
        
        deployed_contracts = 0
        if row["kill_switch_active"] and true_buying_power > im_per_contract:
            deployed_contracts = int(true_buying_power / im_per_contract)
            deployed_notional = deployed_contracts * nq_price * 20
            bucket_b_cash -= (deployed_contracts * im_per_contract) # Locked
            position_b_notional += deployed_notional
            status = f"KILL-SWITCH (Long {deployed_contracts} NQ)"
        else:
            status = "NORMAL" if not row["kill_switch_active"] else "RESURRECTED BUT MARGIN BLOCKED"

        results.append({
            "Date": row["observation_date"].date(),
            "VIX": round(row["vix"], 2),
            "Z_Slow": round(row["z_slow"], 2),
            "MMR_A": round(dynamic_mmr_a, 3),
            "True_BP": round(true_buying_power, 0),
            "Status": status,
            "Price": round(row["qqq_close"], 2)
        })

    audit_df = pd.DataFrame(results)
    print("\n--- v11 POC Phase 6 (Clearing House Meat Grinder) ---")
    print(audit_df.to_string(index=False))
    
    # Check if we went bust
    min_bp = audit_df["True_BP"].min()
    if min_bp == 0:
        logger.error("FATAL: Margin Call detected during crisis. Bucket B buying power evaporated.")
    else:
        logger.info(f"Survival confirmed. Min Buying Power: ${min_bp:,.0f}")

if __name__ == "__main__":
    run_meat_grinder_audit()
