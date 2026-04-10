"""Expectation-process audit for regime probability paths."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER

TREND_WINDOW = 5


def prepare_probability_trace(frame: pd.DataFrame, *, trend_window: int = TREND_WINDOW) -> pd.DataFrame:
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

    out = _apply_trend_window(out, prefix="prob_", trend_window=trend_window, entropy_column="entropy")

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
        probability_hits.append(float(prob_hit.mean()))
        delta_hits.append(float(delta_hit.mean()))
        acceleration_hits.append(float(accel_hit.mean()))
        regime_agreement_scores.append(float(agreement.mean()))
        rows.append(
            {
                "regime": regime,
                "probability_within_band_share": float(prob_hit.mean()),
                "delta_within_band_share": float(delta_hit.mean()),
                "acceleration_within_band_share": float(accel_hit.mean()),
                "probability_mae": float((merged[prob_col] - merged[bench_prob]).abs().mean()),
                "delta_mae": float((merged[delta_col] - merged[bench_delta]).abs().mean()),
                "acceleration_mae": float((merged[accel_col] - merged[bench_accel]).abs().mean()),
                "regime_agreement": float(agreement.mean()),
            }
        )

    transition_mask = pd.to_numeric(
        merged.get("benchmark_transition_intensity"), errors="coerce"
    ).fillna(0.0) >= 0.5
    if transition_mask.any():
        transition_prob_share = float(
            pd.concat(
                [
                    merged.loc[transition_mask, f"prob_{regime}"].between(
                        merged.loc[transition_mask, f"benchmark_prob_lower_{regime}"],
                        merged.loc[transition_mask, f"benchmark_prob_upper_{regime}"],
                    )
                    for regime in ACTIVE_REGIME_ORDER
                ],
                axis=1,
            ).stack().mean()
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
            "acceleration_within_band_share": float(sum(acceleration_hits) / len(acceleration_hits)),
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
        summary["overall"]["entropy_within_band_share"] = float(entropy_hit.mean())
        summary["overall"]["entropy_mae"] = float((entropy - benchmark_entropy).abs().mean())
        if transition_mask.any():
            summary["overall"]["transition_entropy_within_band_share"] = float(
                entropy_hit.loc[transition_mask].mean()
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

    transition_intensity = pd.to_numeric(out["benchmark_transition_intensity"], errors="coerce").fillna(0.0)
    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"benchmark_prob_{regime}"
        if prob_col not in out.columns:
            continue
        prob_band = 0.08 + (0.20 * transition_intensity)
        delta_band = 0.02 + (0.06 * transition_intensity)
        acc_band = 0.015 + (0.04 * transition_intensity)
        out[f"benchmark_prob_lower_{regime}"] = (pd.to_numeric(out[prob_col], errors="coerce") - prob_band).clip(lower=0.0)
        out[f"benchmark_prob_upper_{regime}"] = (pd.to_numeric(out[prob_col], errors="coerce") + prob_band).clip(upper=1.0)
        out[f"benchmark_prob_delta_lower_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_delta_{regime}"), errors="coerce").fillna(0.0)
            - delta_band
        )
        out[f"benchmark_prob_delta_upper_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_delta_{regime}"), errors="coerce").fillna(0.0)
            + delta_band
        )
        out[f"benchmark_prob_acceleration_lower_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_acceleration_{regime}"), errors="coerce").fillna(0.0)
            - acc_band
        )
        out[f"benchmark_prob_acceleration_upper_{regime}"] = (
            pd.to_numeric(out.get(f"benchmark_prob_acceleration_{regime}"), errors="coerce").fillna(0.0)
            + acc_band
        )

    if "benchmark_entropy" in out.columns:
        transition_tension = transition_intensity
        if "benchmark_transition_tension" in out.columns:
            transition_tension = pd.to_numeric(out["benchmark_transition_tension"], errors="coerce").fillna(
                transition_intensity
            )
        entropy_band = (0.05 + (0.20 * transition_intensity) + (0.06 * transition_tension)).clip(
            lower=0.05,
            upper=0.30,
        )
        benchmark_entropy = pd.to_numeric(out["benchmark_entropy"], errors="coerce").fillna(0.0)
        out["benchmark_entropy_lower"] = (benchmark_entropy - entropy_band).clip(lower=0.0)
        out["benchmark_entropy_upper"] = (benchmark_entropy + entropy_band).clip(upper=1.0)
    return out


def _soft_regime_agreement(merged: pd.DataFrame, regime: str) -> pd.Series:
    stable = merged["stable_regime"].astype(str)
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
