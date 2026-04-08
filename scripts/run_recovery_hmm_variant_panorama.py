from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.recovery_hmm.audit import run_shadow_audit
from src.research.recovery_hmm.dataset_builder import build_shadow_dataset
from src.research.recovery_hmm.reporting import (
    build_performance_summary,
    build_review_frame,
    build_variant_matrix,
    plot_four_panel,
    plot_variant_navs,
    promotion_decision,
    write_review_markdown,
    write_summary,
)
from src.research.recovery_hmm.variants import LOCKED_CANDIDATE_VARIANT, WORLDVIEW_OPTIMIZATION_VARIANTS


def _nav_series(frame: pd.DataFrame, *, weight_column: str) -> pd.Series:
    review = frame.copy().sort_values("date")
    returns = pd.to_numeric(review["close"], errors="coerce").pct_change().fillna(0.0)
    weights = pd.to_numeric(review[weight_column], errors="coerce").shift(1)
    weights = weights.fillna(pd.to_numeric(review[weight_column], errors="coerce"))
    return (1.0 + (weights * returns)).cumprod()


def _buy_and_hold_nav(frame: pd.DataFrame) -> pd.Series:
    review = frame.copy().sort_values("date")
    returns = pd.to_numeric(review["close"], errors="coerce").pct_change().fillna(0.0)
    return (1.0 + returns).cumprod()


def _write_panorama_report(
    path: Path,
    *,
    locked_reference: dict[str, object],
    matrix: pd.DataFrame,
    conclusion: str,
) -> None:
    lines = [
        "# Recovery HMM Variant Panorama",
        "",
        "## Baseline Reference",
        "",
        f"- locked candidate decision: `{locked_reference['decision']}`",
        f"- locked candidate shadow total return: `{locked_reference['shadow_total_return']:.4f}`",
        f"- locked candidate shadow Sharpe: `{locked_reference['shadow_sharpe']:.4f}`",
        f"- locked candidate 2022 Q1 avg weight: `{locked_reference['q1_2022_avg_weight']:.4f}`",
        f"- locked candidate 2023 Q1 avg weight: `{locked_reference['q1_2023_avg_weight']:.4f}`",
        "",
        "## Variant Ranking",
        "",
    ]
    for row in matrix.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row['rank']}. {row['variant']}",
                "",
                f"- decision: `{row['decision']}`",
                f"- shadow total return: `{row['shadow_total_return']:.4f}`",
                f"- shadow Sharpe: `{row['shadow_sharpe']:.4f}`",
                f"- vs locked candidate total return: `{row['excess_return_vs_locked']:.4f}`",
                f"- vs locked candidate Sharpe: `{row['excess_sharpe_vs_locked']:.4f}`",
                f"- 2022 Q1 avg weight: `{row['q1_2022_avg_weight']:.4f}`",
                f"- 2023 Q1 avg weight: `{row['q1_2023_avg_weight']:.4f}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Conclusion",
            "",
            f"- `{conclusion}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 8-year panorama comparison for recovery HMM optimization variants.")
    parser.add_argument("--training-end", default="2017-12-31")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--evaluation-end", default="2026-04-07")
    parser.add_argument("--artifact-dir", default="artifacts/recovery_hmm_shadow/variant_panorama_8yr")
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

    nav_frame: pd.DataFrame | None = None
    matrix_records: list[dict[str, object]] = []
    locked_reference: dict[str, object] | None = None

    for variant in (LOCKED_CANDIDATE_VARIANT, *WORLDVIEW_OPTIMIZATION_VARIANTS):
        variant_dir = artifact_dir / variant.name
        audit = run_shadow_audit(
            training_end=args.training_end,
            evaluation_start=args.evaluation_start,
            evaluation_end=args.evaluation_end,
            artifact_dir=variant_dir,
            raw_frame=dataset.frame,
            variant=variant,
        )
        review = build_review_frame(
            shadow_trace_path=audit["trace_path"],
            shadow_input_dataset_path=artifact_dir / "shadow_input_dataset.csv",
            qqq_history_path=args.qqq_history_path,
            production_trace_path=args.production_trace_path,
        )
        review_window = review[
            (review["date"] >= pd.Timestamp(args.evaluation_start)) & (review["date"] <= pd.Timestamp(args.evaluation_end))
        ].copy()
        summary = build_performance_summary(review_window)
        decision, reasons = promotion_decision(summary)
        summary["decision"] = decision
        summary["reasons"] = reasons
        summary["variant"] = variant.to_dict()
        write_summary(variant_dir / "review_summary.json", summary)
        write_review_markdown(
            variant_dir / "review.md",
            review_window,
            summary,
            decision=decision,
            reasons=reasons,
            title=f"Recovery HMM 8-Year Review | {variant.name}",
        )
        plot_four_panel(
            review_window,
            variant_dir / "recovery_hmm_8yr_four_panel.png",
            title_prefix=f"Recovery HMM | {variant.name}",
        )

        variant_nav = _nav_series(review_window, weight_column="w_final")
        if nav_frame is None:
            nav_frame = pd.DataFrame({"date": review_window["date"], "qqq": _buy_and_hold_nav(review_window)})
            if "target_beta" in review_window.columns and review_window["target_beta"].notna().any():
                nav_frame["production"] = _nav_series(review_window.rename(columns={"target_beta": "weight_proxy"}), weight_column="weight_proxy")
        nav_frame[variant.name] = variant_nav.values

        record = {
            "variant": variant.name,
            "decision": decision,
            "shadow_total_return": summary["shadow"]["total_return"],
            "shadow_cagr": summary["shadow"]["cagr"],
            "shadow_max_drawdown": summary["shadow"]["max_drawdown"],
            "shadow_sharpe": summary["shadow"]["sharpe"],
            "production_total_return": summary["production"]["total_return"],
            "production_sharpe": summary["production"]["sharpe"],
            "q1_2022_avg_weight": summary["windows"]["q1_2022"]["avg_weight"],
            "q1_2023_avg_weight": summary["windows"]["q1_2023"]["avg_weight"],
        }

        if variant is LOCKED_CANDIDATE_VARIANT:
            locked_reference = record
        else:
            matrix_records.append(record)

    if locked_reference is None or nav_frame is None:
        raise RuntimeError("Failed to build locked reference for panorama run.")

    for record in matrix_records:
        record["excess_return_vs_locked"] = record["shadow_total_return"] - locked_reference["shadow_total_return"]
        record["excess_sharpe_vs_locked"] = record["shadow_sharpe"] - locked_reference["shadow_sharpe"]

    matrix = build_variant_matrix(matrix_records)
    plot_variant_navs(nav_frame, artifact_dir / "variant_nav_8yr.png")
    matrix.to_csv(artifact_dir / "variant_matrix.csv", index=False)
    write_summary(artifact_dir / "variant_matrix.json", {"rows": matrix.to_dict(orient="records")})

    best_row = matrix.iloc[0].to_dict() if not matrix.empty else {}
    conclusion = (
        f"BEST_CANDIDATE_FOR_GATED_LIVE_TRIAL: {best_row['variant']}"
        if best_row and best_row.get("decision") == "ELIGIBLE_FOR_GATED_LIVE_TRIAL"
        else "KEEP_SHADOW_ONLY_AND_CONTINUE_RESEARCH"
    )
    write_summary(
        artifact_dir / "panorama_summary.json",
        {
            "baseline_reference": locked_reference,
            "best_variant": best_row,
            "conclusion": conclusion,
        },
    )
    _write_panorama_report(
        artifact_dir / "variant_report.md",
        locked_reference=locked_reference,
        matrix=matrix,
        conclusion=conclusion,
    )
    print(
        {
            "artifact_dir": str(artifact_dir),
            "baseline_reference": LOCKED_CANDIDATE_VARIANT.name,
            "best_variant": best_row.get("variant") if best_row else None,
            "best_decision": best_row.get("decision") if best_row else None,
            "conclusion": conclusion,
            "matrix_path": str(artifact_dir / "variant_matrix.csv"),
            "report_path": str(artifact_dir / "variant_report.md"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
