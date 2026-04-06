import logging

import pandas as pd

from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.v11.conductor import V11Conductor

# Setup minimal logging to stdout
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run_era_probe():
    print("--- BAYESIAN FORENSIC ERA PROBE (v14.4 Overdrive) ---")

    # Era Definitions: (Name, Test Dates, Training Cutoff)
    eras = [
        ("2008 GFC (Crisis)", ["2008-09-15", "2008-10-06", "2008-10-15", "2008-11-20"], "2008-01-01"),
        ("2017 (Stable)", ["2017-06-15", "2017-09-15", "2017-12-15"], "2016-12-31"),
        ("2022 (Bear Grind)", ["2022-01-20", "2022-05-20", "2022-09-20"], "2021-12-31")
    ]

    # Load Data once
    full_data = load_all_baseline_data(timeout=30)
    if full_data.empty:
        print("Error: Macro data empty.")
        return

    results = []

    for era_name, test_dates, cutoff in eras:
        print(f"\n=== ERA: {era_name} (Cutoff: {cutoff}) ===")

        # Initialize Conductor for this era
        try:
            conductor = V11Conductor(training_cutoff=cutoff)
        except Exception as e:
            print(f"Error initializing conductor for era {era_name}: {e}")
            continue

        for date_str in test_dates:
            dt = pd.to_datetime(date_str)
            if dt not in full_data.index:
                # Find nearest date
                dt = full_data.index[full_data.index <= dt][-1]

            # Run daily loop
            runtime = conductor.daily_run(full_data.loc[:dt])

            # Extract Overdrive Status
            latest_vector = conductor.seeder.generate_features(full_data.loc[:dt]).iloc[-1:]
            is_ood, d_m = conductor.mahalanobis_guard.is_outlier(
                latest_vector.iloc[0].values,
                threshold=float(conductor.v13_4_registry.get("mahalanobis_ood_threshold", 4.5)),
                return_distance=True
            )

            posteriors = runtime["probabilities"]
            top_regime = max(posteriors, key=posteriors.get)

            print(f"  [{dt.date()}] d_m={d_m:.2f}, Overdrive={is_ood}, Top={top_regime} ({posteriors[top_regime]:.4f})")

            results.append({
                "era": era_name,
                "date": dt.date(),
                "d_m": d_m,
                "is_ood": is_ood,
                "top_regime": top_regime,
                "prob": posteriors[top_regime]
            })

    # Summary Check for False Positives
    print("\n--- FINAL ROBUSTNESS AUDIT ---")
    fp_check = [r for r in results if r["era"] == "2017 (Stable)" and r["is_ood"]]
    if not fp_check:
        print("PASS: Zero False Positives in 2017 Stable Era.")
    else:
        print(f"FAIL: {len(fp_check)} False Positives detected in 2017!")

    tp_check = [r for r in results if r["era"] == "2008 GFC (Crisis)" and r["is_ood"]]
    if tp_check:
        print(f"PASS: Crisis detected in {len(tp_check)}/4 dates in 2008.")
    else:
        print("FAIL: Zero Crisis detections in 2008!")

if __name__ == "__main__":
    run_era_probe()
