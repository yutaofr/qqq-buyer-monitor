"""Shadow OOS audit runner for the recovery HMM research track."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.recovery_hmm.execution_tensor import compute_shadow_weight
from src.research.recovery_hmm.feature_space import build_feature_space
from src.research.recovery_hmm.orthogonalization import fit_pca_projection
from src.research.recovery_hmm.state_engine import recovery_to_midcycle_probability
from src.research.recovery_hmm.variants import LOCKED_CANDIDATE_VARIANT, RecoveryHmmVariant


def _normalized_entropy(probabilities: dict[str, float]) -> float:
    values = np.array(list(probabilities.values()), dtype=float)
    values = np.clip(values, 1e-12, 1.0)
    h = float(-(values * np.log(values)).sum())
    return h / math.log(len(values))


def _softmax(scores: dict[str, float], *, temperature: float = 0.4) -> dict[str, float]:
    values = pd.Series(scores, dtype=float)
    shifted = (values - values.max()) / max(temperature, 1e-6)
    exp = np.exp(shifted)
    denom = float(exp.sum())
    return {str(k): float(v / denom) for k, v in exp.items()}


def _orthogonal_confidence(projected_row: pd.Series | None) -> float:
    if projected_row is None:
        return 0.0
    magnitudes = pd.to_numeric(projected_row, errors="coerce").abs().dropna()
    if magnitudes.empty:
        return 0.0
    dominance = float(magnitudes.max() / max(float(magnitudes.sum()), 1e-6))
    energy = float(np.tanh(float(magnitudes.mean()) / 1.5))
    return float(np.clip(dominance * energy * 1.8, 0.0, 1.0))


def _domain_scores(
    feature_row: pd.Series,
    variant: RecoveryHmmVariant = LOCKED_CANDIDATE_VARIANT,
    *,
    projected_row: pd.Series | None = None,
) -> dict[str, float]:
    spread = float(feature_row["L1_hy_ig_spread"])
    curve = float(feature_row["L2_curve_10y_2y"])
    fci = float(feature_row["L3_chicago_fci"])
    spread_velocity = float(feature_row["V1_spread_compression_velocity"])
    real_yield_velocity = float(feature_row["V2_real_yield_velocity"])
    orders_gap = float(feature_row["V3_orders_inventory_gap"])
    term_ratio = float(feature_row["S1_vix_term_ratio"])
    skew = float(feature_row["S2_qqq_skew_mean"])

    spread_compression = max(0.0, variant.decay_spread_velocity_weight * spread_velocity)
    real_yield_relief = max(0.0, variant.decay_real_yield_relief_weight * (-real_yield_velocity))
    orders_relief = max(0.0, variant.decay_orders_weight * (orders_gap / 10.0))
    curve_support = max(0.0, curve)
    curve_inversion = max(0.0, -curve)
    term_support = max(0.0, term_ratio - 1.0)
    term_inversion = max(0.0, 1.0 - term_ratio)
    spread_penalty = max(0.0, spread / 10.0)
    spread_stress = max(0.0, spread / 5.0)
    spread_widening = max(0.0, -spread_velocity)
    decay_score = spread_compression + real_yield_relief + orders_relief
    level_score = max(
        0.0,
        (variant.level_curve_weight * curve_support)
        - (variant.level_fci_penalty_weight * max(0.0, fci))
        - (variant.level_spread_penalty_weight * spread_penalty)
        + (variant.level_term_support_weight * term_support),
    )
    recovery_transition = recovery_to_midcycle_probability(
        level_score=level_score,
        decay_score=decay_score,
        alpha=variant.transition_alpha,
        beta=variant.transition_beta,
    )

    scores = {
        "RECOVERY": (variant.recovery_decay_weight * decay_score)
        + (variant.recovery_term_support_weight * term_support)
        + (variant.recovery_skew_relief_weight * max(0.0, 0.7 - skew)),
        "MID_CYCLE": (variant.mid_transition_weight * recovery_transition)
        + (variant.mid_curve_support_weight * curve_support)
        + (variant.mid_orders_support_weight * max(0.0, orders_gap / 8.0)),
        "LATE_CYCLE": (variant.late_spread_weight * max(0.0, spread / 8.0))
        + (variant.late_skew_weight * max(0.0, skew - 0.5))
        + (variant.late_term_inversion_weight * term_inversion),
        "BUST": (variant.bust_spread_weight * spread_stress)
        + (variant.bust_fci_weight * max(0.0, fci))
        + (variant.bust_term_inversion_weight * term_inversion)
        + (variant.bust_skew_weight * max(0.0, skew - 0.45))
        + (variant.bust_curve_inversion_weight * curve_inversion)
        + (variant.bust_spread_widening_weight * spread_widening),
    }
    orthogonal_confidence = _orthogonal_confidence(projected_row)
    effective_temperature = variant.softmax_temperature * max(
        0.25,
        1.0 - (variant.orthogonal_temperature_strength * orthogonal_confidence),
    )
    return _softmax(scores, temperature=effective_temperature)


def _fdas_trigger(
    feature_frame: pd.DataFrame,
    *,
    z_threshold: float = 2.5,
    min_breaches: int = 3,
) -> pd.Series:
    rolling_mean = feature_frame.rolling(252, min_periods=20).mean()
    rolling_std = feature_frame.rolling(252, min_periods=20).std().replace(0.0, np.nan)
    zscores = ((feature_frame - rolling_mean) / rolling_std).abs()
    trigger_count = (zscores > float(z_threshold)).sum(axis=1)
    return trigger_count >= int(min_breaches)


def run_shadow_audit(
    *,
    training_end: str,
    evaluation_start: str,
    evaluation_end: str,
    artifact_dir: str | Path,
    raw_frame: pd.DataFrame | None = None,
    variant: RecoveryHmmVariant = LOCKED_CANDIDATE_VARIANT,
) -> dict[str, object]:
    if raw_frame is None:
        raise ValueError("run_shadow_audit currently requires an explicit raw_frame.")

    feature_frame = build_feature_space(raw_frame)
    training_end_ts = pd.Timestamp(training_end)
    evaluation_start_ts = pd.Timestamp(evaluation_start)
    evaluation_end_ts = pd.Timestamp(evaluation_end)

    train = feature_frame.loc[feature_frame.index <= training_end_ts].copy()
    evaluation = feature_frame.loc[
        (feature_frame.index >= evaluation_start_ts) & (feature_frame.index <= evaluation_end_ts)
    ].copy()
    if train.empty or evaluation.empty:
        raise ValueError("Training or evaluation window is empty.")

    projection = fit_pca_projection(train, variance_threshold=0.85)
    projected_eval = projection.transform(evaluation)
    fdas_series = _fdas_trigger(
        feature_frame,
        z_threshold=variant.fdas_z_threshold,
        min_breaches=variant.fdas_min_breaches,
    ).reindex(projected_eval.index).fillna(False)

    rows: list[dict[str, object]] = []
    for dt in projected_eval.index:
        row = evaluation.loc[dt]
        projected_row = projected_eval.loc[dt]
        orthogonal_confidence = _orthogonal_confidence(projected_row)
        probabilities = _domain_scores(row, variant, projected_row=projected_row)
        shadow_state = max(probabilities, key=probabilities.get)
        entropy = _normalized_entropy(probabilities)
        effective_entropy = entropy
        if shadow_state in {"RECOVERY", "MID_CYCLE"} and variant.orthogonal_entropy_relief > 0.0:
            effective_entropy = entropy * max(0.0, 1.0 - (variant.orthogonal_entropy_relief * orthogonal_confidence))
        weight = compute_shadow_weight(
            state=shadow_state,
            entropy=effective_entropy,
            fdas_triggered=bool(fdas_series.loc[dt]),
            preserve_production_floor=variant.preserve_production_floor,
            production_floor=variant.production_floor,
            entropy_threshold=variant.entropy_threshold,
            entropy_slope=variant.entropy_slope,
            entropy_floor=variant.entropy_floor,
            fdas_multiplier=variant.fdas_multiplier,
        )
        rows.append(
            {
                "date": dt,
                "variant": variant.name,
                "shadow_state": shadow_state,
                "prob_RECOVERY": probabilities["RECOVERY"],
                "prob_MID_CYCLE": probabilities["MID_CYCLE"],
                "prob_LATE_CYCLE": probabilities["LATE_CYCLE"],
                "prob_BUST": probabilities["BUST"],
                "entropy": entropy,
                "effective_entropy": effective_entropy,
                "orthogonal_confidence": orthogonal_confidence,
                "fdas_triggered": bool(fdas_series.loc[dt]),
                **weight,
            }
        )

    trace = pd.DataFrame(rows)
    q1_2022 = trace[(trace["date"] >= "2022-01-01") & (trace["date"] <= "2022-03-31")]
    q1_2023 = trace[(trace["date"] >= "2023-01-01") & (trace["date"] <= "2023-02-28")]
    acceptance = {
        "q1_2022_below_or_equal_0_5": bool(not q1_2022.empty and q1_2022["w_final"].min() <= 0.5),
        "q1_2023_above_or_equal_0_85": bool(not q1_2023.empty and q1_2023["w_final"].max() >= 0.85),
    }
    decision_gate = (
        "CANDIDATE_FOR_INTEGRATION"
        if all(acceptance.values())
        else "SHADOW_ONLY"
    )

    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    trace_path = artifact_path / "shadow_trace.csv"
    trace.to_csv(trace_path, index=False)

    summary = {
        "training_end": training_end_ts.date().isoformat(),
        "evaluation_start": evaluation_start_ts.date().isoformat(),
        "evaluation_end": evaluation_end_ts.date().isoformat(),
        "component_count": len(projection.components),
        "explained_variance_ratio_sum": projection.explained_variance_ratio_sum,
        "trace_path": str(trace_path),
        "acceptance": acceptance,
        "decision_gate": decision_gate,
        "variant": variant.to_dict(),
    }
    (artifact_path / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
