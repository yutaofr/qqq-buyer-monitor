from __future__ import annotations

import pandas as pd

from scripts.run_v14_panorama_matrix import _scenario_report, _select_candidate


def test_scenario_report_does_not_force_standard_to_pass():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "close": [100.0, 101.0, 102.0, 101.0],
            "standard_beta": [0.95, 0.95, 0.95, 0.95],
            "s4_sidecar_beta": [0.80, 0.80, 0.80, 0.80],
            "s5_tractor_beta": [0.75, 0.75, 0.75, 0.75],
            "panorama_beta": [0.70, 0.70, 0.70, 0.70],
            "target_beta": [0.95, 0.95, 0.95, 0.95],
            "raw_target_beta": [1.0, 1.0, 1.0, 1.0],
            "expected_target_beta": [0.95, 0.95, 0.95, 0.95],
            "stable_regime": ["MID_CYCLE"] * 4,
            "prob_MID_CYCLE": [0.30, 0.30, 0.30, 0.30],
            "prob_LATE_CYCLE": [0.30, 0.30, 0.30, 0.30],
            "prob_BUST": [0.20, 0.20, 0.20, 0.20],
            "prob_RECOVERY": [0.20, 0.20, 0.20, 0.20],
            "entropy": [0.95, 0.95, 0.95, 0.95],
            "benchmark_regime": ["MID_CYCLE"] * 4,
            "benchmark_transition_intensity": [0.1, 0.1, 0.1, 0.1],
            "benchmark_entropy": [0.20, 0.20, 0.20, 0.20],
            "benchmark_entropy_lower": [0.15, 0.15, 0.15, 0.15],
            "benchmark_entropy_upper": [0.25, 0.25, 0.25, 0.25],
        }
    )
    for regime, values in {
        "MID_CYCLE": [0.70, 0.72, 0.74, 0.76],
        "LATE_CYCLE": [0.15, 0.14, 0.13, 0.12],
        "BUST": [0.10, 0.09, 0.08, 0.07],
        "RECOVERY": [0.05, 0.05, 0.05, 0.05],
    }.items():
        frame[f"benchmark_prob_{regime}"] = values
        frame[f"benchmark_prob_delta_{regime}"] = pd.Series(values).diff().fillna(0.0)
        frame[f"benchmark_prob_acceleration_{regime}"] = (
            pd.Series(frame[f"benchmark_prob_delta_{regime}"]).diff().fillna(0.0)
        )
        frame[f"benchmark_prob_lower_{regime}"] = frame[f"benchmark_prob_{regime}"] - 0.02
        frame[f"benchmark_prob_upper_{regime}"] = frame[f"benchmark_prob_{regime}"] + 0.02
        frame[f"benchmark_prob_delta_lower_{regime}"] = (
            frame[f"benchmark_prob_delta_{regime}"] - 0.01
        )
        frame[f"benchmark_prob_delta_upper_{regime}"] = (
            frame[f"benchmark_prob_delta_{regime}"] + 0.01
        )
        frame[f"benchmark_prob_acceleration_lower_{regime}"] = (
            frame[f"benchmark_prob_acceleration_{regime}"] - 0.01
        )
        frame[f"benchmark_prob_acceleration_upper_{regime}"] = (
            frame[f"benchmark_prob_acceleration_{regime}"] + 0.01
        )

    report = _scenario_report(frame)
    standard = report.loc[report["scenario"] == "standard"].iloc[0]

    assert bool(standard["acceptance_pass"]) is False
    assert "Worldview Process Failure" in str(standard["acceptance_reason"])


def test_select_candidate_fails_closed_to_standard_when_nothing_passes():
    report = pd.DataFrame(
        [
            {
                "scenario": "standard",
                "acceptance_pass": False,
                "acceptance_reason": "Worldview Process Failure (probability_within_band_share)",
                "tractor_threshold": 0.25,
                "sidecar_threshold": 0.20,
                "calm_threshold": 0.10,
            },
            {
                "scenario": "s4_sidecar",
                "acceptance_pass": False,
                "acceptance_reason": "Worldview Process Failure (probability_within_band_share)",
                "tractor_threshold": 0.25,
                "sidecar_threshold": 0.20,
                "calm_threshold": 0.10,
            },
        ]
    )

    selected, failed_closed = _select_candidate(report)

    assert failed_closed is True
    assert selected["scenario"] == "standard"
    assert selected["selection_failed_closed"] is True
