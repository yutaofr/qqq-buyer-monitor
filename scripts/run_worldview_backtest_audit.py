# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.research.worldview_benchmark import build_worldview_benchmark

REGIMES = ("MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY")
CRISIS_WINDOWS: dict[str, tuple[str, str]] = {
    "2018Q4": ("2018-10-01", "2018-12-31"),
    "2020COVID": ("2020-02-15", "2020-04-30"),
    "2022H1": ("2022-01-01", "2022-06-30"),
}


def _load_price_benchmark(price_cache_path: Path) -> pd.DataFrame:
    prices = pd.read_csv(price_cache_path, parse_dates=["Date"])[["Date", "Close", "Volume"]]
    prices["Date"] = pd.to_datetime(prices["Date"], utc=True).dt.tz_convert(None).dt.normalize()
    prices = prices.rename(columns={"Date": "date"}).drop_duplicates("date").sort_values("date")
    benchmark = build_worldview_benchmark(prices.set_index("date"))
    return benchmark.reset_index().rename(columns={"index": "date"})


def _load_mainline(mainline_dir: Path) -> pd.DataFrame:
    trace_path = mainline_dir / "full_audit.csv"
    if not trace_path.exists():
        raise FileNotFoundError(f"Missing mainline audit trace at {trace_path}")
    return pd.read_csv(trace_path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)


def _load_baseline_trace(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    date_col = "Unnamed: 0" if "Unnamed: 0" in frame.columns else "date"
    frame = frame.rename(columns={date_col: "date"})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.sort_values("date").reset_index(drop=True)


def _probability_alignment(merged: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for regime in REGIMES:
        model_prob = pd.to_numeric(merged[f"prob_{regime}"], errors="coerce")
        benchmark_prob = pd.to_numeric(merged[f"benchmark_prob_{regime}"], errors="coerce")
        model_delta = pd.to_numeric(merged[f"prob_delta_{regime}"], errors="coerce").fillna(0.0)
        benchmark_delta = pd.to_numeric(
            merged[f"benchmark_prob_delta_{regime}"], errors="coerce"
        ).fillna(0.0)
        aligned = np.sign(model_delta) == np.sign(benchmark_delta)

        row = {
            "regime": regime,
            "probability_mae": float((model_prob - benchmark_prob).abs().mean()),
            "probability_correlation": float(model_prob.corr(benchmark_prob)),
            "delta_sign_alignment": float(aligned.mean()),
            "model_mean_probability": float(model_prob.mean()),
            "benchmark_mean_probability": float(benchmark_prob.mean()),
        }
        rows.append(row)
        summary[regime] = row
    return pd.DataFrame(rows), summary


def _beta_alignment(merged: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for benchmark_regime, frame in merged.groupby("benchmark_regime"):
        target_beta = pd.to_numeric(frame["target_beta"], errors="coerce")
        benchmark_beta = pd.to_numeric(frame["benchmark_expected_beta"], errors="coerce")
        rows.append(
            {
                "benchmark_regime": str(benchmark_regime),
                "rows": int(len(frame)),
                "mean_target_beta": float(target_beta.mean()),
                "mean_benchmark_beta": float(benchmark_beta.mean()),
                "beta_mae": float((target_beta - benchmark_beta).abs().mean()),
            }
        )
    beta_df = pd.DataFrame(rows).sort_values("benchmark_regime").reset_index(drop=True)
    summary = {
        "overall_beta_mae": float(
            (
                pd.to_numeric(merged["target_beta"], errors="coerce")
                - pd.to_numeric(merged["benchmark_expected_beta"], errors="coerce")
            )
            .abs()
            .mean()
        ),
        "stable_vs_benchmark_regime": float(
            (merged["stable_regime"] == merged["benchmark_regime"]).mean()
        ),
    }
    return beta_df, summary


def _left_tail_audit(merged: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = merged.copy()
    close = pd.to_numeric(frame["close"], errors="coerce")
    frame["qqq_ret_1d"] = close.pct_change().fillna(0.0)
    frame["fwd_20d_drawdown"] = close.shift(-20).rolling(20).min() / close - 1.0
    frame["left_tail_event"] = (frame["qqq_ret_1d"] <= -0.03) | (frame["fwd_20d_drawdown"] <= -0.12)
    frame["tractor_hit"] = pd.to_numeric(frame["tractor_prob"], errors="coerce") >= 0.20
    frame["sidecar_hit"] = frame["sidecar_valid"].fillna(False) & (
        pd.to_numeric(frame["sidecar_prob"], errors="coerce") >= 0.15
    )
    frame["left_tail_cover"] = frame["tractor_hit"] | frame["sidecar_hit"]

    events = frame[frame["left_tail_event"].fillna(False)].copy()
    summary = {
        "event_rows": int(len(events)),
        "covered_share": float(events["left_tail_cover"].mean()) if not events.empty else 0.0,
        "tractor_hit_share": float(events["tractor_hit"].mean()) if not events.empty else 0.0,
        "sidecar_hit_share": float(events["sidecar_hit"].mean()) if not events.empty else 0.0,
    }
    return events, summary


def _transition_audit(merged: pd.DataFrame) -> dict[str, Any]:
    benchmark_prob_cols = [f"benchmark_prob_{regime}" for regime in REGIMES]
    sorted_probs = np.sort(merged[benchmark_prob_cols].to_numpy(), axis=1)
    margin = sorted_probs[:, -1] - sorted_probs[:, -2]
    transition_mask = margin < 0.15
    frame = merged.loc[transition_mask].copy()

    if frame.empty:
        return {"rows": 0, "stable_vs_benchmark_regime": 0.0, "mean_beta_mae": 0.0}

    return {
        "rows": int(len(frame)),
        "stable_vs_benchmark_regime": float(
            (frame["stable_regime"] == frame["benchmark_regime"]).mean()
        ),
        "mean_beta_mae": float(
            (
                pd.to_numeric(frame["target_beta"], errors="coerce")
                - pd.to_numeric(frame["benchmark_expected_beta"], errors="coerce")
            )
            .abs()
            .mean()
        ),
    }


def _window_audit(merged: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window_name, (start, end) in CRISIS_WINDOWS.items():
        frame = merged[
            (merged["date"] >= pd.Timestamp(start)) & (merged["date"] <= pd.Timestamp(end))
        ].copy()
        if frame.empty:
            continue
        left_tail_rows = frame[frame["left_tail_event"].fillna(False)]
        rows.append(
            {
                "window": window_name,
                "rows": int(len(frame)),
                "stable_vs_benchmark_regime": float(
                    (frame["stable_regime"] == frame["benchmark_regime"]).mean()
                ),
                "beta_mae": float(
                    (
                        pd.to_numeric(frame["target_beta"], errors="coerce")
                        - pd.to_numeric(frame["benchmark_expected_beta"], errors="coerce")
                    )
                    .abs()
                    .mean()
                ),
                "tractor_prob_mean": float(
                    pd.to_numeric(frame["tractor_prob"], errors="coerce").mean()
                ),
                "sidecar_prob_mean": float(
                    pd.to_numeric(
                        frame.loc[frame["sidecar_valid"].fillna(False), "sidecar_prob"],
                        errors="coerce",
                    ).mean()
                )
                if frame["sidecar_valid"].fillna(False).any()
                else 0.0,
                "left_tail_cover": float(left_tail_rows["left_tail_cover"].mean())
                if not left_tail_rows.empty
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _write_markdown_report(
    report_path: Path,
    *,
    merged: pd.DataFrame,
    probability_df: pd.DataFrame,
    beta_df: pd.DataFrame,
    left_tail_summary: dict[str, Any],
    transition_summary: dict[str, Any],
    window_df: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    def _markdown_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_No rows_"
        headers = [str(column) for column in df.columns]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join([":---"] * len(headers)) + " |",
        ]
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
        return "\n".join(lines)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# v14 Macro Cycle Worldview Audit",
                "",
                "## Summary",
                "",
                f"- Audit Window: `{merged['date'].min().date()}` to `{merged['date'].max().date()}`",
                f"- Rows: `{len(merged)}`",
                f"- Stable Regime vs Worldview Benchmark: `{summary['beta']['stable_vs_benchmark_regime']:.2%}`",
                f"- Target Beta vs Worldview Benchmark MAE: `{summary['beta']['overall_beta_mae']:.4f}`",
                f"- Left-Tail Event Coverage: `{left_tail_summary['covered_share']:.2%}`",
                f"- Transition-Window Regime Match: `{transition_summary['stable_vs_benchmark_regime']:.2%}`",
                "",
                "## Probability Alignment",
                "",
                _markdown_table(probability_df.round(4)),
                "",
                "## Beta Alignment By Worldview Regime",
                "",
                _markdown_table(beta_df.round(4)),
                "",
                "## Crisis Windows",
                "",
                _markdown_table(window_df.round(4)),
                "",
                "## Left-Tail Audit",
                "",
                f"- Event Rows: `{left_tail_summary['event_rows']}`",
                f"- Tractor Hit Share: `{left_tail_summary['tractor_hit_share']:.2%}`",
                f"- Sidecar Hit Share: `{left_tail_summary['sidecar_hit_share']:.2%}`",
                f"- Combined Coverage: `{left_tail_summary['covered_share']:.2%}`",
                "",
                "## Interpretation",
                "",
                "- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.",
                "- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.",
            ]
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the macro-cycle worldview backtest audit.")
    parser.add_argument("--mainline-artifact-dir", default="artifacts/v14_panorama/mainline")
    parser.add_argument(
        "--baseline-trace-path", default="artifacts/v14_panorama/baseline_oos_trace.csv"
    )
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--output-dir", default="artifacts/v14_worldview_audit")
    parser.add_argument("--report-path", default="docs/research/v14_macro_cycle_worldview_audit.md")
    args = parser.parse_args(argv)

    mainline_dir = Path(args.mainline_artifact_dir)
    baseline_trace_path = Path(args.baseline_trace_path)
    price_cache_path = Path(args.price_cache_path)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    mainline = _load_mainline(mainline_dir)
    benchmark = _load_price_benchmark(price_cache_path)
    baseline_trace = _load_baseline_trace(baseline_trace_path)
    merged = mainline.merge(benchmark, on="date", how="left")
    merged = merged.merge(
        baseline_trace[["date", "tractor_prob", "sidecar_prob", "sidecar_valid"]],
        on="date",
        how="left",
    )

    probability_df, probability_summary = _probability_alignment(merged)
    beta_df, beta_summary = _beta_alignment(merged)
    left_tail_events, left_tail_summary = _left_tail_audit(merged)
    merged = merged.merge(
        left_tail_events[
            [
                "date",
                "qqq_ret_1d",
                "fwd_20d_drawdown",
                "left_tail_event",
                "tractor_hit",
                "sidecar_hit",
                "left_tail_cover",
            ]
        ],
        on="date",
        how="left",
    )
    transition_summary = _transition_audit(merged)
    window_df = _window_audit(merged)

    summary = {
        "probability": probability_summary,
        "beta": beta_summary,
        "left_tail": left_tail_summary,
        "transition": transition_summary,
    }

    merged.to_csv(output_dir / "merged_worldview_trace.csv", index=False)
    probability_df.to_csv(output_dir / "probability_alignment.csv", index=False)
    beta_df.to_csv(output_dir / "beta_alignment_by_regime.csv", index=False)
    left_tail_events.to_csv(output_dir / "left_tail_events.csv", index=False)
    window_df.to_csv(output_dir / "crisis_windows.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown_report(
        report_path,
        merged=merged,
        probability_df=probability_df,
        beta_df=beta_df,
        left_tail_summary=left_tail_summary,
        transition_summary=transition_summary,
        window_df=window_df,
        summary=summary,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
