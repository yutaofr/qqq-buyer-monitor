# ruff: noqa: E402
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.baseline_backtest import collect_panorama_oos_artifacts
from src.backtest import run_v11_audit
from src.engine.panorama_backtest import (
    build_panorama_scenario_frame,
    choose_production_candidate,
    compute_execution_metrics,
    judge_panorama_candidate,
)
from src.research.data_contracts import find_first_supported_evaluation_start

SCENARIOS = {
    "standard": "standard_beta",
    "s4_sidecar": "s4_sidecar_beta",
    "s5_tractor": "s5_tractor_beta",
    "s4s5_panorama": "panorama_beta",
}
TRACTOR_THRESHOLDS = [0.20, 0.25, 0.30]
SIDECAR_THRESHOLDS = [0.15, 0.20, 0.25]
CALM_THRESHOLDS = [0.05, 0.10, 0.15]


def _read_trace(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)


def _read_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_mainline_trace(
    *,
    evaluation_start: str,
    price_end_date: str,
    artifact_dir: Path,
    price_cache_path: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    run_v11_audit(
        evaluation_start=evaluation_start,
        artifact_dir=str(artifact_dir),
        experiment_config={
            "price_cache_path": price_cache_path,
            "allow_price_download": False,
            "price_end_date": price_end_date,
        },
    )
    trace_path = artifact_dir / "regime_process_trace.csv"
    if not trace_path.exists():
        trace_path = artifact_dir / "full_audit.csv"
    return _read_trace(trace_path), _read_summary(artifact_dir / "summary.json")


def _scenario_report(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_metrics = compute_execution_metrics(frame, SCENARIOS["standard"])
    for scenario, beta_col in SCENARIOS.items():
        metrics = compute_execution_metrics(frame, beta_col)
        passed, reason = judge_panorama_candidate(metrics, baseline_metrics)
        rows.append(
            {
                "scenario": scenario,
                **metrics,
                "acceptance_pass": passed,
                "acceptance_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def _select_candidate(calibration_report: pd.DataFrame) -> tuple[dict[str, Any], bool]:
    try:
        return choose_production_candidate(calibration_report), False
    except ValueError:
        baseline_row = calibration_report.loc[calibration_report["scenario"] == "standard"].iloc[0]
        fallback = baseline_row.to_dict()
        fallback["selection_failed_closed"] = True
        return fallback, True


def _evaluate_config(
    trace: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    tractor_threshold: float,
    sidecar_threshold: float,
    calm_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = build_panorama_scenario_frame(
        trace,
        diagnostics,
        tractor_risk_threshold=tractor_threshold,
        sidecar_risk_threshold=sidecar_threshold,
        calm_threshold=calm_threshold,
    )
    report = _scenario_report(frame)
    report["tractor_threshold"] = tractor_threshold
    report["sidecar_threshold"] = sidecar_threshold
    report["calm_threshold"] = calm_threshold
    return frame, report


def _calibration_sweep(
    calibration_trace: pd.DataFrame,
    calibration_diag: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for tractor_threshold, sidecar_threshold, calm_threshold in itertools.product(
        TRACTOR_THRESHOLDS, SIDECAR_THRESHOLDS, CALM_THRESHOLDS
    ):
        _, report = _evaluate_config(
            calibration_trace,
            calibration_diag,
            tractor_threshold=tractor_threshold,
            sidecar_threshold=sidecar_threshold,
            calm_threshold=calm_threshold,
        )
        rows.extend(report.to_dict(orient="records"))
    return pd.DataFrame(rows)


def _write_report(
    *,
    output_path: Path,
    diagnostics_meta: dict[str, Any],
    calibration_report: pd.DataFrame,
    default_holdout_report: pd.DataFrame,
    tuned_holdout_row: dict[str, Any],
    selected_candidate: dict[str, Any],
    selection_failed_closed: bool,
    holdout_start: str,
    floor_conflict_stats: dict[str, Any],
    mainline_summary: dict[str, Any],
) -> None:
    def _markdown_table(df: pd.DataFrame) -> str:
        headers = [str(column) for column in df.columns]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join([":---"] * len(headers)) + " |",
        ]
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
        return "\n".join(lines)

    beta_lens_columns = [
        "scenario",
        "mean_raw_beta",
        "mean_standard_beta",
        "mean_target_beta",
        "mean_expected_beta",
        "raw_beta_expected_mae",
        "standard_beta_expected_mae",
        "beta_expectation_mae",
    ]
    beta_lens = default_holdout_report[
        [c for c in beta_lens_columns if c in default_holdout_report.columns]
    ].copy()
    beta_lens = beta_lens.rename(
        columns={
            "mean_target_beta": "mean_scenario_beta",
            "beta_expectation_mae": "scenario_beta_expected_mae",
        }
    )
    process_columns = [
        "scenario",
        "acceptance_pass",
        "acceptance_reason",
        "stable_vs_benchmark_regime",
        "probability_within_band_share",
        "delta_within_band_share",
        "acceleration_within_band_share",
        "transition_probability_within_band_share",
        "entropy_within_band_share",
        "transition_entropy_within_band_share",
    ]
    process_lens = default_holdout_report[
        [column for column in process_columns if column in default_holdout_report.columns]
    ].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("# v14 Panorama Strategy Matrix\n\n")
        handle.write("## Protocol\n\n")
        handle.write(
            f"- Diagnostics Vintage Mode: `{diagnostics_meta.get('vintage_mode', 'UNKNOWN')}`\n"
        )
        handle.write(f"- Calibration Window: `{diagnostics_meta['oos_start']}` to `2017-12-29`\n")
        handle.write(f"- Holdout Window: `{holdout_start}` onward\n")
        handle.write("- Mainline Trace: `run_v11_audit()` canonical execution trace\n")
        handle.write(
            "- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics\n"
        )
        handle.write(
            "- Acceptance: conditional expected-process gate first, then no worse max drawdown, no worse left-tail beta, bounded turnover drift\n"
        )
        handle.write(
            "- Conditional expected-process gate: probability, delta, acceleration, and entropy are judged against context-aware benchmark bands driven by trend strength, transition intensity, uncertainty, and conflict score.\n\n"
        )

        handle.write("## Default Threshold Holdout\n\n")
        handle.write(_markdown_table(default_holdout_report))
        handle.write("\n\n")

        handle.write("## Mainline Bayesian Audit\n\n")
        handle.write(
            f"- Mainline Audit Window: `{diagnostics_meta['oos_start']}` onward\n"
            f"- Effective Evaluation Start: `{mainline_summary['evaluation_start_effective']}`\n"
            f"- Posterior Top-1 Accuracy: `{mainline_summary['top1_accuracy']:.2%}`\n"
            f"- Posterior Brier: `{mainline_summary['mean_brier']:.4f}`\n"
            f"- Mean Entropy: `{mainline_summary['mean_entropy']:.4f}`\n"
            f"- Stable vs Benchmark Regime: `{mainline_summary['stable_vs_benchmark_regime']:.2%}`\n"
            f"- Probability Within Band: `{mainline_summary['probability_within_band_share']:.2%}`\n"
            f"- Delta Within Band: `{mainline_summary['delta_within_band_share']:.2%}`\n"
            f"- Acceleration Within Band: `{mainline_summary['acceleration_within_band_share']:.2%}`\n"
            f"- Transition Probability Within Band: `{mainline_summary['transition_probability_within_band_share']:.2%}`\n"
            f"- Entropy Within Band: `{mainline_summary.get('entropy_within_band_share', 0.0):.2%}`\n"
            f"- Raw Beta vs Expectation MAE: `{mainline_summary['raw_beta_expectation_mae']:.4f}`\n"
            f"- Target Beta vs Expectation MAE: `{mainline_summary['beta_expectation_mae']:.4f}`\n"
            f"- Deployment Exact Match: `{mainline_summary['deployment_exact_match']:.2%}`\n"
            f"- Deployment Rank Error: `{mainline_summary['deployment_rank_abs_error_mean']:.4f}`\n"
            f"- Deployment Pacing Abs Error: `{mainline_summary['deployment_pacing_abs_error_mean']:.4f}`\n"
            f"- Deployment Pacing Signed Bias: `{mainline_summary['deployment_pacing_signed_mean']:.4f}`\n"
            f"- Raw Beta Min: `{mainline_summary['raw_beta_min']:.4f}`\n"
            f"- Beta Expectation Min: `{mainline_summary['beta_expectation_min']:.4f}`\n"
            f"- Target Beta Min: `{mainline_summary['target_beta_min']:.4f}`\n"
            f"- Raw Beta Within 5pct Of Expected: `{mainline_summary['raw_beta_within_5pct_expected']:.2%}`\n"
            f"- Target Beta Within 5pct Of Expected: `{mainline_summary['target_beta_within_5pct_expected']:.2%}`\n"
            f"- Target Floor Breach Rate: `{mainline_summary['target_floor_breach_rate']:.2%}`\n"
            f"- Share At Floor: `{mainline_summary['share_at_floor']:.2%}`\n\n"
        )

        handle.write("## Beta Fidelity Lens\n\n")
        handle.write(
            "- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.\n"
        )
        handle.write(
            "- `mean_standard_beta`: mainline production target beta after the full execution stack.\n"
        )
        handle.write(
            "- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.\n"
        )
        handle.write(
            "- `mean_expected_beta`: regime-policy beta implied by the realized regime label.\n\n"
        )
        handle.write(_markdown_table(beta_lens))
        handle.write("\n\n")

        handle.write("## Conditional Process Gate Lens\n\n")
        handle.write(_markdown_table(process_lens))
        handle.write("\n\n")

        handle.write("## Calibration Winner\n\n")
        if selection_failed_closed:
            handle.write("- No scenario cleared the acceptance contract in calibration.\n")
            handle.write(
                "- Report is fail-closed; `standard` is shown below only as the baseline reference.\n\n"
            )
        else:
            handle.write(
                f"- Scenario: `{selected_candidate['scenario']}`\n"
                f"- Tractor Threshold: `{selected_candidate['tractor_threshold']:.2f}`\n"
                f"- Sidecar Threshold: `{selected_candidate['sidecar_threshold']:.2f}`\n"
                f"- Calm Threshold: `{selected_candidate['calm_threshold']:.2f}`\n"
                f"- Calibration Return: `{selected_candidate['approx_total_return']:.4f}`\n"
                f"- Calibration Max Drawdown: `{selected_candidate['approx_max_drawdown']:.4f}`\n"
                f"- Calibration Left-Tail Beta: `{selected_candidate['left_tail_mean_beta']:.4f}`\n\n"
            )

        handle.write("## Holdout Result Of Frozen Winner\n\n")
        handle.write(_markdown_table(pd.DataFrame([tuned_holdout_row])))
        handle.write("\n")

        handle.write("\n## Production Recommendation\n\n")
        if selection_failed_closed:
            handle.write(
                "- Fail closed: no scenario, including `standard`, cleared the regime-process acceptance gate.\n"
            )
            handle.write(
                "- Keep all panorama variants in diagnostic mode until the mainline process metrics themselves are repaired.\n"
            )
        elif bool(tuned_holdout_row.get("acceptance_pass")):
            handle.write(
                f"- Promote `{tuned_holdout_row['scenario']}` with thresholds "
                f"`tractor={tuned_holdout_row['tractor_threshold']:.2f}`, "
                f"`sidecar={tuned_holdout_row['sidecar_threshold']:.2f}`, "
                f"`calm={tuned_holdout_row['calm_threshold']:.2f}`.\n"
            )
        else:
            handle.write("- Keep `standard` as the production champion.\n")
            handle.write(
                "- Keep `s4_sidecar`, `s5_tractor`, and `s4s5_panorama` in shadow/diagnostic mode only.\n"
            )

        handle.write(
            f"- Structural note: the mainline holdout trace now stays above the `0.5x` floor "
            f"(min `{floor_conflict_stats['min_beta']:.4f}`, mean `{floor_conflict_stats['mean_beta']:.4f}`, "
            f"below-floor share `{floor_conflict_stats['share_below_floor']:.2%}`).\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v14 panorama scenario matrix.")
    parser.add_argument("--holdout-start", default="2018-01-01")
    parser.add_argument("--output-dir", default="artifacts/v14_panorama")
    parser.add_argument("--report-path", default="docs/research/v14_panorama_strategy_matrix.md")
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    args = parser.parse_args(argv)

    artifacts = collect_panorama_oos_artifacts(prefer_cached_artifacts=True)
    diagnostics = artifacts["oos_results"].reset_index().rename(columns={"index": "date"})
    price_end_date = pd.Timestamp(diagnostics["date"].max()).date().isoformat()
    regime_df = pd.read_csv(args.regime_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )
    mainline_start = find_first_supported_evaluation_start(
        regime_df,
        audit_regimes=("MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"),
        training_lookback_bdays=20,
    )
    if mainline_start is None:
        raise ValueError(
            f"Full-support boundary not found in {args.regime_path}; cannot tighten evaluation_start."
        )
    mainline_evaluation_start = max(
        pd.Timestamp(artifacts["oos_start"]), pd.Timestamp(mainline_start)
    )

    output_dir = Path(args.output_dir)
    mainline_trace, mainline_summary = _run_mainline_trace(
        evaluation_start=mainline_evaluation_start.date().isoformat(),
        price_end_date=price_end_date,
        artifact_dir=output_dir / "mainline",
        price_cache_path=args.price_cache_path,
    )

    calibration_trace = mainline_trace[mainline_trace["date"] < pd.Timestamp(args.holdout_start)]
    holdout_trace = mainline_trace[mainline_trace["date"] >= pd.Timestamp(args.holdout_start)]
    calibration_diag = diagnostics[diagnostics["date"] < pd.Timestamp(args.holdout_start)]
    holdout_diag = diagnostics[diagnostics["date"] >= pd.Timestamp(args.holdout_start)]

    _, default_holdout_report = _evaluate_config(
        holdout_trace,
        holdout_diag,
        tractor_threshold=0.25,
        sidecar_threshold=0.20,
        calm_threshold=0.10,
    )

    calibration_report = _calibration_sweep(calibration_trace, calibration_diag)
    selected_candidate, selection_failed_closed = _select_candidate(calibration_report)

    _, tuned_holdout_report = _evaluate_config(
        holdout_trace,
        holdout_diag,
        tractor_threshold=float(selected_candidate["tractor_threshold"]),
        sidecar_threshold=float(selected_candidate["sidecar_threshold"]),
        calm_threshold=float(selected_candidate["calm_threshold"]),
    )
    tuned_holdout_row = (
        tuned_holdout_report.loc[tuned_holdout_report["scenario"] == selected_candidate["scenario"]]
        .iloc[0]
        .to_dict()
    )
    tuned_holdout_row["selection_failed_closed"] = selection_failed_closed
    selected_candidate["selection_failed_closed"] = selection_failed_closed

    output_dir.mkdir(parents=True, exist_ok=True)
    default_holdout_report.to_csv(output_dir / "default_holdout_report.csv", index=False)
    calibration_report.to_csv(output_dir / "calibration_report.csv", index=False)
    pd.DataFrame([selected_candidate]).to_csv(output_dir / "selected_candidate.csv", index=False)
    pd.DataFrame([tuned_holdout_row]).to_csv(output_dir / "tuned_holdout_report.csv", index=False)
    (output_dir / "selected_candidate.json").write_text(
        json.dumps(selected_candidate, indent=2),
        encoding="utf-8",
    )

    _write_report(
        output_path=Path(args.report_path),
        diagnostics_meta={
            "vintage_mode": artifacts["metadata"].get("vintage_mode", "UNKNOWN"),
            "oos_start": artifacts["oos_start"],
        },
        calibration_report=calibration_report,
        default_holdout_report=default_holdout_report,
        tuned_holdout_row=tuned_holdout_row,
        selected_candidate=selected_candidate,
        selection_failed_closed=selection_failed_closed,
        holdout_start=args.holdout_start,
        floor_conflict_stats={
            "min_beta": float(holdout_trace["target_beta"].min()),
            "mean_beta": float(holdout_trace["target_beta"].mean()),
            "share_below_floor": float((holdout_trace["target_beta"] < 0.5).mean()),
        },
        mainline_summary=mainline_summary,
    )

    print("Default holdout report:")
    print(default_holdout_report.to_string(index=False))
    print("\nSelected candidate:")
    print(pd.DataFrame([selected_candidate]).to_string(index=False))
    print("\nFrozen winner holdout result:")
    print(pd.DataFrame([tuned_holdout_row]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
