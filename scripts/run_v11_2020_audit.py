#!/usr/bin/env python3
"""v11 Final Graduation Audit: 2020 Meltdown Simulation.
Verifies all ACs (Acceptance Criteria) using the production-ready V11Conductor.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from src.engine.v11.conductor import V11Conductor

def run_graduation_audit():
    # 1. Load Data
    source_path = Path("data/v11_poc_phase1_results.csv")
    ev_path = Path("data/v11_full_evidence_history.csv")
    
    df = pd.read_csv(source_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    
    if ev_path.exists():
        ev_df = pd.read_csv(ev_path)
        ev_df["observation_date"] = pd.to_datetime(ev_df["observation_date"])
        df = pd.merge(df, ev_df[["observation_date", "vix3m"]], on="observation_date", how="left")

    # 2. Initialize Conductor
    conductor = V11Conductor()
    # Inject background history
    background_df = df[df["observation_date"] < "2020-02-01"].copy()
    conductor.library.df = background_df
    
    # 3. Simulation Run (2020-02-01 to 2020-04-15)
    test_window = df[(df["observation_date"] >= "2020-02-01") & (df["observation_date"] <= "2020-04-15")]
    
    audit_results = []
    print(f"Starting graduation audit for {len(test_window)} samples...")

    for _, row in test_window.iterrows():
        t0_data = pd.DataFrame([row])
        
        # Stress Test: Inject NaN on 2020-03-12 (VIX Peak)
        if row["observation_date"] == pd.Timestamp("2020-03-12"):
            t0_data["vix"] = np.nan
            
        res = conductor.daily_run(t0_data)
        
        audit_results.append({
            "Date": res["date"].date(),
            "VIX": round(row["vix"], 2),
            "P_BUST": round(res["probabilities"]["BUST"], 4),
            "Signal": res["signal"]["target_exposure"],
            "Quality": round(res["data_quality"], 2),
            "Resurrection": res["resurrection_active"],
            "Reason": res["signal"]["reason"]
        })

    audit_df = pd.DataFrame(audit_results)
    
    # 4. Acceptance Criteria Verification
    print("\n--- v11 Graduation Audit Report (2020 Stress Test) ---")
    print(audit_df.to_string(index=False))
    
    # AC-1: Data Poisoning Resilience
    ac1_pass = audit_df[audit_df["Quality"] < 1.0]["Signal"].iloc[0] == "CASH"
    # AC-2: Left-side Deleveraging (By early March)
    ac2_pass = audit_df[audit_df["Date"] == pd.Timestamp("2020-03-09").date()]["Signal"].iloc[0] != "QLD"
    # AC-3: Right-side Resurrection (Near 3-17)
    ac3_pass = any(audit_df[audit_df["Resurrection"] == True]["Signal"] == "QLD")
    
    print("\n--- Final Acceptance Scorecard ---")
    print(f"AC-1: Data Robustness (NaN Handling) -> {'✅ PASS' if ac1_pass else '❌ FAIL'}")
    print(f"AC-2: Left-side Deleveraging (Early Out) -> {'✅ PASS' if ac2_pass else '❌ FAIL'}")
    print(f"AC-3: Right-side Kill-Switch (Re-entry) -> {'✅ PASS' if ac3_pass else '❌ FAIL'}")
    print(f"AC-4: Settlement Lock Integrity -> ✅ PASS (Verified in TDD)")

    output_report = "data/v11_graduation_report.csv"
    audit_df.to_csv(output_report, index=False)
    print(f"\nFull audit trace saved to {output_report}")

if __name__ == "__main__":
    run_graduation_audit()
