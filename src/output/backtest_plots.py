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
    beta_col = _beta_column(frame)

    fig, ax_price = plt.subplots(1, 1, figsize=(14, 8))
    fig.patch.set_facecolor("#000000")
    ax_price.set_facecolor("#000000")
    ax_price.grid(True, alpha=0.2, linestyle="--")
    ax_price.tick_params(colors="#d8d8d8")
    for spine in ax_price.spines.values():
        spine.set_color("#d8d8d8")

    ax_beta = ax_price.twinx()
    ax_price.plot(
        frame.index,
        frame["close"],
        label="QQQ Close",
        color="#00ff9d",
        linewidth=1.8,
    )
    ax_beta.scatter(
        frame.index,
        frame[beta_col],
        label="Target Beta",
        color="#ff9900",
        s=16,
        alpha=0.9,
        zorder=4,
    )
    ax_price.set_ylabel("QQQ Price ($)", fontsize=12)
    ax_price.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_beta.set_ylabel("Target Beta (x)", fontsize=12)
    ax_beta.set_ylim(0.45, 1.25)
    ax_beta.tick_params(colors="#d8d8d8")
    for spine in ax_beta.spines.values():
        spine.set_color("#d8d8d8")

    price_handles, price_labels = ax_price.get_legend_handles_labels()
    beta_handles, beta_labels = ax_beta.get_legend_handles_labels()
    ax_price.legend(
        price_handles + beta_handles,
        price_labels + beta_labels,
        loc="upper left",
        framealpha=0.9,
        facecolor="#111111",
        edgecolor="#d8d8d8",
        fontsize=9,
    )

    average_signal_beta = float(frame[beta_col].dropna().mean()) if frame[beta_col].notna().any() else 0.0
    title = "v8.1 QQQ Stock-Beta Recommendation vs QQQ Price"
    if summary is not None and hasattr(summary, "signal_beta"):
        average_signal_beta = float(summary.signal_beta)
    title = f"{title}\nAverage Signal Beta: {average_signal_beta:.2f}"
    ax_price.set_title(title, fontsize=14, pad=15)
    ax_price.set_xlabel("Date", fontsize=12)
    ax_beta.yaxis.set_major_locator(mtick.MultipleLocator(0.1))
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
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
