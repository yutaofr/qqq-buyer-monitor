"""
QQQ v12.0 Bayesian Backtest & Audit (Bayesian Convergence).

This module is the sole entry point for system validation. It enforces causal
isolation and probabilistic fidelity audits.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from src.engine.v13.execution_overlay import ExecutionOverlayEngine
from src.regime_topology import canonicalize_regime_sequence, merge_regime_weights

logger = logging.getLogger(__name__)

START_DATE = "1999-03-10"
END_DATE = date.today().isoformat()


def _load_price_history(
    cache_path: str,
    *,
    allow_download: bool = True,
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
        print(f"Downloading fresh data from yfinance since {cache_path} was missing or empty...")
        qqq = yf.Ticker("QQQ").history(start=START_DATE, end=(end_date or END_DATE))
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
        m=float(registry.get("inference_momentum_m", 0.6)),
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
    """Run the unified v12 probabilistic audit with deterministic walk-forward causality."""
    from sklearn.naive_bayes import GaussianNB

    from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
    from src.engine.v11.core.data_quality import (
        assess_data_quality,
        feature_reliability_weights,
    )
    from src.engine.v11.core.entropy_controller import EntropyController
    from src.engine.v11.core.execution_pipeline import run_execution_pipeline
    from src.engine.v11.core.model_validation import validate_feature_contract, validate_gaussian_nb
    from src.engine.v11.core.position_sizer import PositionSizingResult
    from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase
    from src.engine.v11.probability_seeder import ProbabilitySeeder
    from src.engine.v11.signal.behavioral_guard import BehavioralGuard
    from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy
    from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
    from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer
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

    audit_path = Path("src/engine/v11/resources/regime_audit.json")
    with open(audit_path, encoding="utf-8") as f:
        audit_data = json.load(f)
    audit_overrides = dict(experiment.get("audit_overrides", {}))
    base_betas = dict(audit_data["base_betas"])
    regime_sharpes = dict(audit_data["regime_sharpes"])
    if audit_overrides.get("base_betas"):
        base_betas = {str(k): float(v) for k, v in dict(audit_overrides["base_betas"]).items()}
    if audit_overrides.get("regime_sharpes"):
        regime_sharpes = {
            str(k): float(v) for k, v in dict(audit_overrides["regime_sharpes"]).items()
        }
    ordered_regimes = canonicalize_regime_sequence(base_betas.keys(), include_all=False)
    base_betas = merge_regime_weights(base_betas, regimes=ordered_regimes, include_zeros=True)
    regime_sharpes = merge_regime_weights(
        regime_sharpes, regimes=ordered_regimes, include_zeros=True
    )
    default_var_smoothing = float(
        audit_data.get("model_hyperparameters", {}).get("gaussian_nb_var_smoothing", 1e-2)
    )
    posterior_mode = str(
        experiment.get(
            "posterior_mode",
            audit_data.get("model_hyperparameters", {}).get("posterior_mode", "runtime_reweight"),
        )
    )
    overlay_mode = experiment.get("overlay_mode")
    price_cache_path = str(experiment.get("price_cache_path", "data/qqq_history_cache.csv"))
    allow_price_download = bool(experiment.get("allow_price_download", True))
    price_end_date = experiment.get("price_end_date")
    use_canonical_pipeline = bool(experiment.get("use_canonical_pipeline", False))
    state_support = summarize_regime_state_support(regime_df, audit_regimes=ordered_regimes)
    if strict_state_support:
        validate_regime_state_support(regime_df, audit_regimes=ordered_regimes)

    price_df = _load_price_history(
        price_cache_path,
        allow_download=allow_price_download,
        end_date=price_end_date,
    )
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_localize(None).normalize()

    macro_df.index = pd.to_datetime(macro_df.index).tz_localize(None).normalize()
    macro_df["qqq_close"] = price_df["Close"]
    macro_df["qqq_close"] = macro_df["qqq_close"].ffill()
    if "Volume" in price_df.columns:
        macro_df["qqq_volume"] = pd.to_numeric(price_df["Volume"], errors="coerce")
        macro_df["qqq_volume"] = macro_df["qqq_volume"].ffill()
        macro_df["source_qqq_volume"] = "direct:yfinance"
        macro_df["qqq_volume_quality_score"] = 1.0
    macro_df["source_qqq_close"] = "direct:yfinance"
    macro_df["qqq_close_quality_score"] = 1.0

    seeder = ProbabilitySeeder(**dict(experiment.get("probability_seeder", {})))
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
    features = seeder.generate_features(macro_df)
    full_df = features.join(regime_df["regime"], how="inner")

    full_df["qqq_close"] = macro_df["qqq_close"]
    if "qqq_volume" in macro_df.columns:
        full_df["qqq_volume"] = macro_df["qqq_volume"]
        full_df["source_qqq_volume"] = macro_df.get("source_qqq_volume", "direct:yfinance")
    full_df["source_qqq_close"] = macro_df.get("source_qqq_close", "direct:yfinance")

    if "qqq_volume_quality_score" in macro_df.columns:
        full_df["qqq_volume_quality_score"] = macro_df["qqq_volume_quality_score"]
    if "qqq_close_quality_score" in macro_df.columns:
        full_df["qqq_close_quality_score"] = macro_df["qqq_close_quality_score"]

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
    full_df = full_df.dropna(subset=["regime"])
    full_df = full_df.reset_index().rename(columns={"index": "observation_date"})
    full_df = full_df.sort_values("observation_date").reset_index(drop=True)

    eval_start = pd.to_datetime(evaluation_start)
    train = full_df[full_df["observation_date"] < eval_start].copy()
    test = full_df[full_df["observation_date"] >= eval_start].copy()

    if train.empty:
        raise ValueError(f"No pre-evaluation history available before {evaluation_start}.")
    if test.empty:
        raise ValueError(f"No evaluation rows available on or after {evaluation_start}.")

    logger.info(
        f"v12 Audit: Training on {len(train)} days (pre-{evaluation_start}), testing on {len(test)} days."
    )

    feature_cols = [c for c in seeder.feature_names() if c in train.columns]
    entropy_ctrl = EntropyController()
    last_train_regime = str(train.iloc[-1]["regime"])
    initial_beta = float(base_betas.get(last_train_regime, 1.0))
    initial_bucket = "QLD" if initial_beta > 1.0 else ("QQQ" if initial_beta >= 0.5 else "CASH")

    def _initial_deployment_state(regime: str) -> str:
        if regime == "BUST":
            return "DEPLOY_PAUSE"
        if regime == "LATE_CYCLE":
            return "DEPLOY_SLOW"
        if regime == "RECOVERY":
            return "DEPLOY_FAST"
        return "DEPLOY_BASE"

    beta_mapper = InertialBetaMapper(initial_beta=initial_beta)
    behavior_guard = BehavioralGuard(initial_bucket=initial_bucket)
    regime_stabilizer = RegimeStabilizer(initial_regime=last_train_regime)
    deployment_policy = ProbabilisticDeploymentPolicy(
        initial_state=_initial_deployment_state(last_train_regime)
    )
    overlay_engine = ExecutionOverlayEngine()

    with tempfile.TemporaryDirectory(prefix="v12_audit_") as tmp_dir:
        prior_book = PriorKnowledgeBase(
            storage_path=Path(tmp_dir) / "prior_state.json",
            regimes=ordered_regimes,
            bootstrap_regimes=train["regime"].astype(str).tolist(),
        )
        inference_engine = BayesianInferenceEngine(
            kde_models={regime: None for regime in ordered_regimes},
            base_priors=prior_book.current_priors(),
        )

        probability_rows: list[dict[str, Any]] = []
        execution_rows: list[dict[str, Any]] = []

        print(f"Walk-forward Audit: Re-fitting {len(test)} causal windows...")
        previous_raw = None
        for _, row in test.iterrows():
            dt = row["observation_date"]
            train_window = full_df[full_df["observation_date"] < dt].copy()
            if train_window.empty:
                continue

            gnb = GaussianNB(
                var_smoothing=float(experiment.get("var_smoothing", default_var_smoothing))
            )
            gnb.fit(train_window[feature_cols], train_window["regime"])
            validate_gaussian_nb(
                gnb,
                expected_classes=sorted(train_window["regime"].astype(str).unique()),
                feature_count=len(feature_cols),
            )

            evidence = pd.DataFrame([row[feature_cols].to_dict()], columns=feature_cols)
            class_priors = list(getattr(gnb, "class_prior_", []))
            if len(class_priors) != len(gnb.classes_):
                class_priors = [1.0 / len(gnb.classes_)] * len(gnb.classes_)
            training_priors = {
                str(label): float(probability)
                for label, probability in zip(gnb.classes_, class_priors, strict=True)
            }
            runtime_priors, prior_details = prior_book.runtime_priors()
            if posterior_mode == "classifier_only":
                active_priors = training_priors
            elif posterior_mode == "runtime_reweight":
                active_priors = runtime_priors
            else:
                raise ValueError(f"Unknown posterior_mode: {posterior_mode}")

            # v13.7-ULTIMA: Adapt to new weighted inference signature
            registry_path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
            if registry_path.exists():
                with open(registry_path) as f:
                    registry = json.load(f)
            else:
                registry = {}

            overlay_cols = [
                "observation_date",
                "adv_dec_ratio",
                "source_breadth_proxy",
                "breadth_quality_score",
                "ndx_concentration",
                "source_ndx_concentration",
                "ndx_concentration_quality_score",
                "qqq_close",
                "source_qqq_close",
                "qqq_close_quality_score",
                "qqq_volume",
                "source_qqq_volume",
                "qqq_volume_quality_score",
            ]

            # 1. Quality Auditing (Re-enabled for Task 6)
            latest_raw = row
            previous_raw = previous_raw if "previous_raw" in locals() else None
            # Note: In backtest, we can derive previous_raw from the loop state

            quality_audit = assess_data_quality(
                latest_raw,
                previous_raw=previous_raw,
                registry=registry,
                field_specs=_v12_quality_field_specs(),
            )
            feature_weights = feature_reliability_weights(
                latest_vector=evidence,
                latest_raw=latest_raw,
                field_quality={
                    str(name): float(payload.get("quality", 1.0))
                    for name, payload in dict(quality_audit.get("fields", {})).items()
                },
                seeder_config=seeder.config,
            )
            quality_score = float(quality_audit.get("overall_quality", 1.0))

            # 2. Bayesian Inference (With Quality Gating)
            posteriors, bayesian_diagnostics = inference_engine.infer_gaussian_nb_posterior(
                classifier=gnb,
                evidence_frame=evidence,
                runtime_priors=active_priors,
                weight_registry=registry,
                feature_quality_weights=feature_weights,
                tau=float(registry.get("inference_tau", 3.0)),
                m=float(registry.get("inference_momentum_m", 0.6)),
            )

            # Update previous_raw for next iteration
            previous_raw = latest_raw

            # 3. Execution Pipeline (Identity Wiring)
            # Calculation of intermediate pieces
            posterior_entropy = entropy_ctrl.calculate_normalized_entropy(posteriors)
            e_sharpe = sum(posteriors.get(r, 0.0) * s for r, s in regime_sharpes.items())

            # ERP Percentile Rank
            train_erp = pd.to_numeric(train_window.get("erp_ttm_pct"), errors="coerce").dropna()
            current_erp = pd.to_numeric(
                pd.Series([row.get("erp_ttm_pct")]), errors="coerce"
            ).dropna()
            if train_erp.empty or current_erp.empty:
                erp_p = 0.5
            else:
                erp_p = float(
                    pd.concat([train_erp, current_erp], ignore_index=True).rank(pct=True).iloc[-1]
                )

            # Run unified pipeline WITH BYPASS for Bit-identicality
            overlay_cols_for_context = [
                col for col in overlay_cols if col in train_window.columns and col in row.index
            ]
            overlay_context = pd.concat(
                [
                    train_window[overlay_cols_for_context],
                    pd.DataFrame([row[overlay_cols_for_context]]),
                ],
                ignore_index=True,
            )
            overlay = overlay_engine.evaluate(overlay_context, mode=overlay_mode)

            pipeline_result = run_execution_pipeline(
                raw_beta=sum(
                    posteriors.get(regime, 0.0) * base_betas.get(regime, 1.0)
                    for regime in ordered_regimes
                ),
                posterior_entropy=posterior_entropy,
                quality_score=quality_score,  # 1.0
                posteriors=posteriors,
                entropy_controller=entropy_ctrl,
                overlay=overlay,
                e_sharpe=e_sharpe,
                erp_percentile=erp_p,
                high_entropy_streak=0,
                bypass_v11_floor=False,  # CRITICAL: Fixed bug, baseline must also respect 0.5 floor
            )

            # Result Mapping
            norm_h = pipeline_result["effective_entropy"]
            protected_beta = pipeline_result["protected_beta"]
            overlay_beta = pipeline_result["overlay_beta"]
            final_beta = beta_mapper.calculate_inertial_beta(overlay_beta, norm_h)

            deployment_readiness = pipeline_result["deployment_readiness"]
            overlay_readiness = pipeline_result["overlay_deployment_readiness"]

            deployment_decision = deployment_policy.decide(
                posteriors=posteriors,
                entropy=norm_h,
                readiness_score=overlay_readiness,
                value_score=erp_p,
            )

            raw_beta = sum(
                posteriors.get(regime, 0.0) * base_betas.get(regime, 1.0)
                for regime in ordered_regimes
            )
            regime_decision = regime_stabilizer.update(posteriors=posteriors, entropy=norm_h)

            actual_regime = str(row["regime"])
            predicted_regime = max(posteriors, key=posteriors.get)
            brier = sum(
                (posteriors.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2
                for name in ordered_regimes
            )

            if final_beta > 1.0:
                qld = (final_beta - 1.0) * 100_000.0
                qqq = 100_000.0
                cash = 0.0
            else:
                qld = 0.0
                qqq = 100_000.0 * final_beta
                cash = 100_000.0 - qqq
            invested = qqq + qld
            sizing = PositionSizingResult(
                target_beta=round(float(final_beta), 6),
                raw_target_beta=round(float(raw_beta), 6),
                entropy=round(float(norm_h), 6),
                uncertainty_penalty=round(max(0.0, float(raw_beta) - float(final_beta)), 6),
                reference_capital=100_000.0,
                current_nav=100_000.0,
                risk_budget_dollars=round(100_000.0 * float(final_beta), 6),
                qqq_dollars=round(qqq, 6),
                qld_notional_dollars=round(qld, 6),
                cash_dollars=round(cash, 6),
                qld_share=round(qld / invested, 6) if invested > 0 else 0.0,
            )
            execution = behavior_guard.apply(sizing)

            probability_row = {
                "date": dt,
                "actual_regime": actual_regime,
                "actual_regime_probability": float(posteriors.get(actual_regime, 0.0)),
                "predicted_regime": predicted_regime,
                "brier": brier,
            }
            for regime in ordered_regimes:
                probability_row[f"prob_{regime}"] = float(posteriors.get(regime, 0.0))
            probability_rows.append(probability_row)

            execution_rows.append(
                {
                    "date": dt,
                    "protected_beta": protected_beta,
                    "overlay_beta": overlay_beta,
                    "beta_overlay_multiplier": float(overlay["beta_overlay_multiplier"]),
                    "deployment_overlay_multiplier": float(
                        overlay["deployment_overlay_multiplier"]
                    ),
                    "overlay_state": str(overlay["overlay_state"]),
                    "target_beta": final_beta,
                    "raw_target_beta": raw_beta,
                    "entropy": norm_h,
                    "prior_details": prior_details,
                    "predicted_regime": predicted_regime,
                    "actual_regime": actual_regime,
                    "raw_regime": regime_decision["raw_regime"],
                    "stable_regime": regime_decision["stable_regime"],
                    "deployment_state": deployment_decision["deployment_state"],
                    "lock_active": execution.lock_active,
                    "target_bucket": execution.target_bucket,
                    "close": row["qqq_close"],
                }
            )

            prior_book.update_with_posterior(
                observation_date=pd.Timestamp(dt).date().isoformat(),
                posterior=posteriors,
            )
            prior_book.update_execution_state(
                current_beta=float(beta_mapper.current_beta),
                beta_evidence=float(beta_mapper.evidence),
                current_bucket=behavior_guard.current_bucket,
                bucket_evidence=float(behavior_guard.evidence),
                bucket_cooldown_days=int(behavior_guard.cooldown_days_remaining),
                stable_regime=str(regime_decision["stable_regime"]),
                regime_evidence=float(regime_stabilizer.evidence),
                deployment_state=str(deployment_decision["deployment_state"]),
                deployment_evidence=float(deployment_policy.evidence),
            )

    probability_df = pd.DataFrame(probability_rows).sort_values("date")
    execution_df = pd.DataFrame(execution_rows).sort_values("date")
    full_audit_df = pd.merge(
        execution_df, probability_df, on=["date", "predicted_regime", "actual_regime"], how="left"
    )

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
        "gaussian_nb_var_smoothing": float(experiment.get("var_smoothing", default_var_smoothing)),
        "posterior_mode": posterior_mode,
        "overlay_mode": str(overlay_mode or overlay_engine.default_mode),
    }

    print("\n--- v12 Unified Probabilistic Performance Audit ---")
    print(
        f"Accuracy: {summary['top1_accuracy']:.2%} | Brier: {summary['mean_brier']:.4f} | Entropy: {summary['mean_entropy']:.3f} | Lock: {summary['lock_incidence']:.1%}"
    )

    save_dir = Path(artifact_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    probability_df.to_csv(save_dir / "probability_audit.csv", index=False)
    execution_df.to_csv(save_dir / "execution_trace.csv", index=False)
    full_audit_df.to_csv(save_dir / "full_audit.csv", index=False)
    (save_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    save_v11_fidelity_figure(execution_df, summary, [save_dir / "v12_target_beta_fidelity.png"])
    save_v11_probabilistic_audit_figure(
        full_audit_df, summary, [save_dir / "v12_probabilistic_audit.png"]
    )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QQQ v12.0 Bayesian Backtest Audit")
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
    parser.add_argument(
        "--no-canonical-pipeline",
        action="store_false",
        dest="use_canonical_pipeline",
        help="Disable the shared v13.8 canonical quality and execution pipeline.",
    )
    parser.set_defaults(use_canonical_pipeline=True)
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

    experiment_config["use_canonical_pipeline"] = args.use_canonical_pipeline

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
