from __future__ import annotations

import pandas as pd

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


def test_compute_regime_process_alignment_scores_within_band_share():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    benchmark = pd.DataFrame(
        {
            "date": dates,
            "benchmark_regime": ["MID_CYCLE"] * 4,
            "benchmark_transition_intensity": [0.1, 0.2, 0.2, 0.1],
            "benchmark_prob_MID_CYCLE": [0.55, 0.60, 0.63, 0.66],
            "benchmark_prob_LATE_CYCLE": [0.20, 0.18, 0.17, 0.16],
            "benchmark_prob_BUST": [0.15, 0.12, 0.10, 0.09],
            "benchmark_prob_RECOVERY": [0.10, 0.10, 0.10, 0.09],
        }
    )
    for regime in ("MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"):
        benchmark[f"benchmark_prob_delta_{regime}"] = benchmark[f"benchmark_prob_{regime}"].diff().fillna(0.0)
        benchmark[f"benchmark_prob_acceleration_{regime}"] = benchmark[f"benchmark_prob_delta_{regime}"].diff().fillna(0.0)
        benchmark[f"benchmark_prob_lower_{regime}"] = benchmark[f"benchmark_prob_{regime}"] - 0.05
        benchmark[f"benchmark_prob_upper_{regime}"] = benchmark[f"benchmark_prob_{regime}"] + 0.05
        benchmark[f"benchmark_prob_delta_lower_{regime}"] = benchmark[f"benchmark_prob_delta_{regime}"] - 0.03
        benchmark[f"benchmark_prob_delta_upper_{regime}"] = benchmark[f"benchmark_prob_delta_{regime}"] + 0.03
        benchmark[f"benchmark_prob_acceleration_lower_{regime}"] = benchmark[f"benchmark_prob_acceleration_{regime}"] - 0.03
        benchmark[f"benchmark_prob_acceleration_upper_{regime}"] = benchmark[f"benchmark_prob_acceleration_{regime}"] + 0.03

    model = pd.DataFrame(
        {
            "date": dates,
            "stable_regime": ["MID_CYCLE"] * 4,
            "prob_MID_CYCLE": [0.56, 0.59, 0.62, 0.67],
            "prob_LATE_CYCLE": [0.19, 0.19, 0.16, 0.15],
            "prob_BUST": [0.15, 0.13, 0.11, 0.09],
            "prob_RECOVERY": [0.10, 0.09, 0.11, 0.09],
        }
    )

    merged, summary = compute_regime_process_alignment(model, benchmark)

    assert not merged.empty
    assert summary["overall"]["probability_within_band_share"] > 0.9
    assert summary["overall"]["delta_within_band_share"] > 0.8
