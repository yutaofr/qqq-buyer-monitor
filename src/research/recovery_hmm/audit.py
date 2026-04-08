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


def _domain_scores(feature_row: pd.Series) -> dict[str, float]:
    spread = float(feature_row["L1_hy_ig_spread"])
    curve = float(feature_row["L2_curve_10y_2y"])
    fci = float(feature_row["L3_chicago_fci"])
    spread_velocity = float(feature_row["V1_spread_compression_velocity"])
    real_yield_velocity = float(feature_row["V2_real_yield_velocity"])
    orders_gap = float(feature_row["V3_orders_inventory_gap"])
    term_ratio = float(feature_row["S1_vix_term_ratio"])
    skew = float(feature_row["S2_qqq_skew_mean"])

    decay_score = max(0.0, spread_velocity + max(0.0, -real_yield_velocity) + max(0.0, orders_gap / 10.0))
    level_score = max(0.0, curve - max(0.0, fci) - max(0.0, spread / 10.0) + max(0.0, term_ratio - 1.0))
    recovery_transition = recovery_to_midcycle_probability(level_score=level_score, decay_score=decay_score)

    scores = {
        "RECOVERY": (1.8 * decay_score) + max(0.0, term_ratio - 1.0) + max(0.0, 0.7 - skew),
        "MID_CYCLE": (2.5 * recovery_transition) + max(0.0, curve) + max(0.0, orders_gap / 8.0),
        "LATE_CYCLE": max(0.0, spread / 8.0) + max(0.0, skew - 0.5) + max(0.0, 1.0 - term_ratio),
        "BUST": max(0.0, spread / 5.0) + max(0.0, fci) + max(0.0, 1.0 - term_ratio) + max(0.0, skew - 0.45),
    }
    return _softmax(scores)


def _fdas_trigger(feature_frame: pd.DataFrame) -> pd.Series:
    rolling_mean = feature_frame.rolling(252, min_periods=20).mean()
    rolling_std = feature_frame.rolling(252, min_periods=20).std().replace(0.0, np.nan)
    zscores = ((feature_frame - rolling_mean) / rolling_std).abs()
    trigger_count = (zscores > 2.5).sum(axis=1)
    return trigger_count >= 3


def run_shadow_audit(
    *,
    training_end: str,
    evaluation_start: str,
    evaluation_end: str,
    artifact_dir: str | Path,
    raw_frame: pd.DataFrame | None = None,
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
    fdas_series = _fdas_trigger(feature_frame).reindex(projected_eval.index).fillna(False)

    rows: list[dict[str, object]] = []
    for dt in projected_eval.index:
        row = evaluation.loc[dt]
        probabilities = _domain_scores(row)
        shadow_state = max(probabilities, key=probabilities.get)
        entropy = _normalized_entropy(probabilities)
        weight = compute_shadow_weight(
            state=shadow_state,
            entropy=entropy,
            fdas_triggered=bool(fdas_series.loc[dt]),
            preserve_production_floor=True,
        )
        rows.append(
            {
                "date": dt,
                "shadow_state": shadow_state,
                "prob_RECOVERY": probabilities["RECOVERY"],
                "prob_MID_CYCLE": probabilities["MID_CYCLE"],
                "prob_LATE_CYCLE": probabilities["LATE_CYCLE"],
                "prob_BUST": probabilities["BUST"],
                "entropy": entropy,
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
    }
    (artifact_path / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
