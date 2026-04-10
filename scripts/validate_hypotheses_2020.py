import logging

import pandas as pd

from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.v11.conductor import V11Conductor

# Setup minimal logging to stdout
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def validate_hypotheses():
    print("--- HYPOTHESIS VALIDATION: MARCH 2020 LOCK ---")

    # 1. Setup Conductor
    conductor = V11Conductor()

    # 2. Load Data
    data = load_all_baseline_data(timeout=30)
    if data.empty:
        print("Error: Macro data empty.")
        return

    # Define the "Locked" date
    target_date = pd.to_datetime("2020-03-23")  # Deep into the crash

    print(f"Original Columns: {data.columns.tolist()}")

    # Scenario A: Cold Start (Current logic in backtest: ~2 months data)
    print("\n[Scenario A] Cold Start (2020-01-01 to Target, No Renaming)")
    cold_data = data.loc["2020-01-01":target_date]
    run_daily_audit(conductor, cold_data, target_date)

    # Scenario B: Warmup Fixed (Full history, but still Raw Names)
    print("\n[Scenario B] Warmup Fixed (Full history, Raw Names)")
    warm_data = data.loc[:target_date]
    run_daily_audit(conductor, warm_data, target_date)

    # Scenario C: Full Fix (Warmup + Canonical Renaming)
    print("\n[Scenario C] Full Fix (Full history + Renaming)")
    renamed_data = data.copy()
    # Aligning with src/engine/v11/conductor.py's _v12_quality_field_specs
    # and ProbabilitySeeder's src config
    renamed_data = renamed_data.rename(
        columns={
            "BAMLH0A0HYM2": "credit_spread_bps",
            "VIXCLS": "stress_vix",  # In quality audit it maps to VIXCLS? No, check conductor
            "T10Y2Y": "liquidity_slope",
            "^VXN": "stress_vxn",
        }
    )

    # Note: real_yield is STILL MISSING. Let's see if we can still break the uniform distribution.
    run_daily_audit(conductor, renamed_data.loc[:target_date], target_date)


def run_daily_audit(conductor, df_context, dt):
    conductor.high_entropy_streak = 0
    registry = conductor.v13_4_registry
    tau = float(registry.get("inference_tau", 3.0))
    runtime_priors, _ = conductor.prior_book.runtime_priors()

    try:
        # Step 1: Seeder
        features = conductor.seeder.generate_features(df_context)
        latest_vector = features.iloc[-1:]
        f_val = latest_vector.iloc[0].to_dict()

        # Log feature presence
        non_zero = {k: round(v, 4) for k, v in f_val.items() if abs(v) > 0.0001}
        print(f"    Non-Zero Features Count: {len(non_zero)}")
        if non_zero:
            print(f"    Top Feature Signals: {list(non_zero.items())[:3]}")
        else:
            print("    ALERT: ALL FEATURES ARE ZERO (Cold Start confirmed)")

        # Step 2: Quality Veto
        from src.engine.v11.core.data_quality import (
            assess_data_quality,
            feature_reliability_weights,
        )

        latest_raw = df_context.loc[dt]
        quality_audit = assess_data_quality(
            latest_raw,
            previous_raw=None,
            registry=registry,
            field_specs=conductor._v12_quality_field_specs(),
        )

        f_weights = feature_reliability_weights(
            latest_vector=latest_vector,
            latest_raw=latest_raw,
            field_quality={
                str(name): float(payload.get("quality", 1.0))
                for name, payload in dict(quality_audit.get("fields", {})).items()
            },
            seeder_config=conductor.seeder.config,
        )

        # Check core weights
        active_weights = {k: v for k, v in f_weights.items() if v > 0.5}
        print(f"    Active Features (Quality Passed): {len(active_weights)} / {len(f_weights)}")
        if not active_weights:
            print("    ALERT: DATA QUALITY VETO (Naming mismatch confirmed)")

        # Step 3: Bayesian Inference
        posteriors, diag = conductor.inference_engine.infer_gaussian_nb_posterior(
            classifier=conductor.gnb,
            evidence_frame=latest_vector,
            runtime_priors=runtime_priors,
            weight_registry=registry,
            feature_quality_weights=f_weights,
            tau=tau,
        )

        print(
            f"    Uniform: {diag.get('was_uniform')} | Top: {max(posteriors, key=posteriors.get)} ({posteriors[max(posteriors, key=posteriors.get)]:.2%})"
        )

    except Exception as e:
        print(f"    Error: {e}")


if __name__ == "__main__":
    validate_hypotheses()
