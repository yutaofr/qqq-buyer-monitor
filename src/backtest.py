"""
QQQ v11.5 Bayesian Backtest & Audit (Bayesian Convergence).

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

logger = logging.getLogger(__name__)

START_DATE = "1999-03-10"
END_DATE = date.today().isoformat()


def _load_price_history(cache_path: str) -> pd.DataFrame:
    """Load cached QQQ history, downloading only when the cache is unavailable."""
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

    if qqq.empty:
        print(f"Downloading fresh data from yfinance since {cache_path} was missing or empty...")
        qqq = yf.Ticker("QQQ").history(start=START_DATE, end=END_DATE)
        if not qqq.empty:
            os.makedirs("data", exist_ok=True)
            qqq.to_csv(cache_path)
            print(f"Cache updated: {cache_path}")

    if qqq.empty:
        raise ValueError("No price data available.")

    return qqq


def _v11_inference_task(
    row_data: tuple[pd.Series, pd.Series, Any, list[str], list[str]],
) -> dict[str, Any]:
    """Independent worker task for v11.5 Bayesian inference."""
    std_row, source_row, gnb_model, classes, feature_cols = row_data

    evidence = pd.DataFrame([std_row[feature_cols].to_dict()], columns=feature_cols)

    probs_array = gnb_model.predict_proba(evidence)[0]
    posterior = dict(zip(classes, probs_array, strict=True))

    actual_regime = str(std_row.get("regime", source_row.get("regime", "MID_CYCLE")))
    predicted_regime = max(posterior, key=posterior.get)

    brier = sum((posterior.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2 for name in classes)

    return {
        "date": std_row["observation_date"],
        "actual_regime": actual_regime,
        "actual_regime_probability": float(posterior.get(actual_regime, 0.0)),
        "predicted_regime": predicted_regime,
        "brier": brier,
        "posterior": posterior
    }


def run_v11_audit(
    *,
    dataset_path: str = "data/macro_historical_dump.csv",
    regime_path: str = "data/v11_poc_phase1_results.csv",
    evaluation_start: str = "2018-01-01",
) -> dict[str, Any]:
    """Run the unified v12 probabilistic audit with deterministic walk-forward causality."""
    from sklearn.naive_bayes import GaussianNB

    from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
    from src.engine.v11.core.entropy_controller import EntropyController
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

    macro_df = pd.read_csv(dataset_path, parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv(regime_path, parse_dates=["observation_date"]).set_index("observation_date")

    audit_path = Path("src/engine/v11/resources/regime_audit.json")
    with open(audit_path, encoding="utf-8") as f:
        audit_data = json.load(f)
    base_betas = audit_data["base_betas"]
    regime_sharpes = audit_data["regime_sharpes"]
    ordered_regimes = list(base_betas.keys())

    price_df = _load_price_history("data/qqq_history_cache.csv")
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_localize(None).normalize()

    macro_df.index = pd.to_datetime(macro_df.index).tz_localize(None).normalize()
    macro_df["qqq_close"] = price_df["Close"]
    macro_df["qqq_close"] = macro_df["qqq_close"].ffill()

    seeder = ProbabilitySeeder()
    validate_feature_contract(
        expected_hash=audit_data.get("feature_contract", {}).get("seeder_config_hash"),
        actual_hash=seeder.contract_hash(),
        expected_features=audit_data.get("feature_contract", {}).get("feature_names"),
        actual_features=seeder.feature_names(),
    )
    features = seeder.generate_features(macro_df)
    full_df = features.join(regime_df["regime"], how="inner")
    full_df["qqq_close"] = macro_df["qqq_close"]
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

    logger.info(f"v12 Audit: Training on {len(train)} days (pre-{evaluation_start}), testing on {len(test)} days.")

    feature_cols = [
        c
        for c in train.columns
        if c not in ["observation_date", "regime", "qqq_close", "erp_ttm_pct", "erp_pct"]
    ]
    entropy_ctrl = EntropyController()
    last_train_regime = str(train.iloc[-1]["regime"])
    initial_beta = float(base_betas.get(last_train_regime, 1.0))
    initial_bucket = "QLD" if initial_beta > 1.0 else ("QQQ" if initial_beta >= 0.5 else "CASH")

    def _initial_deployment_state(regime: str) -> str:
        if regime == "BUST":
            return "DEPLOY_PAUSE"
        if regime == "LATE_CYCLE":
            return "DEPLOY_SLOW"
        if regime in {"RECOVERY", "CAPITULATION"}:
            return "DEPLOY_FAST"
        return "DEPLOY_BASE"

    beta_mapper = InertialBetaMapper(initial_beta=initial_beta)
    behavior_guard = BehavioralGuard(initial_bucket=initial_bucket)
    regime_stabilizer = RegimeStabilizer(initial_regime=last_train_regime)
    deployment_policy = ProbabilisticDeploymentPolicy(
        initial_state=_initial_deployment_state(last_train_regime)
    )

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
        for _, row in test.iterrows():
            dt = row["observation_date"]
            train_window = full_df[full_df["observation_date"] < dt].copy()
            if train_window.empty:
                continue

            gnb = GaussianNB(var_smoothing=1e-2)
            gnb.fit(train_window[feature_cols], train_window["regime"])
            validate_gaussian_nb(
                gnb,
                expected_classes=sorted(train_window["regime"].astype(str).unique()),
                feature_count=len(feature_cols),
            )

            evidence = pd.DataFrame([row[feature_cols].to_dict()], columns=feature_cols)
            classifier_posteriors = {
                str(label): float(probability)
                for label, probability in zip(gnb.classes_, gnb.predict_proba(evidence)[0], strict=True)
            }
            class_priors = list(getattr(gnb, "class_prior_", []))
            if len(class_priors) != len(gnb.classes_):
                class_priors = [1.0 / len(gnb.classes_)] * len(gnb.classes_)
            training_priors = {
                str(label): float(probability)
                for label, probability in zip(gnb.classes_, class_priors, strict=True)
            }
            runtime_priors, _ = prior_book.runtime_priors()
            posteriors = inference_engine.reweight_probabilities(
                classifier_posteriors=classifier_posteriors,
                training_priors=training_priors,
                runtime_priors=runtime_priors,
            )

            actual_regime = str(row["regime"])
            predicted_regime = max(posteriors, key=posteriors.get)
            brier = sum(
                (posteriors.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2
                for name in ordered_regimes
            )
            norm_h = entropy_ctrl.calculate_normalized_entropy(posteriors)
            regime_decision = regime_stabilizer.update(posteriors=posteriors, entropy=norm_h)

            raw_beta = sum(
                posteriors.get(regime, 0.0) * base_betas.get(regime, 1.0)
                for regime in ordered_regimes
            )
            protected_beta = entropy_ctrl.apply_haircut(
                raw_beta,
                norm_h,
                state_count=len(posteriors),
            )
            final_beta = beta_mapper.calculate_inertial_beta(protected_beta, norm_h)

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

            train_erp = pd.to_numeric(train_window.get("erp_ttm_pct"), errors="coerce").dropna()
            current_erp = pd.to_numeric(pd.Series([row.get("erp_ttm_pct")]), errors="coerce").dropna()
            if train_erp.empty or current_erp.empty:
                erp_percentile = 0.5
            else:
                erp_percentile = float(
                    pd.concat([train_erp, current_erp], ignore_index=True).rank(pct=True).iloc[-1]
                )
            e_sharpe = sum(posteriors.get(regime, 0.0) * regime_sharpes.get(regime, 0.0) for regime in ordered_regimes)
            deployment_readiness = float(
                max(0.0, min(1.0, (1.0 - norm_h) * max(0.0, e_sharpe) * erp_percentile))
            )
            deployment_decision = deployment_policy.decide(
                posteriors=posteriors,
                entropy=norm_h,
                readiness_score=deployment_readiness,
                value_score=erp_percentile,
            )

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
                    "target_beta": final_beta,
                    "raw_target_beta": raw_beta,
                    "entropy": norm_h,
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
    full_audit_df = pd.merge(execution_df, probability_df, on=["date", "predicted_regime", "actual_regime"], how="left")

    summary = {
        "compared_points": int(len(probability_df)),
        "top1_accuracy": float((probability_df["predicted_regime"] == probability_df["actual_regime"]).mean()),
        "mean_brier": float(probability_df["brier"].mean()),
        "mean_entropy": float(execution_df["entropy"].mean()),
        "lock_incidence": float(execution_df["lock_active"].mean())
    }

    print("\n--- v12 Unified Probabilistic Performance Audit ---")
    print(f"Accuracy: {summary['top1_accuracy']:.2%} | Brier: {summary['mean_brier']:.4f} | Entropy: {summary['mean_entropy']:.3f} | Lock: {summary['lock_incidence']:.1%}")

    save_dir = Path("artifacts/v12_audit")
    save_dir.mkdir(parents=True, exist_ok=True)

    probability_df.to_csv(save_dir / "probability_audit.csv", index=False)
    execution_df.to_csv(save_dir / "execution_trace.csv", index=False)
    full_audit_df.to_csv(save_dir / "full_audit.csv", index=False)
    (save_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    save_v11_fidelity_figure(execution_df, summary, [save_dir / "v12_target_beta_fidelity.png"])
    save_v11_probabilistic_audit_figure(full_audit_df, summary, [save_dir / "v12_probabilistic_audit.png"])

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QQQ v11.5 Bayesian Backtest Audit")
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
    args = parser.parse_args(argv)

    run_v11_audit(
        dataset_path=args.dataset_path,
        regime_path=args.regime_path,
        evaluation_start=args.evaluation_start
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
