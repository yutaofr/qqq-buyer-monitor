from __future__ import annotations

import pandas as pd
import pytest

from src.research.regime_process_audit import (
    compute_regime_process_alignment,
    prepare_probability_trace,
)


def test_prepare_probability_trace_derives_delta_and_acceleration_columns():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="B"),
            "prob_MID_CYCLE": [0.4, 0.5, 0.6],
            "prob_LATE_CYCLE": [0.3, 0.25, 0.2],
            "prob_BUST": [0.2, 0.15, 0.1],
            "prob_RECOVERY": [0.1, 0.1, 0.1],
        }
    )

    prepared = prepare_probability_trace(frame)

    assert "prob_delta_MID_CYCLE" in prepared.columns
    assert "prob_acceleration_MID_CYCLE" in prepared.columns


def test_prepare_probability_trace_trend_window_smooths_jitter():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="B"),
            "prob_MID_CYCLE": [0.60, 0.80, 0.60],
            "prob_LATE_CYCLE": [0.20, 0.05, 0.20],
            "prob_BUST": [0.10, 0.10, 0.10],
            "prob_RECOVERY": [0.10, 0.05, 0.10],
            "entropy": [0.42, 0.25, 0.41],
        }
    )

    prepared = prepare_probability_trace(frame, trend_window=3)

    assert prepared.loc[1, "prob_MID_CYCLE"] == pytest.approx((0.60 + 0.80) / 2.0)
    assert abs(prepared.loc[1, "prob_acceleration_MID_CYCLE"]) < 0.2
    assert prepared.loc[1, "entropy"] == pytest.approx((0.42 + 0.25) / 2.0)


def test_compute_regime_process_alignment_scores_within_band_share():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    benchmark = pd.DataFrame(
        {
            "date": dates,
            "benchmark_regime": ["MID_CYCLE"] * 4,
            "benchmark_transition_intensity": [0.1, 0.2, 0.2, 0.1],
            "benchmark_entropy": [0.62, 0.60, 0.58, 0.55],
            "benchmark_entropy_lower": [0.52, 0.50, 0.48, 0.45],
            "benchmark_entropy_upper": [0.72, 0.70, 0.68, 0.65],
            "benchmark_prob_MID_CYCLE": [0.55, 0.60, 0.63, 0.66],
            "benchmark_prob_LATE_CYCLE": [0.20, 0.18, 0.17, 0.16],
            "benchmark_prob_BUST": [0.15, 0.12, 0.10, 0.09],
            "benchmark_prob_RECOVERY": [0.10, 0.10, 0.10, 0.09],
        }
    )
    for regime in ("MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"):
        benchmark[f"benchmark_prob_delta_{regime}"] = (
            benchmark[f"benchmark_prob_{regime}"].diff().fillna(0.0)
        )
        benchmark[f"benchmark_prob_acceleration_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"].diff().fillna(0.0)
        )
        benchmark[f"benchmark_prob_lower_{regime}"] = benchmark[f"benchmark_prob_{regime}"] - 0.05
        benchmark[f"benchmark_prob_upper_{regime}"] = benchmark[f"benchmark_prob_{regime}"] + 0.05
        benchmark[f"benchmark_prob_delta_lower_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] - 0.03
        )
        benchmark[f"benchmark_prob_delta_upper_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] + 0.03
        )
        benchmark[f"benchmark_prob_acceleration_lower_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] - 0.03
        )
        benchmark[f"benchmark_prob_acceleration_upper_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] + 0.03
        )

    model = pd.DataFrame(
        {
            "date": dates,
            "stable_regime": ["MID_CYCLE"] * 4,
            "prob_MID_CYCLE": [0.56, 0.59, 0.62, 0.67],
            "prob_LATE_CYCLE": [0.19, 0.19, 0.16, 0.15],
            "prob_BUST": [0.15, 0.13, 0.11, 0.09],
            "prob_RECOVERY": [0.10, 0.09, 0.11, 0.09],
            "entropy": [0.61, 0.59, 0.56, 0.57],
        }
    )

    merged, summary = compute_regime_process_alignment(model, benchmark)

    assert not merged.empty
    assert summary["overall"]["probability_within_band_share"] > 0.9
    assert summary["overall"]["delta_within_band_share"] > 0.8
    assert summary["overall"]["entropy_within_band_share"] > 0.9


def test_compute_regime_process_alignment_rewards_transition_overlap():
    dates = pd.date_range("2024-06-03", periods=3, freq="B")
    benchmark = pd.DataFrame(
        {
            "date": dates,
            "benchmark_regime": ["RECOVERY", "RECOVERY", "RECOVERY"],
            "benchmark_transition_intensity": [0.82, 0.88, 0.84],
            "benchmark_entropy": [0.74, 0.76, 0.75],
            "benchmark_entropy_lower": [0.64, 0.66, 0.65],
            "benchmark_entropy_upper": [0.84, 0.86, 0.85],
        }
    )
    for regime, values in {
        "MID_CYCLE": [0.29, 0.31, 0.30],
        "LATE_CYCLE": [0.22, 0.20, 0.21],
        "BUST": [0.19, 0.18, 0.19],
        "RECOVERY": [0.30, 0.31, 0.30],
    }.items():
        benchmark[f"benchmark_prob_{regime}"] = values
        benchmark[f"benchmark_prob_delta_{regime}"] = pd.Series(values).diff().fillna(0.0)
        benchmark[f"benchmark_prob_acceleration_{regime}"] = (
            pd.Series(benchmark[f"benchmark_prob_delta_{regime}"]).diff().fillna(0.0)
        )
        benchmark[f"benchmark_prob_lower_{regime}"] = benchmark[f"benchmark_prob_{regime}"] - 0.05
        benchmark[f"benchmark_prob_upper_{regime}"] = benchmark[f"benchmark_prob_{regime}"] + 0.05
        benchmark[f"benchmark_prob_delta_lower_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] - 0.03
        )
        benchmark[f"benchmark_prob_delta_upper_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] + 0.03
        )
        benchmark[f"benchmark_prob_acceleration_lower_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] - 0.03
        )
        benchmark[f"benchmark_prob_acceleration_upper_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] + 0.03
        )

    model = pd.DataFrame(
        {
            "date": dates,
            "stable_regime": ["MID_CYCLE"] * 3,
            "prob_MID_CYCLE": [0.34, 0.32, 0.33],
            "prob_LATE_CYCLE": [0.21, 0.20, 0.21],
            "prob_BUST": [0.18, 0.18, 0.17],
            "prob_RECOVERY": [0.27, 0.30, 0.29],
            "entropy": [0.72, 0.74, 0.73],
        }
    )

    merged, summary = compute_regime_process_alignment(model, benchmark)

    assert not merged.empty
    assert summary["overall"]["stable_vs_benchmark_regime"] > 0.5


def test_compute_regime_process_alignment_widens_bands_for_noisy_stable_windows():
    dates = pd.date_range("2024-01-01", periods=2, freq="B")
    benchmark = pd.DataFrame(
        {
            "date": dates,
            "benchmark_regime": ["MID_CYCLE", "MID_CYCLE"],
            "benchmark_transition_intensity": [0.10, 0.10],
            "benchmark_transition_tension": [0.05, 0.80],
            "benchmark_uncertainty": [0.08, 0.34],
            "benchmark_trend_strength": [0.88, 0.24],
            "benchmark_conflict_score": [0.06, 0.82],
            "benchmark_entropy": [0.22, 0.44],
        }
    )
    for regime, values in {
        "MID_CYCLE": [0.76, 0.76],
        "LATE_CYCLE": [0.12, 0.12],
        "BUST": [0.07, 0.07],
        "RECOVERY": [0.05, 0.05],
    }.items():
        benchmark[f"benchmark_prob_{regime}"] = values
        benchmark[f"benchmark_prob_delta_{regime}"] = 0.0
        benchmark[f"benchmark_prob_acceleration_{regime}"] = 0.0

    model = pd.DataFrame(
        {
            "date": dates,
            "stable_regime": ["MID_CYCLE", "MID_CYCLE"],
            "prob_MID_CYCLE": [0.83, 0.83],
            "prob_LATE_CYCLE": [0.09, 0.09],
            "prob_BUST": [0.04, 0.04],
            "prob_RECOVERY": [0.04, 0.04],
            "entropy": [0.31, 0.59],
        }
    )

    merged, _ = compute_regime_process_alignment(model, benchmark)

    tight_prob_width = (
        merged.loc[0, "benchmark_prob_upper_MID_CYCLE"]
        - merged.loc[0, "benchmark_prob_lower_MID_CYCLE"]
    )
    noisy_prob_width = (
        merged.loc[1, "benchmark_prob_upper_MID_CYCLE"]
        - merged.loc[1, "benchmark_prob_lower_MID_CYCLE"]
    )
    tight_entropy_width = (
        merged.loc[0, "benchmark_entropy_upper"] - merged.loc[0, "benchmark_entropy_lower"]
    )
    noisy_entropy_width = (
        merged.loc[1, "benchmark_entropy_upper"] - merged.loc[1, "benchmark_entropy_lower"]
    )

    assert noisy_prob_width > tight_prob_width
    assert noisy_entropy_width > tight_entropy_width
