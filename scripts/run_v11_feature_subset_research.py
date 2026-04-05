"""Run disciplined QQQ-cycle feature subset research for the v11 mainline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.research.v11_feature_subset_research import (
    build_qqq_cycle_candidate_sets,
    build_research_frame,
    flatten_window_report,
    rank_candidate_frame,
    run_cycle_probability_audit,
)
from src.research.v12_diagnostics import build_v12_diagnostic_report


def _slice_window(
    frame: pd.DataFrame,
    *,
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    window = frame[frame["date"] >= pd.Timestamp(start)].copy()
    if end is not None:
        window = window[window["date"] <= pd.Timestamp(end)].copy()
    return window.reset_index(drop=True)


def _markdown_report(
    *,
    selection_winner: dict[str, Any],
    production_recommendation: dict[str, Any],
    ranked: pd.DataFrame,
    leave_one_out: pd.DataFrame,
    output_path: Path,
    selection_start: str,
    selection_end: str,
    holdout_start: str,
) -> None:
    def _frame_to_markdown(frame: pd.DataFrame) -> str:
        headers = [str(column) for column in frame.columns]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in frame.itertuples(index=False, name=None):
            cells = []
            for value in row:
                if isinstance(value, float):
                    cells.append(f"{value:.6f}".rstrip("0").rstrip("."))
                else:
                    cells.append(str(value))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    top_table = ranked.head(10)[
        [
            "name",
            "family",
            "feature_count",
            "selection_composite_rank",
            "selection_top1_accuracy",
            "selection_mean_brier",
            "selection_mean_entropy",
            "selection_mean_true_regime_probability",
            "holdout_top1_accuracy",
            "holdout_mean_brier",
            "holdout_mean_entropy",
            "holdout_mean_true_regime_probability",
        ]
    ].copy()

    lines = [
        "# v11 QQQ Cycle Feature Research",
        "",
        "## Protocol",
        "",
        f"- Selection Window: `{selection_start}` to `{selection_end}`",
        f"- Holdout Window: `{holdout_start}` onward",
        "- Selection objective: higher posterior truth probability, higher accuracy, lower entropy, lower Brier",
        "- Candidate families: baseline, leave-one-out, first-principles core plus optional enhancers",
        "",
        "## Selection Winner",
        "",
        f"- Name: `{selection_winner['name']}`",
        f"- Family: `{selection_winner['family']}`",
        f"- Features ({int(selection_winner['feature_count'])}): `{selection_winner['features']}`",
        f"- Selection accuracy / Brier / entropy: `{selection_winner['selection_top1_accuracy']:.4f} / {selection_winner['selection_mean_brier']:.4f} / {selection_winner['selection_mean_entropy']:.4f}`",
        f"- Selection true-regime prob / rank / L1: `{selection_winner['selection_mean_true_regime_probability']:.4f} / {selection_winner['selection_mean_true_regime_rank']:.4f} / {selection_winner['selection_mean_expected_l1_error']:.4f}`",
        f"- Holdout accuracy / Brier / entropy: `{selection_winner['holdout_top1_accuracy']:.4f} / {selection_winner['holdout_mean_brier']:.4f} / {selection_winner['holdout_mean_entropy']:.4f}`",
        f"- Holdout true-regime prob / rank / L1: `{selection_winner['holdout_mean_true_regime_probability']:.4f} / {selection_winner['holdout_mean_true_regime_rank']:.4f} / {selection_winner['holdout_mean_expected_l1_error']:.4f}`",
        "",
        "## Production Recommendation",
        "",
        "- Rule: holdout accuracy no worse than baseline, holdout Brier no worse than baseline, holdout entropy no worse than baseline, holdout true-regime probability no worse than baseline; among eligible candidates choose the smallest feature set.",
        f"- Name: `{production_recommendation['name']}`",
        f"- Family: `{production_recommendation['family']}`",
        f"- Features ({int(production_recommendation['feature_count'])}): `{production_recommendation['features']}`",
        f"- Selection composite rank: `{production_recommendation['selection_composite_rank']:.4f}`",
        f"- Holdout accuracy / Brier / entropy: `{production_recommendation['holdout_top1_accuracy']:.4f} / {production_recommendation['holdout_mean_brier']:.4f} / {production_recommendation['holdout_mean_entropy']:.4f}`",
        f"- Holdout true-regime prob / rank / L1: `{production_recommendation['holdout_mean_true_regime_probability']:.4f} / {production_recommendation['holdout_mean_true_regime_rank']:.4f} / {production_recommendation['holdout_mean_expected_l1_error']:.4f}`",
        "",
        "## Top 10",
        "",
        _frame_to_markdown(top_table),
    ]

    if not leave_one_out.empty:
        loo_table = leave_one_out[
            [
                "name",
                "selection_top1_accuracy_delta",
                "selection_mean_brier_delta",
                "selection_mean_entropy_delta",
                "selection_mean_true_regime_probability_delta",
                "holdout_top1_accuracy_delta",
                "holdout_mean_brier_delta",
                "holdout_mean_entropy_delta",
            ]
        ].sort_values(
            [
                "selection_mean_true_regime_probability_delta",
                "selection_top1_accuracy_delta",
                "selection_mean_brier_delta",
            ],
            ascending=[False, False, True],
        )
        lines.extend(
            [
                "",
                "## Leave-One-Out Lens",
                "",
                "Positive `selection_mean_true_regime_probability_delta` or `selection_top1_accuracy_delta` means the system improved after dropping that feature.",
                "",
                _frame_to_markdown(loo_table),
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _select_production_candidate(ranked: pd.DataFrame) -> dict[str, Any]:
    baseline = ranked[ranked["family"] == "baseline"]
    if baseline.empty:
        return ranked.iloc[0].to_dict()

    baseline_row = baseline.iloc[0]
    eligible = ranked[
        (ranked["holdout_top1_accuracy"] >= float(baseline_row["holdout_top1_accuracy"]))
        & (ranked["holdout_mean_brier"] <= float(baseline_row["holdout_mean_brier"]))
        & (ranked["holdout_mean_entropy"] <= float(baseline_row["holdout_mean_entropy"]))
        & (
            ranked["holdout_mean_true_regime_probability"]
            >= float(baseline_row["holdout_mean_true_regime_probability"])
        )
    ].copy()
    if eligible.empty:
        return baseline_row.to_dict()
    eligible = eligible.sort_values(
        [
            "feature_count",
            "selection_composite_rank",
            "holdout_mean_brier",
            "holdout_top1_accuracy",
        ],
        ascending=[True, True, True, False],
    )
    return eligible.iloc[0].to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v11 QQQ-cycle feature subset research.")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--evaluation-start", default="2015-01-01")
    parser.add_argument("--selection-start", default="2016-01-01")
    parser.add_argument("--selection-end", default="2017-12-29")
    parser.add_argument("--holdout-start", default="2018-01-01")
    parser.add_argument("--var-smoothing", type=float, default=1e-4)
    parser.add_argument("--output-dir", default="artifacts/v11_feature_subset_research")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open("src/engine/v11/resources/regime_audit.json", encoding="utf-8") as handle:
        audit_contract = json.load(handle)
    feature_order = list(audit_contract["feature_contract"]["feature_names"])
    candidates = build_qqq_cycle_candidate_sets(feature_order)

    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index:03d}/{len(candidates):03d}] {candidate['name']}")
        research_frame, ordered_regimes, _ = build_research_frame(
            dataset_path=args.dataset_path,
            regime_path=args.regime_path,
            feature_names=candidate["features"],
        )
        audit = run_cycle_probability_audit(
            research_frame,
            ordered_regimes=ordered_regimes,
            feature_names=candidate["features"],
            evaluation_start=args.evaluation_start,
            var_smoothing=args.var_smoothing,
        )
        selection_audit = _slice_window(
            audit,
            start=args.selection_start,
            end=args.selection_end,
        )
        holdout_audit = _slice_window(audit, start=args.holdout_start)
        if selection_audit.empty or holdout_audit.empty:
            raise ValueError(f"Empty research window for candidate {candidate['name']}")

        selection_report = build_v12_diagnostic_report(selection_audit)
        holdout_report = build_v12_diagnostic_report(holdout_audit)
        row = {
            "name": candidate["name"],
            "family": candidate["family"],
            "feature_count": candidate["feature_count"],
            "features": ",".join(candidate["features"]),
        }
        row.update(flatten_window_report("selection", selection_report))
        row.update(flatten_window_report("holdout", holdout_report))
        rows.append(row)

    ranked = rank_candidate_frame(pd.DataFrame(rows))
    ranked.to_csv(output_dir / "candidate_scores.csv", index=False)

    baseline_row = ranked[ranked["name"] == f"baseline_{len(feature_order)}"]
    leave_one_out = ranked[ranked["family"] == "leave_one_out"].copy()
    if not baseline_row.empty and not leave_one_out.empty:
        baseline = baseline_row.iloc[0]
        delta_columns = [
            "selection_top1_accuracy",
            "selection_mean_brier",
            "selection_mean_entropy",
            "selection_mean_true_regime_probability",
            "holdout_top1_accuracy",
            "holdout_mean_brier",
            "holdout_mean_entropy",
        ]
        for column in delta_columns:
            leave_one_out[f"{column}_delta"] = leave_one_out[column] - float(baseline[column])
        leave_one_out.to_csv(output_dir / "leave_one_out.csv", index=False)
    else:
        leave_one_out = pd.DataFrame()

    selection_winner = ranked.iloc[0].to_dict()
    production_recommendation = _select_production_candidate(ranked)
    (output_dir / "selection_winner.json").write_text(
        json.dumps(selection_winner, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (output_dir / "production_recommendation.json").write_text(
        json.dumps(production_recommendation, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    _markdown_report(
        selection_winner=selection_winner,
        production_recommendation=production_recommendation,
        ranked=ranked,
        leave_one_out=leave_one_out,
        output_path=output_dir / "report.md",
        selection_start=args.selection_start,
        selection_end=args.selection_end,
        holdout_start=args.holdout_start,
    )

    print("\nSelection Winner")
    print(json.dumps(selection_winner, indent=2, ensure_ascii=True))
    print("\nProduction Recommendation")
    print(json.dumps(production_recommendation, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
