import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.probability_seeder import ProbabilitySeeder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_tau_sweep():
    dataset_path = "data/macro_historical_dump.csv"
    regime_path = "data/v11_poc_phase1_results.csv"
    evaluation_start = "2023-01-01"  # Forensic slice

    macro_df = pd.read_csv(dataset_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )
    regime_df = pd.read_csv(regime_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )

    full_df = macro_df.join(regime_df["regime"], how="inner")
    full_df.index.name = "observation_date"
    full_df = full_df.reset_index().sort_values("observation_date").reset_index(drop=True)

    eval_start = pd.to_datetime(evaluation_start)
    test = full_df[full_df["observation_date"] >= eval_start].copy()
    if len(test) > 100:
        test = test.iloc[:100]  # Use 100 samples for speed

    seeder = ProbabilitySeeder()
    feature_cols = seeder.feature_names()

    # Load registry for base weights
    registry_path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
    with open(registry_path) as f:
        registry = json.load(f)

    tau_values = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]
    results = []

    for tau in tau_values:
        brier_scores = []
        logger.info(f"Evaluating tau={tau}...")

        for _, row in test.iterrows():
            dt = row["observation_date"]
            train_window = full_df[full_df["observation_date"] < dt].copy()

            # Simplified walk-forward for forensic sweep
            # We use a static window for speed if possible, but let's stick to causal fit
            gnb = GaussianNB(var_smoothing=1e-2)
            # Generate features for window
            context_df = pd.concat([train_window, pd.DataFrame([row])]).set_index(
                "observation_date"
            )
            features_context = seeder.generate_features(context_df)

            train_features = features_context.iloc[:-1]
            latest_features = features_context.iloc[-1:]

            gnb.fit(train_features[feature_cols], train_window["regime"])

            engine = BayesianInferenceEngine(
                {}, {str(c): 1.0 / len(gnb.classes_) for c in gnb.classes_}
            )

            priors = {
                str(label): float(prob)
                for label, prob in zip(gnb.classes_, gnb.class_prior_, strict=True)
            }

            posteriors, _ = engine.infer_gaussian_nb_posterior(
                classifier=gnb,
                evidence_frame=latest_features[feature_cols],
                runtime_priors=priors,
                weight_registry=registry,
                tau=tau,
            )

            actual = str(row["regime"])
            brier = sum(
                (posteriors.get(r, 0.0) - (1.0 if r == actual else 0.0)) ** 2
                for r in gnb.classes_.astype(str)
            )
            brier_scores.append(brier)

        avg_brier = np.mean(brier_scores)
        results.append({"tau": tau, "mean_brier": avg_brier})
        logger.info(f"  Mean Brier: {avg_brier:.4f}")

    print("\n--- Bayesian Tau Sensitivity Sweep ---")
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

    # Save to artifacts
    save_path = Path("artifacts/forensic_audit/tau_sweep_results.json")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    run_tau_sweep()
