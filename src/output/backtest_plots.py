"""Backtest plotting helpers for report generation."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import pandas as pd


def _beta_column(frame: pd.DataFrame) -> str:
    if "target_beta" in frame.columns:
        return "target_beta"
    if "signal_target_beta" in frame.columns:
        return "signal_target_beta"
    raise ValueError("daily_timeseries must contain target_beta or signal_target_beta")


def _raw_beta_series(frame: pd.DataFrame) -> pd.Series:
    if "raw_target_beta" in frame.columns:
        return frame["raw_target_beta"].astype(float)
    beta_col = _beta_column(frame)
    return frame[beta_col].astype(float)


def _advised_beta_series(frame: pd.DataFrame) -> pd.Series:
    if "advised_target_beta" in frame.columns:
        return frame["advised_target_beta"].astype(float)
    beta_col = _beta_column(frame)
    return frame[beta_col].astype(float)


def _coerce_frame(daily_ts: pd.DataFrame) -> pd.DataFrame:
    if daily_ts.empty:
        raise ValueError("daily_timeseries is empty")

    frame = daily_ts.copy()
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[~frame.index.isna()].sort_index()
    if frame.empty:
        raise ValueError("daily_timeseries has no valid timestamps")

    if "close" not in frame.columns:
        raise ValueError("daily_timeseries must contain close")

    return frame


def build_beta_backtest_figure(daily_ts: pd.DataFrame, summary: Any | None = None):
    """Build the stock-beta backtest comparison figure."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    frame = _coerce_frame(daily_ts)
    raw_beta = _raw_beta_series(frame)
    advised_beta = _advised_beta_series(frame)
    beta_series = advised_beta
    change_mask = advised_beta.ne(advised_beta.shift(1))
    beta_plot_mask = change_mask.copy()
    beta_plot_mask.iloc[-1] = True
    raw_plot_frame = raw_beta.loc[beta_plot_mask]
    advised_plot_frame = advised_beta.loc[beta_plot_mask]

    fig, (ax_price, ax_beta) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )
    fig.patch.set_facecolor("#ffffff")
    for axis in (ax_price, ax_beta):
        axis.set_facecolor("#ffffff")
        axis.grid(True, axis="y", color="#d9dee7", linewidth=0.8, alpha=0.85)
        axis.tick_params(colors="#2b3440")
        for spine in axis.spines.values():
            spine.set_color("#c5ccd6")

    ax_price.plot(
        frame.index,
        frame["close"],
        label="QQQ Close",
        color="#0b5fff",
        linewidth=2.2,
    )
    ax_beta.step(
        raw_plot_frame.index,
        raw_plot_frame,
        label="Raw Target Beta",
        color="#8f99ab",
        linewidth=1.4,
        where="post",
        alpha=0.9,
        linestyle="--",
    )
    ax_beta.step(
        advised_plot_frame.index,
        advised_plot_frame,
        label="Advised Target Beta" if "advised_target_beta" in frame.columns else "Target Beta",
        color="#f28c28",
        linewidth=1.8,
        where="post",
        alpha=0.9,
    )
    ax_beta.scatter(
        advised_plot_frame.index,
        advised_plot_frame,
        label="Beta Change Point",
        color="#c96a09",
        s=20,
        zorder=3,
    )

    ax_price.set_ylabel("QQQ Price ($)", fontsize=12, color="#2b3440")
    ax_price.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_price.legend(loc="upper left", frameon=False, fontsize=10)

    beta_min = float(beta_series.min())
    beta_max = float(beta_series.max())
    ax_beta.set_ylabel("Target Beta", fontsize=12, color="#2b3440")
    ax_beta.set_ylim(beta_min - 0.08, beta_max + 0.08)
    ax_beta.yaxis.set_major_locator(mtick.MultipleLocator(0.1))
    ax_beta.legend(loc="upper left", frameon=False, fontsize=10, ncols=2)

    average_signal_beta = float(advised_beta.dropna().mean()) if advised_beta.notna().any() else 0.0
    title = "v8.2 QQQ Stock-Beta Recommendation vs QQQ Price"
    if summary is not None and hasattr(summary, "signal_beta"):
        average_signal_beta = float(summary.signal_beta)
    title = f"{title}\nAverage Signal Beta: {average_signal_beta:.2f}"
    ax_price.set_title(title, fontsize=14, pad=12, color="#18212b")
    ax_beta.set_xlabel("Date", fontsize=12, color="#2b3440")
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    return fig


def save_beta_backtest_figure(
    daily_ts: pd.DataFrame,
    summary: Any | None,
    output_paths: Sequence[str | Path],
) -> list[Path]:
    """Save the beta backtest figure to one or more paths."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    fig = build_beta_backtest_figure(daily_ts, summary=summary)
    saved_paths: list[Path] = []
    try:
        for output_path in output_paths:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
            saved_paths.append(path)
    finally:
        plt.close(fig)
    return saved_paths


def build_deployment_pacing_figure(daily_ts: pd.DataFrame, summary: Any | None = None):
    """Build a continuous deployment-pacing backtest figure."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    frame = _coerce_frame(daily_ts)
    required = {
        "actual_deployment_cash",
        "expected_deployment_cash",
        "deployment_multiplier",
        "expected_deployment_multiplier",
        "deployment_pacing_error",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            "daily_timeseries missing deployment pacing columns: " + ", ".join(sorted(missing))
        )

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(14, 12),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.2, 1.4, 1.4, 1.1], "hspace": 0.08},
    )
    ax_price, ax_pace, ax_cash, ax_error = axes
    fig.patch.set_facecolor("#ffffff")
    for axis in axes:
        axis.set_facecolor("#ffffff")
        axis.grid(True, axis="y", color="#d9dee7", linewidth=0.8, alpha=0.85)
        axis.tick_params(colors="#2b3440")
        for spine in axis.spines.values():
            spine.set_color("#c5ccd6")

    ax_price.plot(frame.index, frame["close"], label="QQQ Close", color="#0b5fff", linewidth=2.0)
    ax_price.set_ylabel("QQQ Price ($)", fontsize=12, color="#2b3440")
    ax_price.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_price.legend(loc="upper left", frameon=False, fontsize=10)

    ax_pace.step(
        frame.index,
        frame["deployment_multiplier"],
        where="post",
        label="Actual Pace",
        color="#f28c28",
        linewidth=1.8,
    )
    ax_pace.step(
        frame.index,
        frame["expected_deployment_multiplier"],
        where="post",
        label="Expected Pace",
        color="#4c7a3f",
        linewidth=1.6,
        linestyle="--",
    )
    ax_pace.set_ylabel("Pacing Multiplier", fontsize=12, color="#2b3440")
    ax_pace.legend(loc="upper left", frameon=False, fontsize=10)

    ax_cash.plot(
        frame.index,
        frame["actual_deployment_cash"],
        label="Actual Deployment Cash",
        color="#ff6b6b",
        linewidth=1.7,
    )
    ax_cash.plot(
        frame.index,
        frame["expected_deployment_cash"],
        label="Expected Deployment Cash",
        color="#2d9cdb",
        linewidth=1.5,
        linestyle="--",
    )
    ax_cash.set_ylabel("Deployment Cash ($)", fontsize=12, color="#2b3440")
    ax_cash.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_cash.legend(loc="upper left", frameon=False, fontsize=10)

    error_series = frame["deployment_pacing_error"].astype(float)
    ax_error.axhline(0.0, color="#8f99ab", linewidth=1.0, linestyle="--")
    ax_error.plot(frame.index, error_series, label="Pacing Error", color="#c0392b", linewidth=1.4)
    ax_error.fill_between(frame.index, 0.0, error_series, color="#f5b7b1", alpha=0.45)
    ax_error.set_ylabel("Pacing Error", fontsize=12, color="#2b3440")
    ax_error.legend(loc="upper left", frameon=False, fontsize=10)

    mae = float(summary.mean_absolute_error) if summary is not None and hasattr(summary, "mean_absolute_error") else float(error_series.abs().mean())
    rmse = float(summary.rmse) if summary is not None and hasattr(summary, "rmse") else float((error_series.pow(2).mean()) ** 0.5)
    variance = float(summary.error_variance) if summary is not None and hasattr(summary, "error_variance") else float(error_series.var(ddof=0))
    within_ratio = (
        float(summary.within_tolerance_ratio)
        if summary is not None and hasattr(summary, "within_tolerance_ratio")
        else float((error_series.abs() <= 0.25).mean())
    )
    ax_price.set_title(
        "v10.0 Deployment Pacing Backtest\n"
        f"MAE: {mae:.3f} | RMSE: {rmse:.3f} | Var: {variance:.4f} | Within Band: {within_ratio:.2%}",
        fontsize=14,
        pad=12,
        color="#18212b",
    )
    ax_error.set_xlabel("Date", fontsize=12, color="#2b3440")
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    return fig


def save_deployment_pacing_figure(
    daily_ts: pd.DataFrame,
    summary: Any | None,
    output_paths: Sequence[str | Path],
) -> list[Path]:
    """Save the deployment pacing figure to one or more paths."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    fig = build_deployment_pacing_figure(daily_ts, summary=summary)
    saved_paths: list[Path] = []
    try:
        for output_path in output_paths:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
            saved_paths.append(path)
    finally:
        plt.close(fig)
    return saved_paths


def build_v11_fidelity_figure(daily_ts: pd.DataFrame, summary: Any | None = None):
    """Build V11 target-beta fidelity figure (Actual vs Expected)."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    frame = _coerce_frame(daily_ts)
    raw_beta = frame["raw_target_beta"].astype(float)
    advised_beta = frame["target_beta"].astype(float)
    expected_beta = frame["expected_target_beta"].astype(float)

    fig, (ax_price, ax_beta) = plt.subplots(
        2,
        1,
        figsize=(14, 10),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.5, 1.5], "hspace": 0.08},
    )
    fig.patch.set_facecolor("#ffffff")
    for axis in (ax_price, ax_beta):
        axis.set_facecolor("#ffffff")
        axis.grid(True, axis="y", color="#d9dee7", linewidth=0.8, alpha=0.85)
        axis.tick_params(colors="#2b3440")
        for spine in axis.spines.values():
            spine.set_color("#c5ccd6")

    ax_price.plot(frame.index, frame["close"], label="QQQ Close", color="#0b5fff", linewidth=2.0)
    ax_price.set_ylabel("QQQ Price ($)", fontsize=12, color="#2b3440")
    ax_price.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_price.legend(loc="upper left", frameon=False, fontsize=10)

    ax_beta.step(frame.index, expected_beta, label="Expected Beta", color="#4c7a3f", linewidth=1.6, linestyle="--", where="post")
    ax_beta.step(frame.index, raw_beta, label="V11 Raw Beta", color="#8f99ab", linewidth=1.2, alpha=0.7, where="post")
    ax_beta.step(frame.index, advised_beta, label="V11 Advised Beta", color="#f28c28", linewidth=2.0, where="post")

    ax_beta.set_ylabel("Target Beta", fontsize=12, color="#2b3440")
    ax_beta.set_ylim(0.4, 1.3)
    ax_beta.yaxis.set_major_locator(mtick.MultipleLocator(0.1))
    ax_beta.legend(loc="upper left", frameon=False, fontsize=10, ncols=3)

    mae = (advised_beta - expected_beta).abs().mean()
    accuracy = summary.get("top1_accuracy", 0.0) if summary else 0.0
    ax_price.set_title(
        f"V11 Bayesian-Core Target Beta Fidelity\nMAE vs Expectations: {mae:.4f} | Regime Accuracy: {accuracy:.2%}",
        fontsize=14, pad=12, color="#18212b"
    )
    ax_beta.set_xlabel("Date", fontsize=12, color="#2b3440")
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    return fig


def save_v11_fidelity_figure(
    daily_ts: pd.DataFrame,
    summary: Any | None,
    output_paths: Sequence[str | Path],
) -> list[Path]:
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    fig = build_v11_fidelity_figure(daily_ts, summary=summary)
    saved_paths: list[Path] = []
    try:
        for output_path in output_paths:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
            saved_paths.append(path)
    finally:
        plt.close(fig)
    return saved_paths


def build_v11_probabilistic_audit_figure(daily_ts: pd.DataFrame, summary: Any | None = None):
    """Build V11 posterior probability distribution and entropy figure."""
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    frame = _coerce_frame(daily_ts)
    regimes = ["MID_CYCLE", "BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE"]
    colors = {"MID_CYCLE": "#3498db", "BUST": "#e74c3c", "CAPITULATION": "#2ecc71", "RECOVERY": "#f1c40f", "LATE_CYCLE": "#9b59b6"}
    
    fig, (ax_prob, ax_entropy) = plt.subplots(
        2, 1, figsize=(14, 10), sharex=True, constrained_layout=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}
    )
    
    bottom = pd.Series(0.0, index=frame.index)
    for r in regimes:
        col = f"prob_{r}"
        if col in frame.columns:
            ax_prob.fill_between(frame.index, bottom, bottom + frame[col], label=r, color=colors.get(r, "#95a5a6"), alpha=0.8)
            bottom += frame[col]
            
    ax_prob.set_ylabel("Posterior Probability", fontsize=12)
    ax_prob.set_ylim(0, 1.0)
    ax_prob.legend(loc="upper left", bbox_to_anchor=(1, 1), frameon=False)
    
    if "entropy" in frame.columns:
        ax_entropy.plot(frame.index, frame["entropy"], color="#34495e", linewidth=1.5, label="Information Entropy")
        ax_entropy.fill_between(frame.index, 0, frame["entropy"], color="#34495e", alpha=0.1)
        ax_entropy.set_ylabel("Entropy", fontsize=12)
        ax_entropy.set_ylim(0, 1.1)
        ax_entropy.legend(loc="upper left", frameon=False)

    ax_prob.set_title("V11 Bayesian Regime Posterior & Information Entropy", fontsize=14, pad=15)
    ax_entropy.set_xlabel("Date", fontsize=12)
    ax_prob.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    return fig


def save_v11_probabilistic_audit_figure(
    daily_ts: pd.DataFrame,
    summary: Any | None,
    output_paths: Sequence[str | Path],
) -> list[Path]:
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    fig = build_v11_probabilistic_audit_figure(daily_ts, summary=summary)
    saved_paths: list[Path] = []
    try:
        for output_path in output_paths:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
            saved_paths.append(path)
    finally:
        plt.close(fig)
    return saved_paths
