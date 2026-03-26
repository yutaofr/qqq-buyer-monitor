"""Backtest plotting helpers for report generation."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import pandas as pd

_REGIME_COLORS = {
    "EUPHORIC": "#19d3ff",
    "NEUTRAL": "#8f9aa8",
    "RICH_TIGHTENING": "#ffb000",
    "TRANSITION_STRESS": "#ff7f50",
    "CRISIS": "#ff3366",
}


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
    beta_floor = 0.50
    beta_cap = 1.20

    fig, (ax_price, ax_beta) = plt.subplots(
        2,
        1,
        figsize=(14, 10),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )
    fig.patch.set_facecolor("#000000")
    for axis in (ax_price, ax_beta):
        axis.set_facecolor("#000000")
        axis.grid(True, alpha=0.2, linestyle="--")
        axis.tick_params(colors="#d8d8d8")
        for spine in axis.spines.values():
            spine.set_color("#d8d8d8")

    ax_price_price = ax_price.twinx()
    ax_price.plot(
        frame.index,
        frame["close"],
        label="QQQ Close",
        color="#00ff9d",
        linewidth=1.5,
    )
    ax_price_price.plot(
        frame.index,
        frame[beta_col],
        label="Target Beta",
        color="#ff3366",
        linewidth=1.5,
        drawstyle="steps-post",
    )
    ax_price.set_ylabel("QQQ Price ($)", fontsize=12)
    ax_price.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax_price_price.set_ylabel("Target Beta (x)", fontsize=12)
    ax_price_price.set_ylim(0.45, 1.25)
    ax_price_price.axhline(beta_floor, color="#aaaaaa", linestyle="--", linewidth=1, alpha=0.8)
    ax_price_price.axhline(beta_cap, color="#aaaaaa", linestyle="--", linewidth=1, alpha=0.8)

    if "tier0_regime" in frame.columns:
        for regime, color in _REGIME_COLORS.items():
            subset = frame[frame["tier0_regime"] == regime]
            if subset.empty:
                continue
            ax_price_price.scatter(
                subset.index,
                subset[beta_col],
                s=10,
                color=color,
                alpha=0.85,
                label=regime.replace("_", " "),
                zorder=4,
            )

    price_handles, price_labels = ax_price.get_legend_handles_labels()
    beta_handles, beta_labels = ax_price_price.get_legend_handles_labels()
    ax_price.legend(
        price_handles + beta_handles,
        price_labels + beta_labels,
        loc="upper left",
        framealpha=0.9,
        facecolor="#111111",
        edgecolor="#d8d8d8",
        fontsize=9,
    )

    title = "v8.1 QQQ Beta Recommendation vs QQQ Price"
    if summary is not None:
        title = (
            "v8.1 QQQ Beta Recommendation vs QQQ Price\n"
            f"Signal Beta: {getattr(summary, 'signal_beta', float(frame[beta_col].mean())):.2f} | "
            f"Realized Beta: {getattr(summary, 'realized_beta', 0.0):.2f} | "
            f"Mean Interval Deviation: {getattr(summary, 'mean_interval_beta_deviation', 0.0):.4f}"
        )
    ax_price.set_title(title, fontsize=14, pad=15)

    ax_beta.fill_between(
        frame.index,
        beta_floor,
        beta_cap,
        color="#1f2c3d",
        alpha=0.6,
        label="Allowed Beta Band",
    )
    ax_beta.plot(
        frame.index,
        frame[beta_col],
        color="#ff9900",
        linewidth=1.5,
        drawstyle="steps-post",
        label="Recommended Beta",
    )
    ax_beta.axhline(beta_floor, color="#aaaaaa", linestyle="--", linewidth=1)
    ax_beta.axhline(beta_cap, color="#aaaaaa", linestyle="--", linewidth=1)
    ax_beta.set_ylim(0.45, 1.25)
    ax_beta.set_ylabel("Beta (x)", fontsize=12)
    ax_beta.set_xlabel("Date", fontsize=12)
    ax_beta.yaxis.set_major_locator(mtick.MultipleLocator(0.1))

    if "risk_state" in frame.columns:
        risk_marker_colors = {
            "RISK_ON": "#19d3ff",
            "RISK_NEUTRAL": "#8f9aa8",
            "RISK_REDUCED": "#ffb000",
            "RISK_DEFENSE": "#ff7f50",
            "RISK_EXIT": "#ff3366",
        }
        for risk_state, color in risk_marker_colors.items():
            subset = frame[frame["risk_state"] == risk_state]
            if subset.empty:
                continue
            ax_beta.scatter(
                subset.index,
                subset[beta_col],
                s=12,
                color=color,
                alpha=0.9,
                label=risk_state.replace("_", " "),
                zorder=4,
            )

    beta_handles, beta_labels = ax_beta.get_legend_handles_labels()
    ax_beta.legend(
        beta_handles,
        beta_labels,
        loc="upper right",
        framealpha=0.9,
        facecolor="#111111",
        edgecolor="#d8d8d8",
        fontsize=9,
    )

    ax_beta.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
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
