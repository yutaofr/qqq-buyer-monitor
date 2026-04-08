"""Expectation-process audit for regime probability paths."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER


def prepare_probability_trace(frame: pd.DataFrame) -> pd.DataFrame:
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

    for regime in ACTIVE_REGIME_ORDER:
        prob_col = f"prob_{regime}"
        if prob_col not in out.columns:
            raise ValueError(f"Missing probability column: {prob_col}")
        out[prob_col] = pd.to_numeric(out[prob_col], errors="coerce").fillna(0.0)
        delta_col = f"prob_delta_{regime}"
        accel_col = f"prob_acceleration_{regime}"
        trend_col = f"prob_trend_{regime}"
        if delta_col not in out.columns:
            out[delta_col] = out[prob_col].diff().fillna(0.0)
        else:
            out[delta_col] = pd.to_numeric(out[delta_col], errors="coerce").fillna(0.0)
        if accel_col not in out.columns:
            out[accel_col] = out[delta_col].diff().fillna(0.0)
        else:
            out[accel_col] = pd.to_numeric(out[accel_col], errors="coerce").fillna(0.0)
        if trend_col not in out.columns:
            out[trend_col] = out[delta_col].map(_trend_label)
    if "stable_regime" not in out.columns:
        regime_probs = out[[f"prob_{regime}" for regime in ACTIVE_REGIME_ORDER]]
        out["stable_regime"] = regime_probs.idxmax(axis=1).str.replace("prob_", "", regex=False)
    return out


def compute_regime_process_alignment(
    model_trace: pd.DataFrame,
    benchmark_trace: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    model = prepare_probability_trace(model_trace)
    benchmark = benchmark_trace.copy()
    benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
    merged = model.merge(benchmark, on="date", how="inner")
    if merged.empty:
        raise ValueError("No overlapping dates between model trace and benchmark trace.")

    rows: list[dict[str, Any]] = []
    probability_hits: list[float] = []
    delta_hits: list[float] = []
    acceleration_hits: list[float] = []

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
        probability_hits.append(float(prob_hit.mean()))
        delta_hits.append(float(delta_hit.mean()))
        acceleration_hits.append(float(accel_hit.mean()))
        rows.append(
            {
                "regime": regime,
                "probability_within_band_share": float(prob_hit.mean()),
                "delta_within_band_share": float(delta_hit.mean()),
                "acceleration_within_band_share": float(accel_hit.mean()),
                "probability_mae": float((merged[prob_col] - merged[bench_prob]).abs().mean()),
                "delta_mae": float((merged[delta_col] - merged[bench_delta]).abs().mean()),
                "acceleration_mae": float((merged[accel_col] - merged[bench_accel]).abs().mean()),
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
            "stable_vs_benchmark_regime": float((merged["stable_regime"] == merged["benchmark_regime"]).mean()),
            "probability_within_band_share": float(sum(probability_hits) / len(probability_hits)),
            "delta_within_band_share": float(sum(delta_hits) / len(delta_hits)),
            "acceleration_within_band_share": float(sum(acceleration_hits) / len(acceleration_hits)),
            "transition_rows": int(transition_mask.sum()),
            "transition_probability_within_band_share": transition_prob_share,
        },
        "by_regime": rows,
    }
    return merged, summary


def _trend_label(value: float) -> str:
    if value > 1e-9:
        return "RISING"
    if value < -1e-9:
        return "FALLING"
    return "FLAT"
