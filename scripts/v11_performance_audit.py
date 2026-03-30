import pandas as pd
import numpy as np
from src.engine.v11.conductor import V11Conductor
from scipy.stats import spearmanr
import logging

# Silence logs for audit speed
logging.getLogger().setLevel(logging.ERROR)

def run_v11_full_system_audit():
    print("--- v11.15 Bayesian Kelly Performance Audit (25-Year Sweep) ---")
    
    # 1. Load Data
    macro = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    poc_results = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")
    
    actual_regimes = poc_results["regime"]
    qqq_close = pd.to_numeric(poc_results["qqq_close"], errors='coerce')
    
    # Audit Horizon: 63 days (1 Quarter)
    HORIZON = 63
    fwd_returns = qqq_close.pct_change(HORIZON).shift(-HORIZON)
    
    # Forward MDD (within the next 63 days)
    # 1 - (min_close / current_close)
    fwd_min_close = qqq_close.rolling(window=HORIZON).min().shift(-HORIZON)
    fwd_mdd = (fwd_min_close / qqq_close) - 1.0

    conductor = V11Conductor()
    
    audit_data = []
    dates = actual_regimes.index.intersection(macro.index).intersection(fwd_returns.dropna().index)
    dates = dates.sort_values()

    print(f"Processing {len(dates)} trading days with 63-day Horizon...")
    
    for i, d in enumerate(dates):
        if i < 252: continue # Warmup
        
        # Snapshot for 5-year structural rank
        historical_snapshot = macro.loc[:d].iloc[-1260:]
        try:
            res = conductor.daily_run(historical_snapshot)
        except Exception:
            continue
            
        actual = actual_regimes.get(d)
        ret_val = float(fwd_returns.get(d, 0.0))
        mdd_val = float(fwd_mdd.get(d, 0.0))
        
        # Risk-Adjusted Score: Sortino proxy (Return / max(abs(MDD), 0.05))
        # Clipping floor on MDD to avoid division by zero
        risk_adj = ret_val / max(abs(mdd_val), 0.02)
        
        audit_data.append({
            "date": d,
            "predicted": max(res["probabilities"], key=res["probabilities"].get),
            "actual": actual,
            "brier_comp": sum(((1.0 if r == actual else 0.0) - res["probabilities"].get(r, 0.0))**2 for r in res["probabilities"]),
            "target_beta": float(res["target_beta"]),
            "cdr": float(res["deployment_readiness"]),
            "fwd_ret": ret_val,
            "fwd_mdd": mdd_val,
            "risk_adj": risk_adj,
            "ideal_beta": float(1.0 if actual in ["MID_CYCLE", "RECOVERY", "CAPITULATION"] else (0.4 if actual == "BUST" else 0.6))
        })

    if not audit_data:
        print("Error: Empty intersection.")
        return

    df = pd.DataFrame(audit_data)
    
    accuracy = (df["predicted"] == df["actual"]).mean()
    brier_score = df["brier_comp"].mean()
    mae = (df["target_beta"] - df["ideal_beta"]).abs().mean()
    
    # 2. CDR Audit (Primary Metric: Risk-Adjusted Efficacy)
    # Correlation between Readiness Score and Forward Risk-Adjusted Return
    corr, p_val = spearmanr(df["cdr"], df["risk_adj"])
    
    high_ready_mask = df["cdr"] > 0.4
    low_ready_mask = df["cdr"] <= 0.4
    
    high_ready_sortino = df[high_ready_mask]["risk_adj"].mean()
    low_ready_sortino = df[low_ready_mask]["risk_adj"].mean()
    
    high_ready_mdd = df[high_ready_mask]["fwd_mdd"].mean()
    low_ready_mdd = df[low_ready_mask]["fwd_mdd"].mean()

    print("\n--- v11.15 PERFORMANCE SCORECARD ---")
    print(f"1. Regime Accuracy:    {accuracy:.2%}")
    print(f"2. Brier Score:        {brier_score:.4f}")
    print(f"3. Beta Fidelity MAE:  {mae:.4f}")
    print(f"4. CDR-Risk Correlation: {corr:.4f} (p={p_val:.4f})")
    print("\n--- Risk-Adjusted Attribution (63d) ---")
    print(f"Avg Risk/Reward (High CDR): {high_ready_sortino:.4f}")
    print(f"Avg Risk/Reward (Low CDR):  {low_ready_sortino:.4f}")
    print(f"Avg Forward Max MDD (High): {high_ready_mdd:.2%}")
    print(f"Avg Forward Max MDD (Low):  {low_ready_mdd:.2%}")
    print("---------------------------------------")

if __name__ == "__main__":
    run_v11_full_system_audit()
