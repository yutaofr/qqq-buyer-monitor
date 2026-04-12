from __future__ import annotations

import pandas as pd

from src.research.qld_permission_ablation import (
    build_qld_permission_ablation_scenarios,
    build_scenario_record,
    evaluate_no_regression,
    flatten_records_for_csv,
    summarize_execution_window,
)


def test_build_qld_permission_ablation_scenarios_exposes_all_expected_switches():
    scenarios = build_qld_permission_ablation_scenarios(
        baseline_trace_path="artifacts/v14_panorama/baseline_oos_trace.csv"
    )

    assert [scenario["name"] for scenario in scenarios] == [
        "parity_only",
        "bind_resonance_sell",
        "fundamental_override",
        "collinear_suppression",
        "sub1x_guard",
        "all_on",
    ]
    assert scenarios[0]["experiment_config"]["qld_permission_toggles"]["bind_resonance_sell"] is False
    assert scenarios[2]["experiment_config"]["qld_permission_toggles"]["enable_sub1x_guard"] is True
    assert scenarios[-1]["experiment_config"]["qld_permission_toggles"]["enable_sub1x_guard"] is True


def test_summarize_execution_window_reports_qld_days_and_first_entry_date():
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2023-02-01", "2023-02-02", "2023-02-03", "2023-02-06", "2023-07-03"]
            ),
            "target_beta": [0.7, 0.8, 0.95, 1.02, 0.6],
            "raw_target_beta": [0.7, 0.8, 0.95, 1.02, 0.6],
            "overlay_beta": [0.7, 0.8, 0.95, 1.02, 0.6],
            "target_bucket": ["QQQ", "QQQ", "QLD", "QLD", "QQQ"],
        }
    )

    summary = summarize_execution_window(
        frame,
        start="2023-02-01",
        end="2023-06-30",
    )

    assert summary["rows"] == 4
    assert summary["qld_days"] == 2
    assert summary["first_qld_date"] == "2023-02-03"


def test_evaluate_no_regression_marks_candidate_fail_when_process_and_rerisk_degrade():
    execution = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-03-01", "2023-02-03", "2023-02-06"]),
            "target_beta": [0.55, 0.70, 0.75],
            "raw_target_beta": [0.55, 0.70, 0.75],
            "overlay_beta": [0.55, 0.70, 0.75],
            "target_bucket": ["QQQ", "QQQ", "QQQ"],
        }
    )
    baseline = build_scenario_record(
        name="parity_only",
        description="baseline",
        summary={
            "posterior_vs_benchmark_process": 0.70,
            "probability_within_band_share": 0.68,
            "delta_within_band_share": 0.66,
            "acceleration_within_band_share": 0.60,
            "transition_probability_within_band_share": 0.55,
            "entropy_within_band_share": 0.52,
        },
        execution_df=execution,
    )
    degraded = build_scenario_record(
        name="candidate",
        description="candidate",
        summary={
            "posterior_vs_benchmark_process": 0.60,
            "probability_within_band_share": 0.60,
            "delta_within_band_share": 0.58,
            "acceleration_within_band_share": 0.50,
            "transition_probability_within_band_share": 0.45,
            "entropy_within_band_share": 0.40,
        },
        execution_df=execution.assign(target_beta=[0.60, 0.50, 0.50]),
    )

    evaluated = evaluate_no_regression([baseline, degraded])
    candidate = next(record for record in evaluated if record["name"] == "candidate")

    assert candidate["no_regression"]["passed"] is False
    assert candidate["no_regression"]["checks"]["process.posterior_vs_benchmark_process"] is False
    assert candidate["no_regression"]["checks"]["window.2023_rerisk.mean_target_beta"] is False


def test_flatten_records_for_csv_emits_single_row_per_scenario():
    execution = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-03-01", "2023-02-03"]),
            "target_beta": [0.55, 0.75],
            "raw_target_beta": [0.55, 0.75],
            "overlay_beta": [0.55, 0.75],
            "target_bucket": ["QQQ", "QLD"],
        }
    )
    record = build_scenario_record(
        name="parity_only",
        description="baseline",
        summary={
            "posterior_vs_benchmark_process": 0.70,
            "probability_within_band_share": 0.68,
            "delta_within_band_share": 0.66,
            "acceleration_within_band_share": 0.60,
            "transition_probability_within_band_share": 0.55,
            "entropy_within_band_share": 0.52,
        },
        execution_df=execution,
    )
    record["no_regression"] = {"checks": {"baseline_defined": True}, "passed": True}

    frame = flatten_records_for_csv([record])

    assert frame.shape[0] == 1
    assert frame.loc[0, "scenario"] == "parity_only"
    assert "2023_rerisk_qld_days" in frame.columns
