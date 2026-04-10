from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REGIMES = ("RECOVERY", "MID_CYCLE", "LATE_CYCLE", "BUST")
REGIME_COLORS = {
    "RECOVERY": "#2f7d32",
    "MID_CYCLE": "#1565c0",
    "LATE_CYCLE": "#ef6c00",
    "BUST": "#c62828",
}


def _load_mainline(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    return frame


def _load_process_trace(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    return frame


def _load_baseline(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    date_col = "Unnamed: 0" if "Unnamed: 0" in frame.columns else "date"
    frame = frame.rename(columns={date_col: "date"})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _merge_inputs(mainline: pd.DataFrame, process_trace: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    frame = process_trace.merge(
        baseline[["date", "tractor_prob", "sidecar_prob", "sidecar_valid"]],
        on="date",
        how="left",
    )
    if "close" not in frame.columns and "close" in mainline.columns:
        frame = frame.merge(mainline[["date", "close"]], on="date", how="left")
    frame["tractor_prob"] = pd.to_numeric(frame["tractor_prob"], errors="coerce").fillna(0.0)
    frame["sidecar_prob"] = pd.to_numeric(frame["sidecar_prob"], errors="coerce").fillna(0.0)
    frame["target_beta"] = pd.to_numeric(frame["target_beta"], errors="coerce")
    frame["benchmark_expected_beta"] = pd.to_numeric(
        frame["benchmark_expected_beta"], errors="coerce"
    )
    frame["entropy"] = pd.to_numeric(frame["entropy"], errors="coerce")
    frame["benchmark_entropy"] = pd.to_numeric(frame["benchmark_entropy"], errors="coerce")
    frame["benchmark_entropy_lower"] = pd.to_numeric(
        frame["benchmark_entropy_lower"], errors="coerce"
    )
    frame["benchmark_entropy_upper"] = pd.to_numeric(
        frame["benchmark_entropy_upper"], errors="coerce"
    )
    frame["benchmark_transition_intensity"] = pd.to_numeric(
        frame["benchmark_transition_intensity"], errors="coerce"
    ).fillna(0.0)
    return frame


def _plot_panorama(frame: pd.DataFrame, output_path: Path, *, title: str) -> None:
    fig, axes = plt.subplots(5, 1, figsize=(18, 24), sharex=True)

    prob_series = [pd.to_numeric(frame[f"prob_{regime}"], errors="coerce").fillna(0.0) for regime in REGIMES]
    axes[0].stackplot(
        frame["date"],
        *prob_series,
        labels=list(REGIMES),
        colors=[REGIME_COLORS[regime] for regime in REGIMES],
        alpha=0.78,
    )
    axes[0].set_title(f"{title}: Regime Probability Surface")
    axes[0].set_ylim(0.0, 1.0)
    axes[0].legend(loc="upper left", ncol=4)
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(frame["date"], frame["entropy"], label="Posterior entropy", color="#5e35b1")
    axes[1].plot(
        frame["date"],
        frame["benchmark_entropy"],
        label="Benchmark entropy",
        color="#6d4c41",
        linewidth=1.2,
    )
    axes[1].fill_between(
        frame["date"],
        frame["benchmark_entropy_lower"],
        frame["benchmark_entropy_upper"],
        color="#bcaaa4",
        alpha=0.25,
        label="Conditional entropy band",
    )
    axes[1].set_title(f"{title}: Entropy vs Conditional Benchmark")
    axes[1].legend(loc="upper left")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(frame["date"], frame["target_beta"], label="Target beta", color="#1b5e20")
    axes[2].plot(
        frame["date"],
        frame["benchmark_expected_beta"],
        label="Benchmark expected beta",
        color="#004d40",
        linewidth=1.2,
    )
    axes[2].plot(frame["date"], frame["tractor_prob"], label="Tractor prob", color="#fb8c00")
    axes[2].plot(frame["date"], frame["sidecar_prob"], label="QQQ sidecar prob", color="#00838f")
    axes[2].set_title(f"{title}: Beta and Left-Tail Defenses")
    axes[2].legend(loc="upper left", ncol=2)
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(
        frame["date"],
        frame["benchmark_transition_intensity"],
        label="Benchmark transition intensity",
        color="#d81b60",
    )
    axes[3].plot(
        frame["date"],
        pd.to_numeric(frame["benchmark_conflict_score"], errors="coerce"),
        label="Benchmark conflict score",
        color="#6a1b9a",
    )
    axes[3].plot(
        frame["date"],
        pd.to_numeric(frame["benchmark_trend_strength"], errors="coerce"),
        label="Benchmark trend strength",
        color="#3949ab",
    )
    axes[3].set_title(f"{title}: Conditional Process Context")
    axes[3].legend(loc="upper left", ncol=3)
    axes[3].grid(True, alpha=0.25)

    axes[4].plot(frame["date"], pd.to_numeric(frame["close"], errors="coerce"), color="#212121")
    axes[4].set_title(f"{title}: QQQ Price")
    axes[4].grid(True, alpha=0.25)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render v14 panorama audit charts.")
    parser.add_argument("--mainline-trace-path", default="artifacts/v14_panorama/mainline/full_audit.csv")
    parser.add_argument(
        "--process-trace-path", default="artifacts/v14_panorama/mainline/regime_process_trace.csv"
    )
    parser.add_argument("--baseline-trace-path", default="artifacts/v14_panorama/baseline_oos_trace.csv")
    parser.add_argument("--output-dir", default="artifacts/v14_panorama/analysis")
    parser.add_argument("--recent-days", type=int, default=252)
    args = parser.parse_args(argv)

    mainline = _load_mainline(Path(args.mainline_trace_path))
    process_trace = _load_process_trace(Path(args.process_trace_path))
    baseline = _load_baseline(Path(args.baseline_trace_path))
    frame = _merge_inputs(mainline, process_trace, baseline)

    output_dir = Path(args.output_dir)
    _plot_panorama(frame, output_dir / "panorama_full_period.png", title="Full Period")
    recent = frame.tail(args.recent_days).reset_index(drop=True)
    _plot_panorama(recent, output_dir / "panorama_recent_period.png", title="Recent Window")
    print(
        {
            "full_chart": str(output_dir / "panorama_full_period.png"),
            "recent_chart": str(output_dir / "panorama_recent_period.png"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
