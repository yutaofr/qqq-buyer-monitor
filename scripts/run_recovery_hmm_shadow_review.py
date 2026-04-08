from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from src.research.recovery_hmm.audit import run_shadow_audit
from src.research.recovery_hmm.dataset_builder import build_shadow_dataset
from src.research.recovery_hmm.reporting import build_performance_summary, build_review_frame, write_summary


def _decision(summary: dict[str, object]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    shadow = summary["shadow"]
    production = summary["production"]
    q1_2022 = summary["windows"]["q1_2022"]
    q1_2023 = summary["windows"]["q1_2023"]

    if shadow["total_return"] < production["total_return"]:
        reasons.append("Shadow total return is below current production beta replay.")
    if shadow["sharpe"] is not None and production["sharpe"] is not None and shadow["sharpe"] < production["sharpe"]:
        reasons.append("Shadow Sharpe is below current production beta replay.")
    if q1_2022["avg_weight"] is not None and q1_2022["avg_weight"] > 0.65:
        reasons.append("2022 Q1 average weight stayed too high for a defensive live upgrade.")
    if q1_2023["avg_weight"] is not None and q1_2023["avg_weight"] < 0.70:
        reasons.append("2023 Q1 average weight stayed too low for an aggressive recovery release.")

    if reasons:
        return "DO_NOT_LIVE_INTEGRATE_YET", reasons
    return "ELIGIBLE_FOR_GATED_LIVE_TRIAL", ["Review window metrics clear the current promotion bar."]


def _write_review_markdown(path: Path, review_window: pd.DataFrame, summary: dict[str, object], decision: str, reasons: list[str]) -> None:
    start = review_window["date"].min().date().isoformat()
    end = review_window["date"].max().date().isoformat()
    shadow = summary["shadow"]
    qqq = summary["qqq"]
    production = summary["production"]
    q1_2022 = summary["windows"]["q1_2022"]
    q1_2023 = summary["windows"]["q1_2023"]

    lines = [
        "# Recovery HMM 8-Year Review",
        "",
        f"- Window: `{start}` to `{end}`",
        f"- Decision: `{decision}`",
        "",
        "## Performance",
        "",
        f"- Shadow total return: `{shadow['total_return']:.4f}`",
        f"- Shadow CAGR: `{shadow['cagr']:.4f}`",
        f"- Shadow max drawdown: `{shadow['max_drawdown']:.4f}`",
        f"- Shadow Sharpe: `{shadow['sharpe']:.4f}`" if shadow["sharpe"] is not None else "- Shadow Sharpe: `None`",
        f"- QQQ total return: `{qqq['total_return']:.4f}`",
        f"- QQQ CAGR: `{qqq['cagr']:.4f}`",
        f"- QQQ max drawdown: `{qqq['max_drawdown']:.4f}`",
        f"- Production beta replay total return: `{production['total_return']:.4f}`",
        f"- Production beta replay CAGR: `{production['cagr']:.4f}`",
        f"- Production beta replay max drawdown: `{production['max_drawdown']:.4f}`",
        f"- Mean abs daily weight change: `{summary['turnover']['mean_abs_daily_change']:.4f}`",
        "",
        "## Critical Windows",
        "",
        f"- 2022 Q1 weight min/avg/max: `{q1_2022['min_weight']:.4f}` / `{q1_2022['avg_weight']:.4f}` / `{q1_2022['max_weight']:.4f}`",
        f"- 2023 Q1 weight min/avg/max: `{q1_2023['min_weight']:.4f}` / `{q1_2023['avg_weight']:.4f}` / `{q1_2023['max_weight']:.4f}`",
        "",
        "## Promotion Verdict",
        "",
    ]
    lines.extend([f"- {reason}" for reason in reasons])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot_four_panel(review_window: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(18, 24), sharex=True, gridspec_kw={"height_ratios": [1.15, 0.8, 0.9, 1.0]})
    plt.subplots_adjust(hspace=0.22)
    dates = review_window["date"]

    axes[0].stackplot(
        dates,
        review_window["prob_BUST"],
        review_window["prob_LATE_CYCLE"],
        review_window["prob_MID_CYCLE"],
        review_window["prob_RECOVERY"],
        labels=["BUST", "LATE_CYCLE", "MID_CYCLE", "RECOVERY"],
        colors=["#d73027", "#f9c74f", "#2b6cb0", "#2a9d8f"],
        alpha=0.82,
    )
    axes[0].set_ylim(0, 1)
    axes[0].set_title("Panel A: Recovery HMM Regime Probabilities", fontsize=15, fontweight="bold")
    axes[0].legend(loc="upper left", ncol=4, frameon=True)
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)

    axes[1].plot(dates, review_window["entropy"], color="#7b2cbf", linewidth=2.0, label="Entropy")
    axes[1].plot(dates, review_window["m_entropy"], color="#6a994e", linewidth=1.8, linestyle="--", label="Entropy Multiplier")
    axes[1].axhline(0.65, color="#7b2cbf", linestyle=":", alpha=0.4)
    axes[1].set_title("Panel B: Entropy And Mechanical Haircut", fontsize=15, fontweight="bold")
    axes[1].legend(loc="upper right", frameon=True)
    axes[1].grid(linestyle="--", alpha=0.25)

    axes[2].plot(dates, review_window["hy_ig_spread"], color="#e76f51", linewidth=2.0, label="HY-IG Spread")
    axes[2].plot(dates, review_window["chicago_fci"], color="#264653", linewidth=1.8, label="NFCI")
    axes[2].plot(dates, review_window["vix_3m_1m_ratio"], color="#219ebc", linewidth=1.8, label="VIX 3M/1M")
    axes[2].plot(dates, review_window["qqq_skew_20d_mean"], color="#ff006e", linewidth=1.6, label="QQQ Skew Proxy")
    axes[2].set_title("Panel C: Stress And Proxy Driver Surface", fontsize=15, fontweight="bold")
    axes[2].legend(loc="upper left", ncol=4, frameon=True)
    axes[2].grid(linestyle="--", alpha=0.25)

    axes[3].plot(dates, review_window["close"], color="black", linewidth=2.0, label="QQQ Close")
    ax_beta = axes[3].twinx()
    ax_beta.plot(dates, review_window["w_final"], color="#0b5fff", linewidth=1.8, label="Shadow Weight")
    if "target_beta" in review_window.columns and review_window["target_beta"].notna().any():
        ax_beta.plot(dates, review_window["target_beta"], color="#f77f00", linewidth=1.5, linestyle="--", label="Production Target Beta")
    axes[3].set_title("Panel D: QQQ Price Vs Shadow Weight", fontsize=15, fontweight="bold")
    axes[3].grid(linestyle="--", alpha=0.25)
    lines1, labels1 = axes[3].get_legend_handles_labels()
    lines2, labels2 = ax_beta.get_legend_handles_labels()
    ax_beta.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)

    if len(dates) > 500:
        axes[3].xaxis.set_major_locator(mdates.YearLocator())
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        axes[3].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


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
    decision, reasons = _decision(summary)
    summary["decision"] = decision
    summary["reasons"] = reasons

    write_summary(artifact_dir / "review_summary.json", summary)
    _write_review_markdown(artifact_dir / "review.md", review_window, summary, decision, reasons)
    _plot_four_panel(review_window, artifact_dir / "recovery_hmm_8yr_four_panel.png")
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
