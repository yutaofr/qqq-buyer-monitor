import logging
import os

import pandas as pd

from src.backtest import run_v11_audit
from src.engine.v11.probability_seeder import ProbabilitySeeder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_era_audit():
    """
    Forensic Era Segmentation Audit.
    1. Automated Pivot Discovery: Sweep split years to find the structural break.
    2. Per-Factor Sensitivity: Identify which factors drift most.
    """
    pivot_years = [2012, 2015, 2018, 2020]
    pivot_results = []

    seeder_base = ProbabilitySeeder()
    all_features = seeder_base.feature_names()

    # --- Part 1: Pivot Discovery ---
    logger.info("=== Phase 1: Automated Pivot Discovery ===")
    for year in pivot_years:
        split_date = f"{year}-01-01"
        logger.info(f"Auditing Era Post-{year} with default Expanding memory...")

        try:
            summary = run_v11_audit(
                evaluation_start=split_date,
                artifact_dir=f"artifacts/era_audit/pivot_{year}",
                experiment_config={"save_plots": False},
                strict_state_support=False,
            )
            pivot_results.append(
                {
                    "pivot_year": year,
                    "accuracy": summary["top1_accuracy"],
                    "brier": summary["mean_brier"],
                    "entropy": summary["mean_entropy"],
                }
            )
        except Exception as e:
            logger.error(f"Pivot {year} failed: {e}")

    pivot_df = pd.DataFrame(pivot_results)
    print("\n--- Pivot Discovery Results ---")
    print(pivot_df.to_string(index=False))

    # --- Part 2: Factor Sensitivity (Using 2018 as base) ---
    # Based on user intuition that 2018 is the break
    base_year = 2018
    logger.info(f"\n=== Phase 2: Per-Factor Sensitivity (Era: {base_year}+) ===")

    # Baseline: All Expanding
    factor_results = []

    for factor in all_features:
        logger.info(f"Testing Rolling Window (756d) for FACTOR: {factor} ...")

        # Override ONLY this factor to rolling
        overrides = {f: {"z_method": "expanding"} for f in all_features}
        overrides[factor] = {"z_method": "rolling", "z_window": 756}

        try:
            summary = run_v11_audit(
                evaluation_start=f"{base_year}-01-01",
                artifact_dir=f"artifacts/era_audit/factor_{factor}",
                experiment_config={
                    "probability_seeder": {"config_overrides": overrides},
                    "save_plots": False,
                },
                strict_state_support=False,
            )
            factor_results.append(
                {
                    "factor": factor,
                    "acc_gain": summary["top1_accuracy"],
                    "brier_gain": summary["mean_brier"],
                }
            )
        except Exception as e:
            logger.error(f"Factor {factor} audit failed: {e}")

    factor_df = pd.DataFrame(factor_results).sort_values("brier_gain")
    print("\n--- Factor Sensitivity Results (Rolling 756d Impact) ---")
    print(factor_df.to_string(index=False))

    os.makedirs("artifacts/era_audit", exist_ok=True)
    pivot_df.to_csv("artifacts/era_audit/pivot_discovery.csv", index=False)
    factor_df.to_csv("artifacts/era_audit/factor_sensitivity.csv", index=False)


if __name__ == "__main__":
    run_era_audit()
