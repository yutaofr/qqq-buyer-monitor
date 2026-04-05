"""QQQ-only posterior research utilities for disciplined feature subset selection."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

QQQ_CYCLE_CORE_FEATURES: tuple[str, ...] = (
    "real_yield_structural_z",
    "core_capex_momentum",
    "liquidity_252d",
    "erp_absolute",
    "spread_absolute",
    "pmi_momentum",
)

QQQ_CYCLE_OPTIONAL_FEATURES: tuple[str, ...] = (
    "move_21d",
    "breakeven_accel",
    "copper_gold_roc_126d",
    "usdjpy_roc_126d",
    "spread_21d",
    "labor_slack",
)

_RANKING_METRICS: tuple[tuple[str, bool], ...] = (
    ("selection_top1_accuracy", False),
    ("selection_mean_brier", True),
    ("selection_mean_entropy", True),
    ("selection_stable_critical_recall", False),
    ("selection_mean_true_regime_probability", False),
    ("selection_mean_true_regime_rank", True),
    ("selection_mean_expected_l1_error", True),
    ("selection_min_regime_true_probability", False),
    ("selection_max_regime_true_rank", True),
)


def build_qqq_cycle_candidate_sets(
    feature_order: list[str] | tuple[str, ...],
    *,
    core_features: list[str] | tuple[str, ...] = QQQ_CYCLE_CORE_FEATURES,
    optional_features: list[str] | tuple[str, ...] = QQQ_CYCLE_OPTIONAL_FEATURES,
    dormant_pairs: tuple[tuple[str, ...], ...] = (("pmi_momentum", "labor_slack"),),
) -> list[dict[str, Any]]:
    ordered = list(feature_order)
    core = list(core_features)
    optional = list(optional_features)
    unknown = [name for name in [*core, *optional] if name not in ordered]
    if unknown:
        raise ValueError(f"Unknown candidate features: {unknown}")
    overlap = sorted(set(core) & set(optional))
    if overlap:
        raise ValueError(f"Core and optional features overlap: {overlap}")
    for pair in dormant_pairs:
        pair_unknown = [name for name in pair if name not in ordered]
        if pair_unknown:
            raise ValueError(f"Unknown dormant pair features: {pair_unknown}")

    candidates: list[dict[str, Any]] = []
    seen_subsets: set[tuple[str, ...]] = set()

    def add_candidate(name: str, features: list[str], family: str) -> None:
        subset = tuple(feature for feature in ordered if feature in set(features))
        if not subset or subset in seen_subsets:
            return
        seen_subsets.add(subset)
        candidates.append(
            {
                "name": name,
                "family": family,
                "feature_count": len(subset),
                "features": list(subset),
            }
        )

    add_candidate(f"baseline_{len(ordered)}", ordered, "baseline")
    add_candidate(f"qqq_core_{len(core)}", core, "first_principles_core")

    for feature_name in ordered:
        add_candidate(
            f"drop_{feature_name}",
            [feature for feature in ordered if feature != feature_name],
            "leave_one_out",
        )
    for pair in dormant_pairs:
        add_candidate(
            f"drop_{'__'.join(pair)}",
            [feature for feature in ordered if feature not in set(pair)],
            "pair_prune",
        )

    for optional_count in range(1, len(optional) + 1):
        for combo in combinations(optional, optional_count):
            add_candidate(
                f"qqq_core_{len(core) + optional_count}__{'__'.join(combo)}",
                [*core, *combo],
                "core_plus_optional",
            )

    return candidates


def flatten_window_report(window_name: str, report: dict[str, Any]) -> dict[str, float]:
    summary = dict(report.get("summary", {}))
    critical = dict(report.get("critical_regime_performance", {}))
    overall = dict(report.get("posterior_alignment", {}).get("overall", {}))
    by_regime = dict(report.get("posterior_alignment", {}).get("by_regime", {}))

    regime_true_probs = [
        float(metrics.get("mean_true_regime_probability", 0.0))
        for metrics in by_regime.values()
        if metrics
    ]
    regime_true_ranks = [
        float(metrics.get("mean_true_regime_rank", 0.0)) for metrics in by_regime.values() if metrics
    ]

    prefix = f"{window_name}_"
    return {
        f"{prefix}top1_accuracy": float(summary.get("top1_accuracy", 0.0)),
        f"{prefix}mean_brier": float(summary.get("mean_brier", 0.0)),
        f"{prefix}mean_entropy": float(summary.get("mean_entropy", 0.0)),
        f"{prefix}stable_critical_recall": float(critical.get("stable_critical_recall", 0.0)),
        f"{prefix}raw_critical_recall": float(critical.get("raw_critical_recall", 0.0)),
        f"{prefix}mean_true_regime_probability": float(
            overall.get("mean_true_regime_probability", 0.0)
        ),
        f"{prefix}mean_true_regime_rank": float(overall.get("mean_true_regime_rank", 0.0)),
        f"{prefix}mean_expected_l1_error": float(overall.get("mean_expected_l1_error", 0.0)),
        f"{prefix}min_regime_true_probability": float(min(regime_true_probs))
        if regime_true_probs
        else 0.0,
        f"{prefix}max_regime_true_rank": float(max(regime_true_ranks)) if regime_true_ranks else 0.0,
    }


def rank_candidate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = frame.copy()
    for metric_name, ascending in _RANKING_METRICS:
        if metric_name not in ranked.columns:
            raise ValueError(f"Missing ranking metric: {metric_name}")
        ranked[f"rank::{metric_name}"] = ranked[metric_name].rank(
            ascending=ascending,
            method="min",
        )

    rank_columns = [column for column in ranked.columns if column.startswith("rank::")]
    ranked["selection_composite_rank"] = ranked[rank_columns].mean(axis=1)
    return ranked.sort_values(
        [
            "selection_composite_rank",
            "selection_mean_brier",
            "selection_mean_entropy",
            "selection_top1_accuracy",
        ],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)


def build_research_frame(
    *,
    dataset_path: str | Path,
    regime_path: str | Path,
    feature_names: list[str] | tuple[str, ...],
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    from src.backtest import _v12_quality_field_specs
    from src.engine.v11.probability_seeder import ProbabilitySeeder
    from src.regime_topology import canonicalize_regime_sequence

    macro_df = pd.read_csv(dataset_path, parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv(regime_path, parse_dates=["observation_date"]).set_index("observation_date")

    macro_df.index = pd.to_datetime(macro_df.index).tz_localize(None).normalize()
    regime_df.index = pd.to_datetime(regime_df.index).tz_localize(None).normalize()

    seeder = ProbabilitySeeder(selected_features=list(feature_names))
    features = seeder.generate_features(macro_df)
    full_df = features.join(regime_df["regime"], how="inner")

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

    full_df = full_df.dropna(subset=["regime"]).reset_index()
    index_name = str(features.index.name or "index")
    full_df = full_df.rename(columns={index_name: "date", "index": "date"})
    full_df = full_df.sort_values("date").reset_index(drop=True)
    ordered_regimes = canonicalize_regime_sequence(full_df["regime"].astype(str).unique(), include_all=False)

    return full_df, ordered_regimes, {"feature_names": list(seeder.feature_names())}


def run_cycle_probability_audit(
    full_df: pd.DataFrame,
    *,
    ordered_regimes: list[str] | tuple[str, ...],
    feature_names: list[str] | tuple[str, ...],
    evaluation_start: str,
    evaluation_end: str | None = None,
    var_smoothing: float = 1e-4,
    registry_path: str | Path = "src/engine/v11/resources/v13_4_weights_registry.json",
) -> pd.DataFrame:
    from sklearn.naive_bayes import GaussianNB

    from src.backtest import _v12_quality_field_specs
    from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
    from src.engine.v11.core.data_quality import assess_data_quality, feature_reliability_weights
    from src.engine.v11.core.entropy_controller import EntropyController
    from src.engine.v11.probability_seeder import ProbabilitySeeder

    if full_df.empty:
        raise ValueError("full_df is required")

    evaluation_start_ts = pd.Timestamp(evaluation_start)
    evaluation_end_ts = pd.Timestamp(evaluation_end) if evaluation_end else None
    ordered_features = [feature for feature in feature_names if feature in full_df.columns]
    if not ordered_features:
        raise ValueError("No selected features available in full_df")

    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    seeder_config = ProbabilitySeeder(selected_features=ordered_features).config
    inference_engine = BayesianInferenceEngine(
        kde_models={regime: None for regime in ordered_regimes},
        base_priors={regime: 1.0 / len(ordered_regimes) for regime in ordered_regimes},
    )
    entropy_controller = EntropyController()

    evaluation = full_df[full_df["date"] >= evaluation_start_ts].copy()
    if evaluation_end_ts is not None:
        evaluation = evaluation[evaluation["date"] <= evaluation_end_ts].copy()
    if evaluation.empty:
        raise ValueError("No evaluation rows in requested window")

    rows: list[dict[str, Any]] = []
    previous_raw = None
    for _, row in evaluation.iterrows():
        train_window = full_df[full_df["date"] < row["date"]].copy()
        if train_window.empty:
            continue

        gnb = GaussianNB(var_smoothing=float(var_smoothing))
        gnb.fit(train_window[ordered_features], train_window["regime"])

        evidence = pd.DataFrame([row[ordered_features].to_dict()], columns=ordered_features)
        training_priors = {
            str(label): float(probability)
            for label, probability in zip(gnb.classes_, gnb.class_prior_, strict=True)
        }

        quality_audit = assess_data_quality(
            row,
            previous_raw=previous_raw,
            registry=registry,
            field_specs=_v12_quality_field_specs(),
        )
        feature_weights = feature_reliability_weights(
            latest_vector=evidence,
            latest_raw=row,
            field_quality={
                str(name): float(payload.get("quality", 1.0))
                for name, payload in dict(quality_audit.get("fields", {})).items()
            },
            seeder_config=seeder_config,
        )
        posteriors, _ = inference_engine.infer_gaussian_nb_posterior(
            classifier=gnb,
            evidence_frame=evidence,
            runtime_priors=training_priors,
            weight_registry=registry,
            feature_quality_weights=feature_weights,
            tau=float(registry.get("inference_tau", 3.0)),
            m=float(registry.get("inference_momentum_m", 0.6)),
        )
        previous_raw = row

        actual_regime = str(row["regime"])
        predicted_regime = max(posteriors, key=posteriors.get)
        brier = sum(
            (posteriors.get(regime, 0.0) - (1.0 if regime == actual_regime else 0.0)) ** 2
            for regime in ordered_regimes
        )
        entropy = entropy_controller.calculate_normalized_entropy(posteriors)

        record = {
            "date": row["date"],
            "actual_regime": actual_regime,
            "predicted_regime": predicted_regime,
            "raw_regime": predicted_regime,
            "stable_regime": predicted_regime,
            "brier": float(brier),
            "entropy": float(entropy),
            "actual_regime_probability": float(posteriors.get(actual_regime, 0.0)),
            "feature_count": len(ordered_features),
        }
        for regime in ordered_regimes:
            record[f"prob_{regime}"] = float(posteriors.get(regime, 0.0))
        rows.append(record)

    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
