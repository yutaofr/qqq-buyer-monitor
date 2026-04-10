"""
QQQ v11 production-black-box backtest and audit entrypoint.

This module replays the live conductor against frozen historical inputs.
Backtests must not re-implement the production inference chain.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from src.engine.v11.core.expectation_surface import (
    deployment_cash_notional,
    deployment_state_rank,
    expected_policy_for_regime,
)
from src.engine.v11.core.price_topology import (
    align_posteriors_with_recovery_process,  # noqa: F401
    topology_likelihood_penalties,  # noqa: F401
)
from src.engine.v13.execution_overlay import ExecutionOverlayEngine
from src.regime_dynamics import flatten_probability_dynamics
from src.regime_topology import canonicalize_regime_sequence, merge_regime_weights
from src.research.data_contracts import (
    find_first_supported_evaluation_start,
    summarize_regime_state_support,
    validate_regime_state_support,
)
from src.research.regime_process_audit import compute_regime_process_alignment
from src.research.worldview_benchmark import build_worldview_benchmark

logger = logging.getLogger(__name__)

START_DATE = "1999-03-10"


def _resolve_process_entropy(runtime: dict[str, Any]) -> float:
    quality_audit = dict(runtime.get("quality_audit", {}))
    return float(quality_audit.get("posterior_entropy", runtime.get("entropy", 0.0)))


def _resolve_execution_entropy(runtime: dict[str, Any]) -> float:
    quality_audit = dict(runtime.get("quality_audit", {}))
    return float(quality_audit.get("effective_entropy", runtime.get("entropy", 0.0)))


def _load_price_history(
    cache_path: str,
    *,
    allow_download: bool = False,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Load cached QQQ history, downloading only when explicitly allowed."""
    print(f"Loading QQQ history from {cache_path}...")

    qqq = pd.DataFrame()
    if os.path.exists(cache_path):
        try:
            qqq = pd.read_csv(cache_path, index_col=0)
            if not qqq.empty:
                qqq.index = pd.to_datetime(qqq.index, utc=True)
                last_cached = qqq.index[-1].date().isoformat()
                print(f"Successfully loaded {len(qqq)} rows (Last date: {last_cached})")
        except Exception as exc:
            print(f"Cache read failed: {exc}")

    if qqq.empty and not allow_download:
        raise FileNotFoundError(
            f"Frozen QQQ history missing at {cache_path}. Acceptance mode refuses live downloads."
        )

    if qqq.empty:
        if not end_date:
            raise ValueError(
                "Live price refresh requires an explicit pinned end_date to avoid moving-window drift."
            )
        print(f"Downloading fresh data from yfinance since {cache_path} was missing or empty...")
        qqq = yf.Ticker("QQQ").history(start=START_DATE, end=end_date)
        if not qqq.empty:
            os.makedirs("data", exist_ok=True)
            qqq.to_csv(cache_path)
            print(f"Cache updated: {cache_path}")

    if end_date:
        cutoff = pd.to_datetime(end_date, utc=True).normalize()
        if not qqq.empty:
            qqq.index = pd.to_datetime(qqq.index, utc=True)
            qqq = qqq[qqq.index <= cutoff]

    if qqq.empty:
        raise ValueError("No price data available.")

    return qqq


def _v11_inference_task(
    row_data: tuple[pd.Series, pd.Series, Any, list[str], list[str]],
) -> dict[str, Any]:
    """Independent worker task for v12.0 Bayesian inference."""
    from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine

    std_row, source_row, gnb_model, classes, feature_cols = row_data

    evidence = pd.DataFrame([std_row[feature_cols].to_dict()], columns=feature_cols)

    # Use BayesianInferenceEngine for correct Bayesian evaluation
    engine = BayesianInferenceEngine(kde_models={}, base_priors={})

    # To pass down active priors, we assume base priors initially if runtime is not available
    base_priors = {str(c): 1.0 / len(classes) for c in classes}

    registry_path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
    else:
        registry = {}

    posterior, _ = engine.infer_gaussian_nb_posterior(
        classifier=gnb_model,
        evidence_frame=evidence,
        runtime_priors=base_priors,
        weight_registry=registry,
        tau=float(registry.get("inference_tau", 3.0)),
    )

    actual_regime = str(std_row.get("regime", source_row.get("regime", "MID_CYCLE")))
    predicted_regime = max(posterior, key=posterior.get)

    brier = sum(
        (posterior.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2
        for name in classes
    )

    return {
        "date": std_row["observation_date"],
        "actual_regime": actual_regime,
        "actual_regime_probability": float(posterior.get(actual_regime, 0.0)),
        "predicted_regime": predicted_regime,
        "brier": brier,
        "posterior": posterior,
        "test_type": "UNKNOWN" # Will be updated in loop
    }


def _v12_quality_field_specs() -> dict[str, tuple[str, str, str | None]]:
    return {
        "credit_spread": ("credit_spread_bps", "source_credit_spread", None),
        "net_liquidity": ("net_liquidity_usd_bn", "source_net_liquidity", None),
        "real_yield": ("real_yield_10y_pct", "source_real_yield", None),
        "treasury_vol": ("treasury_vol_21d", "source_treasury_vol", None),
        "copper_gold": ("copper_gold_ratio", "source_copper_gold", None),
        "breakeven": ("breakeven_10y", "source_breakeven", None),
        "core_capex": ("core_capex_mm", "source_core_capex", None),
        "usdjpy": ("usdjpy", "source_usdjpy", None),
        "erp_ttm": ("erp_ttm_pct", "source_erp_ttm", None),
    }


def run_v11_audit(
    *,
    dataset_path: str = "data/macro_historical_dump.csv",
    regime_path: str = "data/v11_poc_phase1_results.csv",
    evaluation_start: str = "2018-01-01",
    artifact_dir: str = "artifacts/v12_audit",
    strict_state_support: bool = False,
    experiment_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay the production conductor on frozen historical inputs."""
    import numpy as np

    # v14.0 INDUSTRIAL REPRODUCIBILITY: Fixed seed for all ML/Stochastic components
    np.random.seed(42)

    from src.engine.v11.core.model_validation import validate_feature_contract
    from src.engine.v11.probability_seeder import ProbabilitySeeder
    from src.output.backtest_plots import (
        save_v11_fidelity_figure,
        save_v11_probabilistic_audit_figure,
    )
    from src.research.data_contracts import (
        summarize_regime_state_support,
        validate_regime_state_support,
    )

    dataset = Path(dataset_path)
    regimes_file = Path(regime_path)
    if not dataset.exists():
        raise FileNotFoundError(
            f"Canonical macro DNA missing at {dataset}. Walk-forward audit requires checked-in baseline data."
        )
    if not regimes_file.exists():
        raise FileNotFoundError(
            f"Canonical regime DNA missing at {regimes_file}. Walk-forward audit requires checked-in baseline labels."
        )

    macro_df = pd.read_csv(dataset_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )
    regime_df = pd.read_csv(regime_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )
    experiment = dict(experiment_config or {})

    if experiment.get("use_canonical_pipeline", True) is False:
        raise ValueError(
            "Legacy backtest re-implementations are retired. Audits must replay V11Conductor."
        )

    disallowed_experiment_keys = {
        "audit_overrides",
        "posterior_mode",
        "probability_seeder",
        "var_smoothing",
    }
    invalid_experiment_keys = sorted(
        key for key in disallowed_experiment_keys if key in experiment
    )
    if invalid_experiment_keys:
        raise ValueError(
            "run_v11_audit only accepts production-chain controls. "
            f"Disallowed overrides: {', '.join(invalid_experiment_keys)}"
        )

    audit_path = Path("src/engine/v11/resources/regime_audit.json")
    with open(audit_path, encoding="utf-8") as f:
        audit_data = json.load(f)
    base_betas = dict(audit_data["base_betas"])
    regime_sharpes = dict(audit_data["regime_sharpes"])
    ordered_regimes = canonicalize_regime_sequence(base_betas.keys(), include_all=False)
    base_betas = merge_regime_weights(base_betas, regimes=ordered_regimes, include_zeros=True)
    regime_sharpes = merge_regime_weights(
        regime_sharpes, regimes=ordered_regimes, include_zeros=True
    )
    default_var_smoothing = float(
        audit_data.get("model_hyperparameters", {}).get("gaussian_nb_var_smoothing", 1e-2)
    )
    posterior_mode = str(
        audit_data.get("model_hyperparameters", {}).get("posterior_mode", "runtime_reweight")
    )

    # v14.5 INDUSTRIAL GOVERNANCE: Load registry once for the entire audit
    registry_path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
    if registry_path.exists():
        with open(registry_path) as f:
            json.load(f)
    overlay_mode = experiment.get("overlay_mode")
    price_cache_path = str(experiment.get("price_cache_path", "data/qqq_history_cache.csv"))
    allow_price_download = bool(experiment.get("allow_price_download", False))
    price_end_date = experiment.get("price_end_date")
    use_canonical_pipeline = True
    state_support = summarize_regime_state_support(regime_df, audit_regimes=ordered_regimes)
    support_ready_eval_dt = find_first_supported_evaluation_start(
        regime_df,
        audit_regimes=ordered_regimes,
        training_lookback_bdays=20,
    )
    if support_ready_eval_dt is None:
        raise ValueError(
            "Audit regime contract never reaches support-ready evaluation_start for all configured regimes."
        )
    if strict_state_support:
        validate_regime_state_support(regime_df, audit_regimes=ordered_regimes)

    price_df = _load_price_history(
        price_cache_path,
        allow_download=allow_price_download,
        end_date=price_end_date,
    )
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_localize(None).normalize()

    # v14.0 INDUSTRIAL PIT AUDIT: Reindex macro data onto the canonical trading calendar
    # This prevents temporal contamination by ensuring macro data is only visible on trading days
    # and subsequent ffill() honors the daily close sequence correctly.
    trading_calendar = price_df.index
    macro_df.index = pd.to_datetime(macro_df.index).tz_localize(None).normalize()
    macro_df = macro_df.reindex(trading_calendar).ffill()

    macro_df["qqq_close"] = price_df["Close"]
    if "Volume" in price_df.columns:
        macro_df["qqq_volume"] = pd.to_numeric(price_df["Volume"], errors="coerce")
        macro_df["source_qqq_volume"] = "direct:yfinance"
        macro_df["qqq_volume_quality_score"] = 1.0
    macro_df["source_qqq_close"] = "direct:yfinance"
    macro_df["qqq_close_quality_score"] = 1.0

    # v14.9 CAUSAL ISOLATION GUARD: Enforce minimum training window
    # The longest structural anchor is 1260 days (~5 years).
    # Any audit starting before this threshold will have high-entropy noise.
    eval_dt = pd.to_datetime(evaluation_start).tz_localize(None).normalize()
    min_train_cutoff = macro_df.index[0] + pd.offsets.BDay(1260)

    if eval_dt < min_train_cutoff:
        logger.warning(
            f"CAUSAL VIOLATION: evaluation_start {evaluation_start} is before "
            f"the 5-year structural anchor threshold ({min_train_cutoff.date()}). "
            "Audit results will be contaminated by initialization noise."
        )
        if strict_state_support:
             raise ValueError("Strict Causal Isolation failed: Insufficient training data for 5-year anchor.")

    effective_eval_dt = max(eval_dt, pd.Timestamp(support_ready_eval_dt).normalize())
    if effective_eval_dt > eval_dt:
        logger.warning(
            "evaluation_start %s tightened to first full-support date %s",
            eval_dt.date().isoformat(),
            effective_eval_dt.date().isoformat(),
        )

    seeder_kwargs: dict[str, Any] = {}
    if "selected_features" not in seeder_kwargs:
        contract_features = audit_data.get("feature_contract", {}).get("feature_names")
        if contract_features:
            seeder_kwargs["selected_features"] = list(contract_features)

    seeder = ProbabilitySeeder(**seeder_kwargs)
    feature_contract_validation = "validated"
    try:
        validate_feature_contract(
            expected_hash=audit_data.get("feature_contract", {}).get("seeder_config_hash"),
            actual_hash=seeder.contract_hash(),
            expected_features=audit_data.get("feature_contract", {}).get("feature_names"),
            actual_features=seeder.feature_names(),
        )
    except ValueError as exc:
        if experiment:
            feature_contract_validation = f"override:{exc}"
        else:
            raise

    # v14.0 CAUSAL PIPELINE: Features are generated INSIDE the walk-forward loop to prevent "Shadow Leakage"
    # We join labels and macro inputs into a raw container first.
    full_df = macro_df.join(regime_df["regime"], how="inner")

    # Preserve raw macro inputs and provenance
    quality_fields = {"build_version"}
    for value_key, source_key, quality_key in _v12_quality_field_specs().values():
        quality_fields.add(str(value_key))
        if source_key:
            quality_fields.add(str(source_key))
        if quality_key:
            quality_fields.add(str(quality_key))
    for col in sorted(quality_fields):
        if col in macro_df.columns:
            full_df[col] = macro_df[col]

    # Add overlay signals
    for col in [
        "adv_dec_ratio",
        "source_breadth_proxy",
        "breadth_quality_score",
        "ndx_concentration",
        "source_ndx_concentration",
        "ndx_concentration_quality_score",
    ]:
        if col in macro_df.columns:
            full_df[col] = macro_df[col]

    if "erp_ttm_pct" in macro_df.columns:
        full_df["erp_ttm_pct"] = pd.to_numeric(macro_df["erp_ttm_pct"], errors="coerce")

    full_df.index.name = "observation_date"
    full_df = full_df.reset_index().sort_values("observation_date").reset_index(drop=True)

    eval_start = effective_eval_dt
    train = full_df[full_df["observation_date"] < eval_start].copy()
    test = full_df[full_df["observation_date"] >= eval_start].copy()

    if train.empty:
        raise ValueError(f"No pre-evaluation history available before {evaluation_start}.")
    if test.empty:
        raise ValueError(f"No evaluation rows available on or after {evaluation_start}.")

    logger.info(
        f"v12 Audit: Training on {len(train)} days (pre-{evaluation_start}), testing on {len(test)} days."
    )

    active_feature_names = list(seeder.feature_names())

    def _finalize_artifacts(
        probability_rows: list[dict[str, Any]],
        execution_rows: list[dict[str, Any]],
        *,
        forensic_rows: list[dict[str, Any]] | None = None,
        training_class_counts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        probability_df = pd.DataFrame(probability_rows).sort_values("date")
        execution_df = pd.DataFrame(execution_rows).sort_values("date")
        full_audit_df = pd.merge(
            execution_df,
            probability_df,
            on=["date", "predicted_regime", "actual_regime"],
            how="left",
        )
        oos_probability_df = probability_df.loc[probability_df["test_type"] == "TEST_OOS"].copy()
        oos_execution_df = execution_df.loc[
            execution_df["date"].isin(oos_probability_df["date"])
        ].copy()
        training_support_df = pd.DataFrame(training_class_counts or []).sort_values("date")
        if not training_support_df.empty:
            full_support_mask = training_support_df["class_count"] >= len(ordered_regimes)
            first_full_support_date = (
                pd.Timestamp(training_support_df.loc[full_support_mask, "date"].iloc[0]).date().isoformat()
                if bool(full_support_mask.any())
                else None
            )
        else:
            full_support_mask = pd.Series(dtype=bool)
            first_full_support_date = None

        summary = {
            "compared_points": int(len(probability_df)),
            "top1_accuracy": float(
                (probability_df["predicted_regime"] == probability_df["actual_regime"]).mean()
            ),
            "mean_brier": float(probability_df["brier"].mean()),
            "mean_entropy": float(execution_df["entropy"].mean()),
            "lock_incidence": float(execution_df["lock_active"].mean()),
            "state_support": state_support,
            "audit_regimes": ordered_regimes,
            "feature_contract_validation": feature_contract_validation,
            "experiment_config": experiment,
            "evaluation_start_requested": pd.Timestamp(eval_dt).date().isoformat(),
            "evaluation_start_effective": pd.Timestamp(eval_start).date().isoformat(),
            "gaussian_nb_var_smoothing": default_var_smoothing,
            "posterior_mode": posterior_mode,
            "overlay_mode": str(overlay_mode or ExecutionOverlayEngine().default_mode),
            "active_features": active_feature_names,
            "beta_expectation_mae": float(
                (execution_df["target_beta"] - execution_df["expected_target_beta"]).abs().mean()
            ),
            "raw_beta_expectation_mae": float(
                (execution_df["raw_target_beta"] - execution_df["expected_target_beta"]).abs().mean()
            ),
            "deployment_exact_match": float(
                (
                    execution_df["deployment_state"] == execution_df["expected_deployment_state"]
                ).mean()
            ),
            "deployment_rank_abs_error_mean": float(
                execution_df["deployment_rank_abs_error"].mean()
            ),
            "deployment_pacing_abs_error_mean": float(
                execution_df["deployment_pacing_error"].abs().mean()
            ),
            "deployment_pacing_signed_mean": float(
                execution_df["deployment_pacing_error"].mean()
            ),
            "raw_floor_breach_rate": float((execution_df["raw_target_beta"] < 0.5).mean()),
            "expectation_floor_breach_rate": float(
                (execution_df["beta_expectation"] < 0.5).mean()
            ),
            "target_floor_breach_rate": float((execution_df["target_beta"] < 0.5).mean()),
            "raw_beta_min": float(execution_df["raw_target_beta"].min()),
            "beta_expectation_min": float(execution_df["beta_expectation"].min()),
            "target_beta_min": float(execution_df["target_beta"].min()),
            "raw_beta_within_5pct_expected": float(
                (
                    (execution_df["raw_target_beta"] - execution_df["expected_target_beta"]).abs()
                    <= 0.05
                ).mean()
            ),
            "target_beta_within_5pct_expected": float(
                (
                    (execution_df["target_beta"] - execution_df["expected_target_beta"]).abs()
                    <= 0.05
                ).mean()
            ),
            "share_at_floor": float((execution_df["target_beta"] <= 0.500001).mean()),
            "canonical_pipeline": bool(use_canonical_pipeline),
            "mid_cycle_gt_075_rate": float(
                (probability_df["prob_MID_CYCLE"] > 0.75).mean()
            )
            if "prob_MID_CYCLE" in probability_df
            else None,
            "bust_beta_le_060_rate": float(
                (
                    execution_df.loc[execution_df["actual_regime"] == "BUST", "target_beta"] <= 0.60
                ).mean()
            )
            if (execution_df["actual_regime"] == "BUST").any()
            else None,
            "oos_compared_points": int(len(oos_probability_df)),
            "oos_top1_accuracy": float(
                (oos_probability_df["predicted_regime"] == oos_probability_df["actual_regime"]).mean()
            )
            if not oos_probability_df.empty
            else None,
            "oos_mean_brier": float(oos_probability_df["brier"].mean())
            if not oos_probability_df.empty
            else None,
            "oos_mean_entropy": float(oos_execution_df["entropy"].mean())
            if not oos_execution_df.empty
            else None,
            "oos_beta_expectation_mae": float(
                (oos_execution_df["target_beta"] - oos_execution_df["expected_target_beta"]).abs().mean()
            )
            if not oos_execution_df.empty
            else None,
            "training_min_class_count": int(training_support_df["class_count"].min())
            if not training_support_df.empty
            else 0,
            "training_max_class_count": int(training_support_df["class_count"].max())
            if not training_support_df.empty
            else 0,
            "training_rows_below_full_support": int((~full_support_mask).sum())
            if not training_support_df.empty
            else 0,
            "training_first_full_support_date": first_full_support_date,
            "forensic_snapshot_count": int(
                execution_df.get("forensic_snapshot_path", pd.Series(dtype=str))
                .fillna("")
                .astype(str)
                .ne("")
                .sum()
            ),
        }
        benchmark = build_worldview_benchmark(price_df[["Close", "Volume"]])
        benchmark = benchmark.reset_index().rename(columns={benchmark.index.name or "index": "date"})
        regime_process_trace, regime_process_summary = compute_regime_process_alignment(
            full_audit_df,
            benchmark,
        )
        summary.update(
            {
                key: value
                for key, value in regime_process_summary["overall"].items()
                if isinstance(value, (int, float))
            }
        )

        print("\n--- v12 Unified Probabilistic Performance Audit ---")
        print(
            f"Accuracy: {summary['top1_accuracy']:.2%} | Brier: {summary['mean_brier']:.4f} | Entropy: {summary['mean_entropy']:.3f} | Lock: {summary['lock_incidence']:.1%}"
        )

        save_dir = Path(artifact_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        probability_df.to_csv(save_dir / "probability_audit.csv", index=False)
        execution_df.to_csv(save_dir / "execution_trace.csv", index=False)
        full_audit_df.to_csv(save_dir / "full_audit.csv", index=False)
        regime_process_trace.to_csv(save_dir / "regime_process_trace.csv", index=False)
        (save_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if forensic_rows:
            (save_dir / "forensic_trace.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in forensic_rows) + "\n",
                encoding="utf-8",
            )
        if bool(experiment.get("save_plots", True)):
            save_v11_fidelity_figure(
                execution_df, summary, [save_dir / "v12_target_beta_fidelity.png"]
            )
            save_v11_probabilistic_audit_figure(
                full_audit_df, summary, [save_dir / "v12_probabilistic_audit.png"]
            )

        return summary

    if use_canonical_pipeline:
        from src.engine.v11.conductor import V11Conductor

        probability_rows: list[dict[str, Any]] = []
        execution_rows: list[dict[str, Any]] = []
        forensic_rows: list[dict[str, Any]] = []
        training_class_counts: list[dict[str, Any]] = []
        runtime_state_dir = Path(artifact_dir) / "runtime_state"
        runtime_state_dir.mkdir(parents=True, exist_ok=True)
        prior_state_path = runtime_state_dir / "prior_state.json"
        snapshot_dir = Path(artifact_dir) / "mainline_snapshots"
        if prior_state_path.exists():
            prior_state_path.unlink()

        print(f"Walk-forward Audit: Replaying {len(test)} windows through V11Conductor black-box...")
        for _, row in test.iterrows():
            dt = pd.Timestamp(row["observation_date"]).normalize()
            cutoff_dt = dt - pd.offsets.BDay(20)
            train_window = full_df[full_df["observation_date"] < cutoff_dt]
            if train_window.empty:
                continue

            is_oos = dt > (macro_df.index[-1] - pd.offsets.BDay(252))
            test_type = "TEST_OOS" if is_oos else "VALIDATION"

            conductor = V11Conductor(
                macro_data_path=dataset_path,
                regime_data_path=regime_path,
                prior_state_path=str(prior_state_path),
                snapshot_dir=str(snapshot_dir),
                overlay_mode=overlay_mode,
                training_cutoff=cutoff_dt,
                price_history_path=price_cache_path,
                allow_prior_bootstrap_drift=True,
            )
            t0_data = pd.DataFrame([row]).set_index("observation_date")
            runtime = conductor.daily_run(t0_data)
            class_count = getattr(getattr(conductor, "gnb", None), "classes_", None)
            if class_count is None:
                class_count_value = len(ordered_regimes)
            else:
                class_count_value = len(class_count)
            training_class_counts.append(
                {
                    "date": dt,
                    "class_count": int(class_count_value),
                }
            )

            actual_regime = str(row["regime"])
            expected_policy = expected_policy_for_regime(actual_regime, base_betas=base_betas)
            posteriors = {
                regime: float(runtime["probabilities"].get(regime, 0.0)) for regime in ordered_regimes
            }
            predicted_regime = max(posteriors, key=posteriors.get)
            brier = sum(
                (posteriors.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2
                for name in ordered_regimes
            )
            prior_details = dict(runtime.get("prior_details", {}))
            price_topology = dict(runtime.get("price_topology", {}))
            diagnostics = dict(runtime.get("v13_4_diagnostics", {}))
            penalties_applied = dict(diagnostics.get("penalties_applied", {}))

            probability_row = {
                "date": dt,
                "actual_regime": actual_regime,
                "actual_regime_probability": float(posteriors.get(actual_regime, 0.0)),
                "predicted_regime": predicted_regime,
                "brier": brier,
                "test_type": test_type,
            }
            for regime in ordered_regimes:
                probability_row[f"prob_{regime}"] = float(posteriors.get(regime, 0.0))
            probability_row.update(
                flatten_probability_dynamics(runtime.get("probability_dynamics", {}))
            )
            probability_rows.append(probability_row)

            execution_rows.append(
                {
                    "date": dt,
                    "beta_expectation": float(
                        runtime.get("beta_expectation", runtime["raw_target_beta"])
                    ),
                    "expected_target_beta": float(expected_policy["expected_target_beta"]),
                    "protected_beta": float(runtime.get("protected_beta", runtime["target_beta"])),
                    "overlay_beta": float(runtime.get("overlay_beta", runtime["target_beta"])),
                    "beta_overlay_multiplier": float(
                        runtime.get("overlay", {}).get("beta_overlay_multiplier", 1.0)
                    ),
                    "deployment_overlay_multiplier": float(
                        runtime.get("overlay", {}).get("deployment_overlay_multiplier", 1.0)
                    ),
                    "overlay_state": str(runtime.get("overlay", {}).get("overlay_state", "NEUTRAL")),
                    "target_beta": float(runtime["target_beta"]),
                    "raw_target_beta": float(runtime["raw_target_beta"]),
                    "entropy": _resolve_process_entropy(runtime),
                    "effective_entropy": _resolve_execution_entropy(runtime),
                    "prior_details": runtime.get("prior_details", {}),
                    "predicted_regime": predicted_regime,
                    "actual_regime": actual_regime,
                    "raw_regime": str(runtime.get("raw_regime", predicted_regime)),
                    "stable_regime": str(runtime.get("stable_regime", predicted_regime)),
                    "deployment_state": str(
                        runtime.get("deployment", {}).get("deployment_state", "DEPLOY_BASE")
                    ),
                    "deployment_multiplier": float(
                        runtime.get("deployment", {}).get("deployment_multiplier", 1.0)
                    ),
                    "expected_deployment_state": str(expected_policy["expected_deployment_state"]),
                    "expected_deployment_multiplier": float(
                        expected_policy["expected_deployment_multiplier"]
                    ),
                    "deployment_rank_abs_error": abs(
                        deployment_state_rank(
                            str(runtime.get("deployment", {}).get("deployment_state", "DEPLOY_BASE"))
                        )
                        - deployment_state_rank(str(expected_policy["expected_deployment_state"]))
                    ),
                    "actual_deployment_cash": deployment_cash_notional(
                        float(runtime.get("deployment", {}).get("deployment_multiplier", 1.0))
                    ),
                    "expected_deployment_cash": deployment_cash_notional(
                        float(expected_policy["expected_deployment_multiplier"])
                    ),
                    "deployment_pacing_error": float(
                        runtime.get("deployment", {}).get("deployment_multiplier", 1.0)
                    )
                    - float(expected_policy["expected_deployment_multiplier"]),
                    "lock_active": bool(runtime.get("v11_execution", {}).get("lock_active", False)),
                    "target_bucket": str(runtime.get("v11_execution", {}).get("target_bucket", "QQQ")),
                    "close": row.get("qqq_close"),
                    "price_topology_regime": str(price_topology.get("regime", "MID_CYCLE")),
                    "price_topology_expected_beta": float(
                        price_topology.get("expected_beta", runtime["target_beta"])
                    ),
                    "price_topology_confidence": float(price_topology.get("confidence", 0.0)),
                    "price_topology_posterior_blend_weight": float(
                        price_topology.get("posterior_blend_weight", 0.0)
                    ),
                    "price_topology_beta_anchor_weight": float(
                        price_topology.get("beta_anchor_weight", 0.0)
                    ),
                    "forensic_snapshot_path": str(runtime.get("forensic_snapshot_path", "")),
                    "forensic_stress_score": float(prior_details.get("stress_score", 0.0) or 0.0),
                    "forensic_mid_cycle_penalty": float(penalties_applied.get("MID_CYCLE", 1.0)),
                    "forensic_bust_penalty": float(penalties_applied.get("BUST", 1.0)),
                    "resonance_action": str(runtime.get("signal", {}).get("resonance", {}).get("action", "HOLD")),
                    "resonance_confidence": float(runtime.get("signal", {}).get("resonance", {}).get("confidence", 0.0)),
                    "resonance_reason": str(runtime.get("signal", {}).get("resonance", {}).get("reason", "No Resonance")),
                }
            )
            forensic_rows.append(
                {
                    "date": str(dt.date()),
                    "test_type": test_type,
                    "actual_regime": actual_regime,
                    "predicted_regime": predicted_regime,
                    "stable_regime": str(runtime.get("stable_regime", predicted_regime)),
                    "raw_regime": str(runtime.get("raw_regime", predicted_regime)),
                    "prior_details": prior_details,
                    "price_topology": price_topology,
                    "regime_stabilizer": runtime.get("regime_stabilizer", {}),
                    "v13_4_diagnostics": diagnostics,
                    "quality_audit": runtime.get("quality_audit", {}),
                    "forensic_snapshot_path": str(runtime.get("forensic_snapshot_path", "")),
                }
            )

        summary = _finalize_artifacts(
            probability_rows,
            execution_rows,
            forensic_rows=forensic_rows,
            training_class_counts=training_class_counts,
        )
        if summary["training_rows_below_full_support"] > 0:
            raise ValueError(
                "Full-support hard gate failed: training rows below full support remain after evaluation_start tightening."
            )
        return summary



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QQQ v11 production-black-box backtest audit")
    parser.add_argument(
        "--evaluation-start",
        default="2018-01-01",
        help="Evaluation start date for causal isolation audit (default: 2018-01-01)",
    )
    parser.add_argument(
        "--dataset-path",
        default="data/macro_historical_dump.csv",
        help="Path to the historical macro dataset.",
    )
    parser.add_argument(
        "--regime-path",
        default="data/v11_poc_phase1_results.csv",
        help="Path to the historical regime label dataset.",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/v12_audit",
        help="Directory for backtest artifacts.",
    )
    parser.add_argument(
        "--strict-state-support",
        action="store_true",
        help="Fail when the configured audit regimes are absent from the label dataset.",
    )
    parser.add_argument(
        "--overlay-mode",
        choices=["DISABLED", "SHADOW", "NEGATIVE_ONLY", "FULL"],
        help="v13 execution overlay operating mode.",
    )
    parser.add_argument(
        "--price-cache-path",
        help="Pinned QQQ history cache path for deterministic backtests.",
    )
    parser.add_argument(
        "--price-end-date",
        help="Pinned inclusive end date for QQQ history in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--no-price-download",
        action="store_true",
        help="Fail closed instead of downloading QQQ history when the cache is missing.",
    )
    parser.add_argument(
        "--acceptance",
        action="store_true",
        help="Force frozen-artifact acceptance mode. Requires --price-cache-path and --price-end-date.",
    )
    args = parser.parse_args(argv)

    if args.acceptance:
        if not args.price_cache_path:
            parser.error("--acceptance mode REQUIRE --price-cache-path (Fail-closed)")
        if not args.price_end_date:
            parser.error("--acceptance mode REQUIRE --price-end-date (Fail-closed)")

        # Lookahead defense: Reject if the end_date is the current dynamic 'today'
        import datetime

        now_date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        if args.price_end_date == now_date:
            parser.error(
                f"--acceptance mode REJECTS current dynamic date '{now_date}' to prevent lookahead leakage."
            )

    experiment_config: dict[str, Any] = {}
    if args.overlay_mode:
        experiment_config["overlay_mode"] = args.overlay_mode
    if args.price_cache_path:
        experiment_config["price_cache_path"] = args.price_cache_path
    if args.price_end_date:
        experiment_config["price_end_date"] = args.price_end_date
    if args.no_price_download or args.acceptance:
        experiment_config["allow_price_download"] = False

    run_v11_audit(
        dataset_path=args.dataset_path,
        regime_path=args.regime_path,
        evaluation_start=args.evaluation_start,
        artifact_dir=args.artifact_dir,
        strict_state_support=args.strict_state_support,
        experiment_config=experiment_config or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
