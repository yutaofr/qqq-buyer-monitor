from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.research.stabilizer_release_forensics import (  # noqa: E402
    build_release_failure_frame,
    load_forensic_trace,
    render_release_failure_report,
    summarize_release_failures,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze delayed RECOVERY stable-state releases.")
    parser.add_argument(
        "--merged-trace-path",
        default="artifacts/regime_process_panorama_rebench/mainline_merged.csv",
    )
    parser.add_argument(
        "--forensic-trace-path",
        default="artifacts/regime_process_mainline_8yr/forensic_trace.jsonl",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/stabilizer_release_forensics/mainline_2023_recovery",
    )
    parser.add_argument("--window-start", default="2023-01-01")
    parser.add_argument("--window-end", default="2023-06-30")
    args = parser.parse_args()

    merged = pd.read_csv(args.merged_trace_path, parse_dates=["date"])
    forensic = load_forensic_trace(args.forensic_trace_path)
    failures = build_release_failure_frame(merged, forensic)

    window_start = pd.Timestamp(args.window_start)
    window_end = pd.Timestamp(args.window_end)
    failures = failures[
        (failures["date"] >= window_start) & (failures["date"] <= window_end)
    ].copy()
    summary = summarize_release_failures(failures)

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    failures.to_csv(artifact_dir / "failure_rows.csv", index=False)
    (artifact_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = render_release_failure_report(summary, failures)
    (artifact_dir / "report.md").write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "artifact_dir": str(artifact_dir.resolve()),
                "summary_path": str((artifact_dir / "summary.json").resolve()),
                "report_path": str((artifact_dir / "report.md").resolve()),
                "failure_rows": summary["failure_rows"],
            }
        )
    )


if __name__ == "__main__":
    main()
