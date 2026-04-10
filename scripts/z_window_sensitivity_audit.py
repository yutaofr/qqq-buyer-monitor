import logging
import os

import pandas as pd

from src.backtest import run_v11_audit
from src.engine.v11.probability_seeder import ProbabilitySeeder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_sensitivity_audit():
    """
    Forensic Audit: Sensitivity analysis of Z-Score Windows.
    Objective: '验证先于结论' (Validation before conclusion).
    Compare the impact of different window sizes on Bayesian Regime Inference.
    """
    windows = [1260, "expanding"]
    results = []

    seeder_base = ProbabilitySeeder()
    feature_names = seeder_base.feature_names()

    for window in windows:
        logger.info(f"--- Auditing Z-Window: {window} ---")

        # Build overrides for all features
        overrides = {}
        for feature in feature_names:
            if window == "expanding":
                overrides[feature] = {"z_method": "expanding"}
            else:
                overrides[feature] = {"z_method": "rolling", "z_window": window}

        experiment_config = {
            "probability_seeder": {"config_overrides": overrides},
            "save_plots": False,
            "artifact_dir": f"artifacts/sensitivity_audit/window_{window}",
        }

        try:
            summary = run_v11_audit(
                evaluation_start="2018-01-01",
                artifact_dir=f"artifacts/sensitivity_audit/window_{window}",
                experiment_config=experiment_config,
                strict_state_support=False,
            )

            summary["window"] = str(window)
            results.append(summary)
            logger.info(
                f"Window {window} completed. Accuracy: {summary['top1_accuracy']:.2%}, Brier: {summary['mean_brier']:.4f}"
            )

        except Exception as e:
            logger.error(f"Audit failed for window {window}: {e}")
            import traceback

            traceback.print_exc()

    # 3. Report Generation
    report_df = pd.DataFrame(results)
    cols = [
        "window",
        "top1_accuracy",
        "mean_brier",
        "mean_entropy",
        "lock_incidence",
        "target_beta_min",
    ]
    report_df = report_df[cols]

    print("\n--- Z-Window Sensitivity Audit Report ---")
    print(report_df.to_string(index=False))

    # Save results
    os.makedirs("artifacts/sensitivity_audit", exist_ok=True)
    report_df.to_csv("artifacts/sensitivity_audit/report.csv", index=False)

    # Find optimal
    # Typically we want High Accuracy, Low Brier, and moderate Entropy (not locked at 1.0 or 0.0)
    best_brier = report_df.loc[report_df["mean_brier"].idxmin()]
    logger.info(
        f"Optimal Window by Brier Score: {best_brier['window']} (Brier: {best_brier['mean_brier']:.4f})"
    )


if __name__ == "__main__":
    run_sensitivity_audit()
