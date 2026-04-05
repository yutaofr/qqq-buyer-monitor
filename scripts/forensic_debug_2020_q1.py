import logging
import os

import numpy as np
import pandas as pd

from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.v11.conductor import V11Conductor

# Setup minimal logging to stdout
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run_forensic():
    print("--- BAYESIAN FORENSIC TRACE: MARCH 2020 ---")

    # 1. Initialize Conductor
    os.environ["ADAPTIVE_TAU_OVERRIDE"] = "OFF" # Ensure clean run
    conductor = V11Conductor()

    # 2. Load Data
    data = load_all_baseline_data(timeout=30)
    if data.empty:
        print("Error: Macro data empty.")
        return

    # Period of interest: Just before and during the lock
    test_dates = ["2020-02-20", "2020-03-02", "2020-03-09", "2020-03-16", "2020-03-23", "2020-03-30"]

    # Pre-calculate all features once for the full dataset to use in diagnostics
    all_features = conductor.seeder.generate_features(data)

    for date_str in test_dates:
        dt = pd.to_datetime(date_str)
        if dt not in data.index:
            # Find nearest date
            dt = data.index[data.index <= dt][-1]

        print(f"\n>>> AUDIT DATE: {dt.date()}")

        # Reset conductor state to ensure clean run
        conductor.high_entropy_streak = 0

        # Use daily_run features to be exact
        runtime = conductor.daily_run(data.loc[:dt])

        latest_vector = all_features.loc[[dt]]

        # 3. Inspect intermediates from daily_run (via side-channel)
        posteriors = runtime["probabilities"]
        diagnostics = runtime["v13_4_diagnostics"]

        print(f"  Entropy: {runtime['entropy']:.4f}")
        print(f"  Evidence Uniform: {diagnostics.get('was_uniform')}")
        print(f"  Top Posteriors: { {k: round(v, 4) for k, v in list(posteriors.items())[:2]} }")

        eff_weights = diagnostics.get("effective_weights", {})

        # Pick a core feature: real_yield_structural_z
        f_name = "real_yield_structural_z"
        w_eff = eff_weights.get(f_name, "N/A")

        # Get quality weight for this feature
        # Feature weights are calculated in conductor and used in inference
        # Let's check the diagnostics from inference_engine

        val = latest_vector[f_name].iloc[0]
        print(f"  Feature [{f_name}]: vector_val={val:.4f}, weight_eff={w_eff}")

        # Check Gaussian params for this feature for "BUST" regime
        if "BUST" in conductor.gnb.classes_:
            bust_idx = list(conductor.gnb.classes_).index("BUST")
            theta = conductor.gnb.theta_[bust_idx][all_features.columns.get_loc(f_name)]
            var = conductor.gnb.var_[bust_idx][all_features.columns.get_loc(f_name)]
            print(f"  BUST Params for [{f_name}]: theta={theta:.4f}, var={var:.4f}")

            # Manual calc of log-lh
            feat_log_lh = -0.5 * (np.log(2.0 * np.pi * var) + ((val - theta) ** 2) / var)
            print(f"  Raw Log-LH for [{f_name}] in BUST: {feat_log_lh:.4f}")

if __name__ == "__main__":
    run_forensic()
