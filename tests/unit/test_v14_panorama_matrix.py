from __future__ import annotations

import pandas as pd

from scripts.baseline_backtest import collect_panorama_oos_artifacts
from scripts.run_v14_panorama_matrix import _scenario_report, _select_candidate, _write_report


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


def test_collect_panorama_oos_artifacts_prefers_cached_trace(tmp_path, monkeypatch):
    cache_path = tmp_path / "baseline_oos_trace.csv"
    pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="B"),
            "tractor_prob": [0.1, 0.2, 0.3],
            "sidecar_prob": [0.2, 0.1, 0.4],
            "sidecar_valid": [True, False, True],
        }
    ).to_csv(cache_path, index=False)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("live baseline reload should not be called when cache is preferred")

    monkeypatch.setattr("scripts.baseline_backtest.load_all_baseline_data", _fail_if_called)

    artifacts = collect_panorama_oos_artifacts(
        baseline_trace_path=str(cache_path),
        prefer_cached_artifacts=True,
    )

    assert artifacts["metadata"]["vintage_mode"] == "CACHED_ARTIFACT"
    assert list(artifacts["oos_results"].columns) == [
        "tractor_prob",
        "sidecar_prob",
        "sidecar_valid",
    ]
    assert len(artifacts["oos_results"]) == 3
    assert artifacts["oos_results"].index.min().strftime("%Y-%m-%d") == "2024-01-01"


def test_write_report_calls_out_conditional_process_gate(tmp_path):
    output_path = tmp_path / "report.md"
    report = pd.DataFrame(
        [
            {
                "scenario": "standard",
                "acceptance_pass": False,
                "acceptance_reason": "Worldview Process Failure (entropy_within_band_share)",
                "stable_vs_benchmark_regime": 0.80,
                "probability_within_band_share": 0.56,
                "delta_within_band_share": 0.83,
                "acceleration_within_band_share": 0.85,
                "transition_probability_within_band_share": 0.94,
                "entropy_within_band_share": 0.62,
                "transition_entropy_within_band_share": 0.87,
                "mean_raw_beta": 0.91,
                "mean_standard_beta": 0.88,
                "mean_target_beta": 0.88,
                "mean_expected_beta": 0.90,
                "raw_beta_expected_mae": 0.05,
                "standard_beta_expected_mae": 0.04,
                "beta_expectation_mae": 0.04,
            }
        ]
    )
    _write_report(
        output_path=output_path,
        diagnostics_meta={"vintage_mode": "CACHED_ARTIFACT", "oos_start": "2013-01-30"},
        calibration_report=report,
        default_holdout_report=report,
        tuned_holdout_row=report.iloc[0].to_dict(),
        selected_candidate=report.iloc[0].to_dict(),
        selection_failed_closed=True,
        holdout_start="2018-01-01",
        floor_conflict_stats={"min_beta": 0.5, "mean_beta": 0.8, "share_below_floor": 0.0},
        mainline_summary={
            "evaluation_start_effective": "2013-01-30",
            "top1_accuracy": 0.74,
            "mean_brier": 0.48,
            "mean_entropy": 0.55,
            "stable_vs_benchmark_regime": 0.80,
            "probability_within_band_share": 0.56,
            "delta_within_band_share": 0.83,
            "acceleration_within_band_share": 0.85,
            "transition_probability_within_band_share": 0.94,
            "entropy_within_band_share": 0.62,
            "raw_beta_expectation_mae": 0.05,
            "beta_expectation_mae": 0.04,
            "deployment_exact_match": 0.70,
            "deployment_rank_abs_error_mean": 0.10,
            "deployment_pacing_abs_error_mean": 0.12,
            "deployment_pacing_signed_mean": 0.01,
            "raw_beta_min": 0.5,
            "beta_expectation_min": 0.5,
            "target_beta_min": 0.5,
            "raw_beta_within_5pct_expected": 0.4,
            "target_beta_within_5pct_expected": 0.45,
            "target_floor_breach_rate": 0.0,
            "share_at_floor": 0.1,
        },
    )
    text = output_path.read_text(encoding="utf-8")
    assert "Conditional expected-process gate" in text
    assert "Conditional Process Gate Lens" in text
