"""Run controlled QLD permission ablations against the canonical backtest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.backtest import run_v11_audit
from src.research.qld_permission_ablation import (
    build_qld_permission_ablation_scenarios,
    build_scenario_record,
    evaluate_no_regression,
    flatten_records_for_csv,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run QLD permission ablation scenarios.")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--artifact-dir", default="artifacts/qld_permission_ablation")
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--price-end-date", default="2026-03-31")
    parser.add_argument(
        "--baseline-trace-path",
        default="artifacts/v14_panorama/baseline_oos_trace.csv",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Optional scenario name to run. Repeat for multiple scenarios.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scenarios = build_qld_permission_ablation_scenarios(
        baseline_trace_path=args.baseline_trace_path
    )
    if args.scenarios:
        requested = set(args.scenarios)
        scenarios = [scenario for scenario in scenarios if scenario["name"] in requested]
        if not scenarios:
            raise ValueError(f"No known scenarios matched: {sorted(requested)}")
    records: list[dict] = []
    for scenario in scenarios:
        scenario_dir = artifact_dir / scenario["name"]
        summary = run_v11_audit(
            dataset_path=args.dataset_path,
            regime_path=args.regime_path,
            evaluation_start=args.evaluation_start,
            artifact_dir=str(scenario_dir),
            experiment_config={
                **scenario["experiment_config"],
                "price_cache_path": args.price_cache_path,
                "allow_price_download": False,
                "price_end_date": args.price_end_date,
            },
        )
        import pandas as pd
        execution_df = pd.read_csv(scenario_dir / "execution_trace.csv")
        records.append(
            build_scenario_record(
                name=scenario["name"],
                description=scenario["description"],
                summary=summary,
                execution_df=execution_df,
            )
        )

    try:
        evaluated = evaluate_no_regression(records)
    except ValueError:
        evaluated = records

    flatten_records_for_csv(evaluated).to_csv(artifact_dir / "scenario_metrics.csv", index=False)
    (artifact_dir / "summary.json").write_text(
        json.dumps(evaluated, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_lines = ["# QLD Permission Ablation", ""]
    for record in evaluated:
        report_lines.append(f"## {record['name']}")
        report_lines.append(record["description"])
        if "no_regression" in record:
            report_lines.append(
                f"- No regression: `{record['no_regression']['passed']}`"
            )
        report_lines.append(
            f"- 2022 defense mean beta: `{record['windows']['2022_defense']['mean_target_beta']:.3f}`"
        )
        report_lines.append(
            f"- 2023 re-risk mean beta: `{record['windows']['2023_rerisk']['mean_target_beta']:.3f}`"
        )
        report_lines.append(
            f"- 2023 re-risk QLD days: `{record['windows']['2023_rerisk']['qld_days']}`"
        )
        unsupported_windows = [
            name
            for name, window in record["windows"].items()
            if not bool(window.get("supported", True))
        ]
        if unsupported_windows:
            report_lines.append(
                f"- Unsupported windows: `{', '.join(sorted(unsupported_windows))}`"
            )
        report_lines.append("")
    (artifact_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
