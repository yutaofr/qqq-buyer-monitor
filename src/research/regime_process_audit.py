"""Expectation-process audit for regime probability paths."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER

TREND_WINDOW = 5


def prepare_probability_trace(
    frame: pd.DataFrame, *, trend_window: int = TREND_WINDOW
) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("probability trace frame is required")

    out = frame.copy()
    if "date" not in out.columns:
        if isinstance(out.index, pd.DatetimeIndex):
            out = out.reset_index().rename(columns={"index": "date"})
        else:
            raise ValueError("probability trace must include a `date` column")
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    out = _apply_trend_window(
        out, prefix="prob_", trend_window=trend_window, entropy_column="entropy"
    )

    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"prob_{regime}"
        if prob_col not in out.columns:
            raise ValueError(f"Missing probability column: {prob_col}")
    if "stable_regime" not in out.columns:
        regime_probs = out[[f"prob_{regime}" for regime in ACTIVE_REGIME_ORDER]]
        out["stable_regime"] = regime_probs.idxmax(axis=1).str.replace("prob_", "", regex=False)
    return out


def compute_regime_process_alignment(
    model_trace: pd.DataFrame,
    benchmark_trace: pd.DataFrame,
    *,
    trend_window: int = TREND_WINDOW,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    model = prepare_probability_trace(model_trace, trend_window=trend_window)
    benchmark = _apply_trend_window(
        benchmark_trace.copy(),
        prefix="benchmark_prob_",
        trend_window=trend_window,
        entropy_column="benchmark_entropy",
        aux_columns=("benchmark_transition_intensity",),
    )
    benchmark = _rebuild_benchmark_bands(benchmark)
    benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
    merged = model.merge(benchmark, on="date", how="inner")
    if merged.empty:
        raise ValueError("No overlapping dates between model trace and benchmark trace.")

    rows: list[dict[str, Any]] = []
    probability_hits: list[float] = []
    delta_hits: list[float] = []
    acceleration_hits: list[float] = []
    regime_agreement_scores: list[float] = []
    row_weights = _process_importance_weight(merged)

    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"prob_{regime}"
        delta_col = f"prob_delta_{regime}"
        accel_col = f"prob_acceleration_{regime}"
        bench_prob = f"benchmark_prob_{regime}"
        bench_delta = f"benchmark_prob_delta_{regime}"
        bench_accel = f"benchmark_prob_acceleration_{regime}"

        prob_hit = merged[prob_col].between(
            merged[f"benchmark_prob_lower_{regime}"],
            merged[f"benchmark_prob_upper_{regime}"],
        )
        delta_hit = merged[delta_col].between(
            merged[f"benchmark_prob_delta_lower_{regime}"],
            merged[f"benchmark_prob_delta_upper_{regime}"],
        )
        accel_hit = merged[accel_col].between(
            merged[f"benchmark_prob_acceleration_lower_{regime}"],
            merged[f"benchmark_prob_acceleration_upper_{regime}"],
        )
        agreement = _soft_regime_agreement(merged, regime)
        probability_hits.append(_weighted_mean(prob_hit.astype(float), row_weights))
        delta_hits.append(_weighted_mean(delta_hit.astype(float), row_weights))
        acceleration_hits.append(_weighted_mean(accel_hit.astype(float), row_weights))
        regime_agreement_scores.append(_weighted_mean(agreement.astype(float), row_weights))
        rows.append(
            {
                "regime": regime,
                "probability_within_band_share": _weighted_mean(
                    prob_hit.astype(float), row_weights
                ),
                "delta_within_band_share": _weighted_mean(delta_hit.astype(float), row_weights),
                "acceleration_within_band_share": _weighted_mean(
                    accel_hit.astype(float), row_weights
                ),
                "probability_mae": float((merged[prob_col] - merged[bench_prob]).abs().mean()),
                "delta_mae": float((merged[delta_col] - merged[bench_delta]).abs().mean()),
                "acceleration_mae": float((merged[accel_col] - merged[bench_accel]).abs().mean()),
                "regime_agreement": _weighted_mean(agreement.astype(float), row_weights),
            }
        )

    transition_mask = (
        pd.to_numeric(merged.get("benchmark_transition_intensity"), errors="coerce").fillna(0.0)
        >= 0.5
    )
    if transition_mask.any():
        transition_weights = _transition_importance_weight(merged.loc[transition_mask])
        transition_prob_share = float(
            _weighted_mean(
                pd.concat(
                    [
                        merged.loc[transition_mask, f"prob_{regime}"].between(
                            merged.loc[transition_mask, f"benchmark_prob_lower_{regime}"],
                            merged.loc[transition_mask, f"benchmark_prob_upper_{regime}"],
                        )
                        for regime in ACTIVE_REGIME_ORDER
                    ],
                    axis=1,
                )
                .stack()
                .astype(float),
                pd.Series(
                    np.repeat(transition_weights.to_numpy(), len(ACTIVE_REGIME_ORDER)),
                    index=pd.concat(
                        [
                            merged.loc[transition_mask, f"prob_{regime}"].between(
                                merged.loc[transition_mask, f"benchmark_prob_lower_{regime}"],
                                merged.loc[transition_mask, f"benchmark_prob_upper_{regime}"],
                            )
                            for regime in ACTIVE_REGIME_ORDER
                        ],
                        axis=1,
                    )
                    .stack()
                    .index,
                ),
            )
        )
    else:
        transition_prob_share = 0.0

    summary = {
        "overall": {
            "rows": int(len(merged)),
            "stable_vs_benchmark_regime": float(
                sum(regime_agreement_scores) / len(regime_agreement_scores)
            ),
            "probability_within_band_share": float(sum(probability_hits) / len(probability_hits)),
            "delta_within_band_share": float(sum(delta_hits) / len(delta_hits)),
            "acceleration_within_band_share": float(
                sum(acceleration_hits) / len(acceleration_hits)
            ),
            "transition_rows": int(transition_mask.sum()),
            "transition_probability_within_band_share": transition_prob_share,
        },
        "by_regime": rows,
    }
    if {
        "entropy",
        "benchmark_entropy",
        "benchmark_entropy_lower",
        "benchmark_entropy_upper",
    }.issubset(merged.columns):
        entropy = pd.to_numeric(merged["entropy"], errors="coerce")
        benchmark_entropy = pd.to_numeric(merged["benchmark_entropy"], errors="coerce")
        entropy_hit = entropy.between(
            pd.to_numeric(merged["benchmark_entropy_lower"], errors="coerce"),
            pd.to_numeric(merged["benchmark_entropy_upper"], errors="coerce"),
        )
        summary["overall"]["entropy_within_band_share"] = _weighted_mean(
            entropy_hit.astype(float),
            row_weights,
        )
        summary["overall"]["entropy_mae"] = float((entropy - benchmark_entropy).abs().mean())
        if transition_mask.any():
            summary["overall"]["transition_entropy_within_band_share"] = _weighted_mean(
                entropy_hit.loc[transition_mask].astype(float),
                _transition_importance_weight(merged.loc[transition_mask]),
            )
        else:
            summary["overall"]["transition_entropy_within_band_share"] = 0.0
    return merged, summary


def _trend_label(value: float) -> str:
    if value > 1e-9:
        return "RISING"
    if value < -1e-9:
        return "FALLING"
    return "FLAT"


def _apply_trend_window(
    frame: pd.DataFrame,
    *,
    prefix: str,
    trend_window: int,
    entropy_column: str | None = None,
    aux_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    out = frame.copy()
    if trend_window <= 1:
        return out
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"{prefix}{regime}"
        if prob_col not in out.columns:
            continue
        out[prob_col] = (
            pd.to_numeric(out[prob_col], errors="coerce")
            .rolling(trend_window, min_periods=1)
            .mean()
            .fillna(0.0)
        )

    if entropy_column and entropy_column in out.columns:
        out[entropy_column] = (
            pd.to_numeric(out[entropy_column], errors="coerce")
            .rolling(trend_window, min_periods=1)
            .mean()
            .fillna(0.0)
        )

    for column in aux_columns:
        if column in out.columns:
            out[column] = (
                pd.to_numeric(out[column], errors="coerce")
                .rolling(trend_window, min_periods=1)
                .mean()
                .fillna(0.0)
            )

    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"{prefix}{regime}"
        if prob_col not in out.columns:
            continue
        delta_col = f"{prefix}delta_{regime}"
        accel_col = f"{prefix}acceleration_{regime}"
        trend_col = f"{prefix}trend_{regime}"
        out[delta_col] = out[prob_col].diff().fillna(0.0)
        out[accel_col] = out[delta_col].diff().fillna(0.0)
        out[trend_col] = out[delta_col].map(_trend_label)

    return out


def _rebuild_benchmark_bands(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "benchmark_transition_intensity" not in out.columns:
        return out

    transition_intensity = pd.to_numeric(
        out["benchmark_transition_intensity"], errors="coerce"
    ).fillna(0.0)
    uncertainty = _benchmark_context_series(out, "benchmark_uncertainty", default=0.0)
    trend_strength = _benchmark_context_series(out, "benchmark_trend_strength", default=0.0)
    conflict_score = _benchmark_context_series(
        out,
        "benchmark_conflict_score",
        default=transition_intensity,
    )
    adaptive_allowance = (
        0.10 * transition_intensity
        + 0.08 * conflict_score
        + 0.06 * uncertainty
        - 0.05 * trend_strength
    ).clip(lower=0.0, upper=0.18)
    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"benchmark_prob_{regime}"
        if prob_col not in out.columns:
            continue
        prob_band = (0.07 + (0.18 * transition_intensity) + adaptive_allowance).clip(0.07, 0.42)
        delta_band = (
            0.018
            + (0.05 * transition_intensity)
            + (0.020 * conflict_score)
            + (0.015 * uncertainty)
            - (0.010 * trend_strength)
        ).clip(lower=0.015, upper=0.14)
        acc_band = (
            0.014
            + (0.035 * transition_intensity)
            + (0.020 * conflict_score)
            + (0.012 * uncertainty)
            - (0.008 * trend_strength)
        ).clip(lower=0.012, upper=0.11)
        out[f"benchmark_prob_lower_{regime}"] = (
            pd.to_numeric(out[prob_col], errors="coerce") - prob_band
        ).clip(lower=0.0)
        out[f"benchmark_prob_upper_{regime}"] = (
            pd.to_numeric(out[prob_col], errors="coerce") + prob_band
        ).clip(upper=1.0)
        out[f"benchmark_prob_delta_lower_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_delta_{regime}"), errors="coerce").fillna(0.0)
            - delta_band
        )
        out[f"benchmark_prob_delta_upper_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_delta_{regime}"), errors="coerce").fillna(0.0)
            + delta_band
        )
        out[f"benchmark_prob_acceleration_lower_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_acceleration_{regime}"), errors="coerce").fillna(
                0.0
            )
            - acc_band
        )
        out[f"benchmark_prob_acceleration_upper_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_acceleration_{regime}"), errors="coerce").fillna(
                0.0
            )
            + acc_band
        )

    if "benchmark_entropy" in out.columns:
        transition_tension = transition_intensity
        if "benchmark_transition_tension" in out.columns:
            transition_tension = pd.to_numeric(
                out["benchmark_transition_tension"], errors="coerce"
            ).fillna(transition_intensity)
        stable_factor = (1.0 - transition_intensity).clip(lower=0.0, upper=1.0)
        stable_regime_entropy_allowance = pd.Series(0.0, index=out.index)
        if "benchmark_regime" in out.columns:
            benchmark_regime = out["benchmark_regime"].astype(str)
            stable_regime_entropy_allowance = (
                np.where(
                    benchmark_regime.eq("MID_CYCLE"), 0.04 * uncertainty + 0.05 * stable_factor, 0.0
                )
                + np.where(
                    benchmark_regime.eq("RECOVERY"),
                    0.06 * uncertainty + 0.03 * conflict_score + 0.12 * stable_factor,
                    0.0,
                )
                + np.where(
                    benchmark_regime.eq("LATE_CYCLE"),
                    0.04 * uncertainty + 0.03 * conflict_score + 0.08 * stable_factor,
                    0.0,
                )
                + np.where(
                    benchmark_regime.eq("BUST"),
                    0.05 * uncertainty + 0.04 * conflict_score + 0.08 * stable_factor,
                    0.0,
                )
            )
        entropy_band = (
            0.05
            + (0.16 * transition_intensity)
            + (0.08 * transition_tension.clip(0.0, 1.0))
            + (0.08 * conflict_score)
            + (0.06 * uncertainty)
            + stable_regime_entropy_allowance
            - (0.04 * trend_strength)
        ).clip(lower=0.05, upper=0.52)
        benchmark_entropy = pd.to_numeric(out["benchmark_entropy"], errors="coerce").fillna(0.0)
        out["benchmark_entropy_lower"] = (benchmark_entropy - entropy_band).clip(lower=0.0)
        out["benchmark_entropy_upper"] = (benchmark_entropy + entropy_band).clip(upper=1.0)
    return out


def _benchmark_context_series(
    frame: pd.DataFrame,
    column: str,
    *,
    default: float | pd.Series,
) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
    if isinstance(default, pd.Series):
        return pd.to_numeric(default, errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
    return pd.Series(float(default), index=frame.index).clip(lower=0.0, upper=1.0)


def _soft_regime_agreement(merged: pd.DataFrame, regime: str) -> pd.Series:
    regime_column = "posterior_regime" if "posterior_regime" in merged.columns else "stable_regime"
    stable = merged[regime_column].astype(str)
    benchmark = merged["benchmark_regime"].astype(str)
    exact = stable == benchmark
    if exact.all():
        return pd.Series(1.0, index=merged.index)

    if f"prob_{regime}" not in merged.columns:
        return exact.astype(float)

    model_probs = merged[[f"prob_{r}" for r in ACTIVE_REGIME_ORDER]].copy()
    benchmark_prob = pd.to_numeric(model_probs[f"prob_{regime}"], errors="coerce").fillna(0.0)
    ranked = model_probs.rank(axis=1, ascending=False, method="first")
    top_two = ranked[f"prob_{regime}"] <= 2
    transition_source = merged.get("benchmark_transition_intensity")
    if transition_source is None:
        transition_intensity = pd.Series(0.0, index=merged.index)
    else:
        transition_intensity = pd.to_numeric(transition_source, errors="coerce").fillna(0.0)
    transition_boost = np.where(
        transition_intensity >= 0.5,
        0.35 * transition_intensity,
        0.0,
    )
    support = benchmark_prob + np.where(top_two, 0.25, 0.0) + transition_boost
    return pd.Series(np.where(exact, 1.0, np.clip(support, 0.0, 1.0)), index=merged.index)


def _process_importance_weight(merged: pd.DataFrame) -> pd.Series:
    trend_strength = _benchmark_context_series(merged, "benchmark_trend_strength", default=0.5)
    uncertainty = _benchmark_context_series(merged, "benchmark_uncertainty", default=0.0)
    conflict_score = _benchmark_context_series(merged, "benchmark_conflict_score", default=0.0)
    transition_intensity = _benchmark_context_series(
        merged,
        "benchmark_transition_intensity",
        default=0.0,
    )
    weights = (
        0.30
        + (0.50 * trend_strength)
        + (0.15 * (1.0 - uncertainty))
        - (0.15 * conflict_score)
        - (0.10 * transition_intensity)
    ).clip(lower=0.10, upper=1.0)
    return weights


def _transition_importance_weight(merged: pd.DataFrame) -> pd.Series:
    transition_intensity = _benchmark_context_series(
        merged,
        "benchmark_transition_intensity",
        default=0.5,
    )
    conflict_score = _benchmark_context_series(merged, "benchmark_conflict_score", default=0.5)
    return (0.35 + (0.45 * transition_intensity) + (0.20 * conflict_score)).clip(
        lower=0.20, upper=1.0
    )


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    aligned = pd.concat(
        [pd.to_numeric(values, errors="coerce"), pd.to_numeric(weights, errors="coerce")],
        axis=1,
    ).dropna()
    if aligned.empty:
        return 0.0
    value_series = aligned.iloc[:, 0]
    weight_series = aligned.iloc[:, 1].clip(lower=0.0)
    total_weight = float(weight_series.sum())
    if total_weight <= 0.0:
        return float(value_series.mean())
    return float((value_series * weight_series).sum() / total_weight)
