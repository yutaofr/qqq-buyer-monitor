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
    beta_series = frame[beta_col]
    change_mask = beta_series.ne(beta_series.shift(1))
    beta_plot_mask = change_mask.copy()
    beta_plot_mask.iloc[-1] = True
    beta_plot_frame = frame.loc[beta_plot_mask, [beta_col]]

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
        beta_plot_frame.index,
        beta_plot_frame[beta_col],
        label="Target Beta",
        color="#f28c28",
        linewidth=1.8,
        where="post",
        alpha=0.9,
    )
    ax_beta.scatter(
        beta_plot_frame.index,
        beta_plot_frame[beta_col],
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

    average_signal_beta = float(frame[beta_col].dropna().mean()) if frame[beta_col].notna().any() else 0.0
    title = "v8.1 QQQ Stock-Beta Recommendation vs QQQ Price"
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
