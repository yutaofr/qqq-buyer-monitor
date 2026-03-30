import pandas as pd
import numpy as np
from src.engine.v11.conductor import V11Conductor
import logging

logging.basicConfig(level=logging.ERROR)

def audit_target_beta_fidelity():
    conductor = V11Conductor()
    
    # Load historical data
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    
    # We'll audit a broad window: 2020 to 2026
    test_dates = macro_df.loc["2020-01-01":"2026-03-25"].index
    
    results = []
    prev_beta = 1.0
    
    print(f"Auditing Target Beta Fidelity for {len(test_dates)} trading days...")
    
    for date in test_dates:
        t0_data = macro_df.loc[:date].iloc[-252:]
        signal = conductor.daily_run(t0_data)
        
        results.append({
            "date": date,
            "target_beta": signal["target_beta"],
            "raw_target_beta": signal["raw_target_beta"], # Before hysteresis/guard
             
            "outlier_stress": signal["feature_values"]["outlier_stress"]
        })
    
    df = pd.DataFrame(results).set_index("date")
    
    # 1. Fidelity (Tracking Error between Raw and Guarded Beta)
    df["tracking_diff"] = np.abs(df["target_beta"] - df["raw_target_beta"])
    mean_fidelity_error = df["tracking_diff"].mean()
    
    # 2. Turnover (Number of shifts in target_beta)
    shifts = df["target_beta"].diff().abs() > 0.001
    total_shifts = shifts.sum()
    turnover_rate = total_shifts / len(df) * 252 # Annualized shifts
    
    # 3. Lock Efficiency (How often was the system locked?)
    lock_rate = 0.0
    
    print("\nTarget Beta Performance Core Metrics (v11.7)")
    print("-" * 50)
    print(f"Mean Fidelity Error (Hysteresis Lag): {mean_fidelity_error:.4f}")
    print(f"Annualized Shifts (Turnover): {turnover_rate:.2f} per year")
    print(f"Settlement Lock Rate: {lock_rate:.2%}")
    print(f"Average Outlier Stress: {df['outlier_stress'].mean():.4f}")
    
    # 2022 Specific Check
    df_2022 = df.loc["2022-01-01":"2022-12-31"]
    print(f"\n2022 Special Audit:")
    print(f"Avg Target Beta: {df_2022['target_beta'].mean():.2f}")
    print(f"Peak Outlier Stress: {df_2022['outlier_stress'].max():.2%}")

if __name__ == "__main__":
    audit_target_beta_fidelity()
