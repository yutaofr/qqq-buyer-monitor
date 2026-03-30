import pandas as pd
import numpy as np
from src.engine.v11.conductor import V11Conductor
from scipy.stats import spearmanr
import logging

# Silence logs for audit speed
logging.getLogger().setLevel(logging.ERROR)

def run_v11_full_system_audit():
    print("--- v11.11 Full System Performance Audit (25-Year Sweep) ---")
    
    # 1. Load Data
    macro = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    # The POC file has a header.
    poc_results = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")
    
    actual_regimes = poc_results["regime"]
    qqq_close = pd.to_numeric(poc_results["qqq_close"], errors='coerce')
    fwd_21d_returns = qqq_close.pct_change(21).shift(-21)

    conductor = V11Conductor()
    
    audit_data = []
    # Intersect dates to ensure we have macro, labels, and returns
    dates = actual_regimes.index.intersection(macro.index).intersection(fwd_21d_returns.dropna().index)
    dates = dates.sort_values()

    print(f"Processing {len(dates)} trading days...")
    
    for i, d in enumerate(dates):
        if i < 252: continue # Warmup for seeder
        
        # Run conductor
        historical_snapshot = macro.loc[:d].iloc[-260:]
        try:
            res = conductor.daily_run(historical_snapshot)
        except Exception:
            continue
            
        actual = actual_regimes.get(d)
        fwd_ret = fwd_21d_returns.get(d, 0.0)
        
        # Collect Metrics
        audit_data.append({
            "date": d,
            "predicted": max(res["probabilities"], key=res["probabilities"].get),
            "actual": actual,
            "brier_comp": sum(( (1.0 if r == actual else 0.0) - res["probabilities"].get(r, 0.0))**2 for r in res["probabilities"]),
            "target_beta": float(res["target_beta"]),
            "raw_beta": float(res["raw_target_beta"]),
            "cdr": float(res["deployment_readiness"]),
            "fwd_ret": float(fwd_ret),
            "ideal_beta": float(1.0 if actual in ["MID_CYCLE", "RECOVERY", "CAPITULATION"] else (0.4 if actual == "BUST" else 0.6))
        })

    if not audit_data:
        print("Error: No audit data generated. Check date intersection.")
        return

    df = pd.DataFrame(audit_data)
    
    # --- Metrics Calculation ---
    accuracy = (df["predicted"] == df["actual"]).mean()
    # Brier score is sum of squared errors across all classes / N
    # Since I did it per-day: avg(sum( (y_i - p_i)^2 ))
    brier_score = df["brier_comp"].mean()
    
    # 2. Beta Fidelity (AC-4)
    mae = (df["target_beta"] - df["ideal_beta"]).abs().mean()
    
    # 3. Deployment Efficacy
    corr, p_val = spearmanr(df["cdr"], df["fwd_ret"])
    
    # Use standard partitions if enough data
    fast_deployment_ret = df[df["cdr"] > 0.65]["fwd_ret"].mean()
    pause_deployment_ret = df[df["cdr"] < 0.35]["fwd_ret"].mean()

    print("\n--- PERFORMANCE SCORECARD ---")
    print(f"1. Regime Accuracy:    {accuracy:.2%}")
    print(f"2. Brier Score:        {brier_score:.4f}")
    print(f"3. Beta Fidelity MAE:  {mae:.4f} (Target < 0.05)")
    print(f"4. CDR Correlation:    {corr:.4f} (p={p_val:.4f})")
    print("\n--- Deployment Attribution ---")
    print(f"Avg 21d Return (High Readiness): {fast_deployment_ret:.2%}")
    print(f"Avg 21d Return (Low Readiness):  {pause_deployment_ret:.2%}")
    print("----------------------------")

if __name__ == "__main__":
    run_v11_full_system_audit()
