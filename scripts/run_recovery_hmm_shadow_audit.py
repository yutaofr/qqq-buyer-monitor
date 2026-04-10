from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.recovery_hmm.audit import run_shadow_audit  # noqa: E402
from src.research.recovery_hmm.comparison import compare_shadow_vs_production  # noqa: E402
from src.research.recovery_hmm.dataset_builder import build_shadow_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the recovery HMM shadow audit.")
    parser.add_argument("--input-csv")
    parser.add_argument("--macro-dump-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--qqq-history-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--training-end", default="2021-12-31")
    parser.add_argument("--evaluation-start", default="2022-01-01")
    parser.add_argument("--evaluation-end", default="2024-12-31")
    parser.add_argument("--artifact-dir", default="artifacts/recovery_hmm_shadow")
    parser.add_argument(
        "--production-trace-path", default="artifacts/v14_panorama/mainline/execution_trace.csv"
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if args.input_csv:
        raw_frame = pd.read_csv(args.input_csv, index_col=0, parse_dates=True)
        lineage = None
    else:
        readiness = build_shadow_dataset(
            macro_dump_path=args.macro_dump_path,
            qqq_history_path=args.qqq_history_path,
        )
        if not readiness.is_ready:
            summary_path = artifact_dir / "readiness_report.json"
            summary_path.write_text(
                json.dumps(readiness.to_dict(), indent=2),
                encoding="utf-8",
            )
            print(
                {
                    "status": "DATA_GAP",
                    "readiness_report": str(summary_path),
                    "missing_columns": list(readiness.missing_columns),
                    "incomplete_columns": list(readiness.incomplete_columns),
                }
            )
            return 2
        raw_frame = readiness.frame
        lineage = readiness.to_dict()
        raw_frame.to_csv(artifact_dir / "shadow_input_dataset.csv")
        (artifact_dir / "source_lineage.json").write_text(
            json.dumps(lineage, indent=2),
            encoding="utf-8",
        )

    summary = run_shadow_audit(
        training_end=args.training_end,
        evaluation_start=args.evaluation_start,
        evaluation_end=args.evaluation_end,
        artifact_dir=artifact_dir,
        raw_frame=raw_frame,
    )
    production_trace = Path(args.production_trace_path)
    if production_trace.exists():
        comparison = compare_shadow_vs_production(
            production_trace_path=production_trace,
            shadow_trace_path=summary["trace_path"],
        )
        (artifact_dir / "comparison.json").write_text(
            json.dumps(comparison, indent=2),
            encoding="utf-8",
        )
        summary["comparison"] = comparison
    if lineage is not None:
        summary["lineage_path"] = str(artifact_dir / "source_lineage.json")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
