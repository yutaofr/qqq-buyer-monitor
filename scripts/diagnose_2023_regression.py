import logging

import pandas as pd

from src.engine.v11.conductor import V11Conductor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Forensic-2023")

def run_focused_diagnosis():
    start_date = "2023-01-01"
    end_date = "2023-06-30"

    conductor = V11Conductor(
        macro_data_path="data/macro_historical_dump.csv",
        regime_data_path="data/v11_poc_phase1_results.csv",
        prior_state_path="artifacts/v11_prior_state_backtest.json",
        price_history_path="data/qqq_history_cache.csv",
        allow_prior_bootstrap_drift=True
    )

    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")

    test_dates = macro_df[(macro_df.index >= start_date) & (macro_df.index <= end_date)].index

    diag_rows = []
    logger.info(f"Starting focused diagnosis for {len(test_dates)} trading days in 2023...")

    for dt in test_dates:
        conductor.training_cutoff = dt - pd.offsets.BDay(20)
        t0_data = macro_df.loc[[dt]]

        try:
            runtime = conductor.daily_run(t0_data)

            # Extract Feature Contributions to Likelihood (Top Drivers)
            # v13.4 supports quality_audit which contains feature-level weights
            weights = runtime.get("v13_4_diagnostics", {}).get("feature_weights", {})

            row = {
                "date": dt,
                "BUST": runtime["probabilities"]["BUST"],
                "RECOVERY": runtime["probabilities"]["RECOVERY"],
                "MID_CYCLE": runtime["probabilities"]["MID_CYCLE"],
                "entropy": runtime["entropy"],
                "tau_scaling": runtime.get("v13_4_diagnostics", {}).get("tau_factor", 10.0)
            }
            # Find strongest feature (just as a sample)
            if weights:
                top_f = max(weights, key=weights.get)
                row["top_feature"] = top_f
                row["top_f_weight"] = weights[top_f]

            diag_rows.append(row)
        except Exception as e:
            logger.error(f"Failed at {dt}: {e}")

    df_diag = pd.DataFrame(diag_rows).set_index("date")
    df_diag.to_csv("artifacts/diagnosis_2023_h1.csv")

    print("\n--- DIAGNOSIS SUMMARY: 2023 Q1-Q2 ---")
    print(df_diag[["BUST", "RECOVERY", "MID_CYCLE", "entropy"]].mean())
    print("\nCritical Days (>50% BUST):")
    print(df_diag[df_diag["BUST"] > 0.5][["BUST", "top_feature", "top_f_weight"]].head(10))

if __name__ == "__main__":
    run_focused_diagnosis()
