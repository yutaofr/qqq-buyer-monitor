from __future__ import annotations

import pandas as pd
import pytest

from src.engine.panorama_backtest import (
    build_panorama_scenario_frame,
    choose_production_candidate,
    compute_execution_metrics,
    judge_panorama_candidate,
)


def test_build_panorama_scenario_frame_respects_single_and_combined_detectors():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    trace = pd.DataFrame(
        {
            "date": dates,
            "target_beta": [0.90, 0.85, 1.00, 1.10],
            "close": [100.0, 99.0, 98.0, 101.0],
        }
    )
    diagnostics = pd.DataFrame(
        {
            "date": dates,
            "tractor_prob": [0.05, 0.05, 0.35, 0.15],
            "sidecar_prob": [0.04, 0.30, 0.05, 0.12],
            "sidecar_valid": [True, True, True, True],
        }
    )

    scenarios = build_panorama_scenario_frame(trace, diagnostics)

    assert scenarios.loc[dates[0], "standard_beta"] == 0.90
    assert scenarios.loc[dates[0], "s4_sidecar_beta"] == 0.90
    assert scenarios.loc[dates[0], "s5_tractor_beta"] == 0.90
    assert scenarios.loc[dates[0], "panorama_beta"] == 1.25

    assert scenarios.loc[dates[1], "s4_sidecar_beta"] == 0.50
    assert scenarios.loc[dates[1], "s5_tractor_beta"] == 0.85
    assert scenarios.loc[dates[1], "panorama_beta"] == 0.50

    assert scenarios.loc[dates[2], "s4_sidecar_beta"] == 1.00
    assert scenarios.loc[dates[2], "s5_tractor_beta"] == 0.50
    assert scenarios.loc[dates[2], "panorama_beta"] == 0.50

    assert scenarios.loc[dates[3], "panorama_beta"] == 1.10


def test_build_panorama_scenario_frame_ignores_missing_sidecar_signal():
    dates = pd.date_range("2024-02-01", periods=2, freq="B")
    trace = pd.DataFrame(
        {
            "date": dates,
            "target_beta": [0.95, 0.95],
            "close": [100.0, 101.0],
        }
    )
    diagnostics = pd.DataFrame(
        {
            "date": dates,
            "tractor_prob": [0.30, 0.05],
            "sidecar_prob": [float("nan"), float("nan")],
            "sidecar_valid": [False, False],
        }
    )

    scenarios = build_panorama_scenario_frame(trace, diagnostics)

    assert scenarios.loc[dates[0], "s4_sidecar_beta"] == 0.95
    assert scenarios.loc[dates[0], "s5_tractor_beta"] == 0.50
    assert scenarios.loc[dates[0], "panorama_beta"] == 0.50
    assert scenarios.loc[dates[1], "panorama_beta"] == 0.95


def test_judge_panorama_candidate_rejects_more_aggressive_left_tail():
    baseline = {
        "approx_total_return": 0.40,
        "approx_max_drawdown": -0.20,
        "left_tail_mean_beta": 0.70,
        "mean_turnover": 0.03,
    }
    current = {
        "approx_total_return": 0.45,
        "approx_max_drawdown": -0.24,
        "left_tail_mean_beta": 0.76,
        "mean_turnover": 0.03,
    }

    passed, reason = judge_panorama_candidate(current, baseline)

    assert passed is False
    assert "Defensive Violation" in reason


def test_choose_production_candidate_prefers_best_passing_scenario():
    report = pd.DataFrame(
        [
            {
                "scenario": "standard",
                "acceptance_pass": True,
                "approx_total_return": 0.30,
                "approx_max_drawdown": -0.20,
                "left_tail_mean_beta": 0.70,
                "mean_turnover": 0.03,
            },
            {
                "scenario": "s4_sidecar",
                "acceptance_pass": True,
                "approx_total_return": 0.36,
                "approx_max_drawdown": -0.18,
                "left_tail_mean_beta": 0.66,
                "mean_turnover": 0.04,
            },
            {
                "scenario": "s5_tractor",
                "acceptance_pass": False,
                "approx_total_return": 0.44,
                "approx_max_drawdown": -0.28,
                "left_tail_mean_beta": 0.82,
                "mean_turnover": 0.05,
            },
        ]
    )

    winner = choose_production_candidate(report)

    assert winner["scenario"] == "s4_sidecar"


def test_compute_execution_metrics_includes_expectation_fidelity_when_available():
    dates = pd.date_range("2024-03-01", periods=3, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "close": [100.0, 102.0, 101.0],
            "raw_target_beta": [1.1, 0.9, 0.7],
            "standard_beta": [1.0, 0.8, 0.5],
            "expected_target_beta": [1.0, 1.0, 0.5],
        }
    )

    metrics = compute_execution_metrics(frame, "standard_beta")

    assert metrics["mean_raw_beta"] == pytest.approx(0.9)
    assert metrics["mean_standard_beta"] == pytest.approx(0.7666666666666666)
    assert metrics["mean_expected_beta"] == pytest.approx(0.8333333333333334)
    assert metrics["raw_beta_expected_mae"] == pytest.approx(0.13333333333333333)
    assert metrics["standard_beta_expected_mae"] == pytest.approx(0.06666666666666667)
    assert metrics["beta_expectation_mae"] == pytest.approx(0.06666666666666667)
    assert metrics["beta_expectation_rmse"] == pytest.approx(0.11547005383792516)
