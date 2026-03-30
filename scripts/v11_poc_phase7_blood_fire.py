#!/usr/bin/env python3
"""v11 POC Phase 7: The 'Blood & Fire' Audit.
Tests Bayesian Deleveraging and Convexity Nuke against the 2020 Meat Grinder.
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

from src.engine.v11.allocator.dynamic_deleverager import BayesianDeleverager
from src.engine.v11.allocator.convexity_nuke import ConvexityEngine

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_blood_fire_audit():
    # 1. Load Ground Truth
    audit_path = "data/v11_poc_phase2_audit_results.csv"
    evidence_path = "data/v11_full_evidence_history.csv"
    df_a = pd.read_csv(audit_path)
    df_e = pd.read_csv(evidence_path)
    df = pd.merge(df_a, df_e, on="observation_date")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # 2. Components
    deleverager = BayesianDeleverager(gamma=2.0)
    nuke_engine = ConvexityEngine(premium_budget_bps=200) # 2% premium drag/year
    
    # 3. Pre-calculate Kill-Switch
    df["ts_spread"] = df["vix3m"] - df["vix"]
    df["delta_ts"] = df["ts_spread"].diff(3)
    df["mu_slow"] = df["delta_ts"].rolling(252).mean()
    df["std_slow"] = df["delta_ts"].rolling(252).std()
    df["z_slow"] = (df["delta_ts"] - df["mu_slow"]) / df["std_slow"]
    df["vix_momentum"] = df["vix"].diff(1)
    df["kill_switch"] = (df["z_slow"] > 3.0) & (df["vix_momentum"] < 0)

    # 4. Simulation: 2020 Crash
    initial_aum = 1_000_000.0
    shares_a = 700_000.0 / df.iloc[0]["qqq_close"] # 70% spot
    free_cash = 300_000.0 # Initial 30% reserve
    
    mask_2020 = (df["observation_date"] >= "2020-02-01") & (df["observation_date"] <= "2020-04-15")
    sub = df[mask_2020].copy()
    
    results = []
    
    for i, row in sub.iterrows():
        price = row["qqq_close"]
        vix = row["vix"]
        p_bust = row["BUST"]
        
        # --- LEFT SIDE: Bayesian Deleveraging ---
        current_spot_value = shares_a * price
        target_ratio = deleverager.compute_safe_exposure(p_bust)
        
        # If overexposed based on Bayesian prob, SELL.
        if (current_spot_value / (current_spot_value + free_cash)) > target_ratio:
            sell_amount = current_spot_value - (current_spot_value + free_cash) * target_ratio
            shares_a -= (sell_amount / price)
            free_cash += sell_amount
            deleveraged = True
        else:
            deleveraged = False

        # --- RIGHT SIDE: Convexity Nuke ---
        nuke_payout = 0.0
        if row["kill_switch"]:
            # Approximate: base vix was 15 before the crash
            nuke_payout = nuke_engine.simulate_nuke_payout(
                total_equity=(shares_a * price + free_cash),
                base_vix=15.0,
                peak_vix=vix,
                is_kill_switch_triggered=True
            )
            free_cash += nuke_payout

        results.append({
            "Date": row["observation_date"].date(),
            "VIX": round(vix, 2),
            "P_BUST": round(p_bust, 4),
            "Exp_A": round(target_ratio * 100, 1),
            "Free_Cash": round(free_cash, 0),
            "Nuke": round(nuke_payout, 0),
            "Price": round(price, 2)
        })

    audit_df = pd.DataFrame(results)
    print("\n--- v11 POC Phase 7 (Blood & Fire Audit) ---")
    print(audit_df.to_string(index=False))
    
    # Final Verdict
    peak_cash = audit_df["Free_Cash"].max()
    print(f"\nFinal Liquidity Achievement: Max Free Cash ${peak_cash:,.0f}")
    if peak_cash > 1_500_000:
        logger.info("Verdit: Apex Predator Confirmed. Cash reserves exceeded 1.5x initial AUM through Convexity.")
    else:
        logger.error("Verdict: Firepower insufficient.")

if __name__ == "__main__":
    run_blood_fire_audit()
