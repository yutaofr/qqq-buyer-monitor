from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from src.research.recovery_hmm.audit import run_shadow_audit  # noqa: E402
from src.research.recovery_hmm.dataset_builder import build_shadow_dataset  # noqa: E402
from src.research.recovery_hmm.reporting import (  # noqa: E402
    build_performance_summary,
    build_review_frame,
    plot_four_panel,
    promotion_decision,
    write_review_markdown,
    write_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 8-year recovery HMM review artifacts.")
    parser.add_argument("--training-end", default="2017-12-31")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--evaluation-end", default="2026-04-07")
    parser.add_argument("--artifact-dir", default="artifacts/recovery_hmm_shadow/review_8yr")
    parser.add_argument("--macro-dump-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--qqq-history-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--production-trace-path", default="artifacts/v14_panorama/mainline/execution_trace.csv")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_shadow_dataset(
        macro_dump_path=args.macro_dump_path,
        qqq_history_path=args.qqq_history_path,
    )
    dataset.frame.to_csv(artifact_dir / "shadow_input_dataset.csv")
    (artifact_dir / "source_lineage.json").write_text(json.dumps(dataset.to_dict(), indent=2), encoding="utf-8")

    audit = run_shadow_audit(
        training_end=args.training_end,
        evaluation_start=args.evaluation_start,
        evaluation_end=args.evaluation_end,
        artifact_dir=artifact_dir,
        raw_frame=dataset.frame,
    )

    review = build_review_frame(
        shadow_trace_path=audit["trace_path"],
        shadow_input_dataset_path=artifact_dir / "shadow_input_dataset.csv",
        qqq_history_path=args.qqq_history_path,
        production_trace_path=args.production_trace_path,
    )
    review_window = review[(review["date"] >= pd.Timestamp(args.evaluation_start)) & (review["date"] <= pd.Timestamp(args.evaluation_end))].copy()
    summary = build_performance_summary(review_window)
    decision, reasons = promotion_decision(summary)
    summary["decision"] = decision
    summary["reasons"] = reasons

    write_summary(artifact_dir / "review_summary.json", summary)
    write_review_markdown(
        artifact_dir / "review.md",
        review_window,
        summary,
        decision=decision,
        reasons=reasons,
        title="Recovery HMM 8-Year Review",
    )
    plot_four_panel(
        review_window,
        artifact_dir / "recovery_hmm_8yr_four_panel.png",
        title_prefix="Recovery HMM",
    )
    print(
        {
            "artifact_dir": str(artifact_dir),
            "decision": decision,
            "review_summary_path": str(artifact_dir / "review_summary.json"),
            "figure_path": str(artifact_dir / "recovery_hmm_8yr_four_panel.png"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
