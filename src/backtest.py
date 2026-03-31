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
    evaluation_start: str = "2018-01-01",
) -> dict[str, Any]:
    """Run the unified v11.5 probabilistic audit with causal isolation."""
    from sklearn.naive_bayes import GaussianNB

    from src.engine.v11.core.entropy_controller import EntropyController
    from src.engine.v11.core.position_sizer import PositionSizingResult
    from src.engine.v11.probability_seeder import ProbabilitySeeder
    from src.engine.v11.signal.behavioral_guard import BehavioralGuard
    from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
    from src.engine.v11.utils.memory_booster import SovereignMemoryBooster
    from src.output.backtest_plots import (
        save_v11_fidelity_figure,
        save_v11_probabilistic_audit_figure,
    )

    # Sovereign Determinism: Ensure baseline data exists for audit (v11.51)
    # This prevents FileNotFoundError in ephemeral CI/CD environments.
    SovereignMemoryBooster(
        macro_path=dataset_path, 
        regime_path="data/v11_poc_phase1_results.csv"
    ).ensure_baseline()

    macro_df = pd.read_csv(dataset_path, parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")

    audit_path = Path("src/engine/v11/resources/regime_audit.json")
    with open(audit_path, encoding="utf-8") as f:
        audit_data = json.load(f)
    base_betas = audit_data["base_betas"]
    entropy_threshold = audit_data["risk_thresholds"]["entropy_max"]

    price_df = _load_price_history("data/qqq_history_cache.csv")
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_localize(None).normalize()

    macro_df.index = pd.to_datetime(macro_df.index).tz_localize(None).normalize()
    macro_df["qqq_close"] = price_df["Close"]
    macro_df["qqq_close"] = macro_df["qqq_close"].ffill()

    seeder = ProbabilitySeeder()
    features = seeder.generate_features(macro_df)
    full_df = features.join(regime_df["regime"], how="inner")
    full_df["qqq_close"] = macro_df["qqq_close"]
    full_df = full_df.dropna()
    full_df = full_df.reset_index().rename(columns={"index": "observation_date"})

    train = full_df[full_df["observation_date"] < pd.to_datetime(evaluation_start)].copy()
    test = full_df[full_df["observation_date"] >= pd.to_datetime(evaluation_start)].copy()

    logger.info(f"v11.5 Audit: Training on {len(train)} days (pre-{evaluation_start}), testing on {len(test)} days.")

    feature_cols = [c for c in train.columns if c not in ["observation_date", "regime", "qqq_close"]]
    gnb = GaussianNB()
    gnb.fit(train[feature_cols], train["regime"])

    print(f"Parallel Inference: Dispatching {len(test)} tasks...")
    source_df_map = macro_df.reset_index()
    tasks = []
    for _, row in test.iterrows():
        source_row = source_df_map[source_df_map["observation_date"] == row["observation_date"]].iloc[0]
        tasks.append((row, source_row, gnb, list(gnb.classes_), feature_cols))

    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor() as executor:
        probability_results = list(executor.map(_v11_inference_task, tasks))

    probability_df = pd.DataFrame([r for r in probability_results if r])
    probability_df = probability_df.sort_values("date")

    entropy_ctrl = EntropyController(threshold=entropy_threshold)
    beta_mapper = InertialBetaMapper()
    behavior_guard = BehavioralGuard()

    execution_rows = []
    for _, prob_row in probability_df.iterrows():
        dt = prob_row["date"]
        source_row = test[test["observation_date"] == dt].iloc[0]
        posteriors = prob_row["posterior"]

        raw_beta = sum(posteriors.get(regime, 1.0) * base_betas.get(regime, 1.0)
                       for regime in posteriors)

        norm_h = entropy_ctrl.calculate_normalized_entropy(posteriors)
        protected_beta = entropy_ctrl.apply_haircut(raw_beta, norm_h)

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

        execution_rows.append({
            "date": dt,
            "target_beta": final_beta,
            "raw_target_beta": raw_beta,
            "entropy": norm_h,
            "predicted_regime": prob_row["predicted_regime"],
            "actual_regime": source_row["regime"],
            "lock_active": execution.lock_active,
            "target_bucket": execution.target_bucket,
            "close": source_row["qqq_close"]
        })

    execution_df = pd.DataFrame(execution_rows)
    full_audit_df = pd.merge(execution_df, probability_df.drop(columns=["posterior"]), on="date", how="left")

    summary = {
        "compared_points": int(len(probability_df)),
        "top1_accuracy": float((probability_df["predicted_regime"] == probability_df["actual_regime"]).mean()),
        "mean_brier": float(probability_df["brier"].mean()),
        "mean_entropy": float(execution_df["entropy"].mean()),
        "lock_incidence": float(execution_df["lock_active"].mean())
    }

    print("\n--- v11.5 Unified Probabilistic Performance Audit ---")
    print(f"Accuracy: {summary['top1_accuracy']:.2%} | Brier: {summary['mean_brier']:.4f} | Entropy: {summary['mean_entropy']:.3f} | Lock: {summary['lock_incidence']:.1%}")

    save_dir = Path("artifacts/v11_5_acceptance")
    save_dir.mkdir(parents=True, exist_ok=True)

    save_v11_fidelity_figure(execution_df, summary, [save_dir / "v11_5_target_beta_fidelity.png"])
    save_v11_probabilistic_audit_figure(full_audit_df, summary, [save_dir / "v11_5_probabilistic_audit.png"])

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
    args = parser.parse_args(argv)

    run_v11_audit(
        dataset_path=args.dataset_path,
        evaluation_start=args.evaluation_start
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
