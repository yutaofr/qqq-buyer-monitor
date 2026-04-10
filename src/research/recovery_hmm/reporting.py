"""Performance reporting helpers for recovery HMM shadow audits."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg", force=True)
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def build_review_frame(
    *,
    shadow_trace_path: str | Path,
    shadow_input_dataset_path: str | Path,
    qqq_history_path: str | Path,
    production_trace_path: str | Path | None = None,
) -> pd.DataFrame:
    shadow = pd.read_csv(shadow_trace_path, parse_dates=["date"]).sort_values("date")
    inputs = pd.read_csv(shadow_input_dataset_path)
    date_col = inputs.columns[0]
    inputs["date"] = pd.to_datetime(inputs[date_col], errors="coerce")
    inputs = inputs.drop(columns=[date_col]).sort_values("date")

    qqq = pd.read_csv(qqq_history_path)
    qqq["date"] = (
        pd.to_datetime(qqq["Date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    )
    qqq["close"] = pd.to_numeric(qqq["Close"], errors="coerce")
    qqq = qqq.loc[:, ["date", "close"]].dropna().drop_duplicates("date").sort_values("date")

    frame = shadow.merge(inputs, on="date", how="left").merge(qqq, on="date", how="left")
    if production_trace_path is not None and Path(production_trace_path).exists():
        prod = pd.read_csv(production_trace_path, parse_dates=["date"])
        frame = frame.merge(prod.loc[:, ["date", "target_beta"]], on="date", how="left")
    else:
        frame["target_beta"] = np.nan
    return frame.sort_values("date").reset_index(drop=True)


def _metric_block(returns: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    if clean.empty:
        return {"total_return": None, "cagr": None, "max_drawdown": None, "sharpe": None}
    nav = (1.0 + clean).cumprod()
    total_return = float(nav.iloc[-1] - 1.0)
    years = max(len(clean) / 252.0, 1e-9)
    cagr = float(nav.iloc[-1] ** (1.0 / years) - 1.0)
    max_drawdown = float((nav / nav.cummax() - 1.0).min())
    vol = float(clean.std() * np.sqrt(252.0))
    sharpe = float((clean.mean() * 252.0) / vol) if vol > 0 else None
    return {
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def build_performance_summary(frame: pd.DataFrame) -> dict[str, object]:
    review = frame.copy().sort_values("date")
    review["ret"] = pd.to_numeric(review["close"], errors="coerce").pct_change().fillna(0.0)
    review["shadow_weight_lag"] = pd.to_numeric(review["w_final"], errors="coerce").shift(1)
    review["shadow_weight_lag"] = review["shadow_weight_lag"].fillna(review["w_final"])
    review["shadow_ret"] = review["shadow_weight_lag"] * review["ret"]
    review["qqq_ret"] = review["ret"]
    review["production_weight_lag"] = pd.to_numeric(
        review.get("target_beta"), errors="coerce"
    ).shift(1)
    review["production_weight_lag"] = review["production_weight_lag"].ffill().bfill().fillna(1.0)
    review["production_ret"] = review["production_weight_lag"] * review["ret"]

    q1_2022 = review[(review["date"] >= "2022-01-01") & (review["date"] <= "2022-03-31")]
    q1_2023 = review[(review["date"] >= "2023-01-01") & (review["date"] <= "2023-02-28")]

    return {
        "shadow": _metric_block(review["shadow_ret"]),
        "qqq": _metric_block(review["qqq_ret"]),
        "production": _metric_block(review["production_ret"]),
        "turnover": {
            "mean_abs_daily_change": float(
                pd.to_numeric(review["w_final"], errors="coerce").diff().abs().mean()
            )
        },
        "windows": {
            "q1_2022": {
                "min_weight": float(q1_2022["w_final"].min()) if not q1_2022.empty else None,
                "avg_weight": float(q1_2022["w_final"].mean()) if not q1_2022.empty else None,
                "max_weight": float(q1_2022["w_final"].max()) if not q1_2022.empty else None,
            },
            "q1_2023": {
                "min_weight": float(q1_2023["w_final"].min()) if not q1_2023.empty else None,
                "avg_weight": float(q1_2023["w_final"].mean()) if not q1_2023.empty else None,
                "max_weight": float(q1_2023["w_final"].max()) if not q1_2023.empty else None,
            },
        },
    }


def promotion_decision(summary: dict[str, object]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    shadow = summary["shadow"]
    production = summary["production"]
    q1_2022 = summary["windows"]["q1_2022"]
    q1_2023 = summary["windows"]["q1_2023"]

    if shadow["total_return"] < production["total_return"]:
        reasons.append("Shadow total return is below current production beta replay.")
    if (
        shadow["sharpe"] is not None
        and production["sharpe"] is not None
        and shadow["sharpe"] < production["sharpe"]
    ):
        reasons.append("Shadow Sharpe is below current production beta replay.")
    if q1_2022["avg_weight"] is not None and q1_2022["avg_weight"] > 0.65:
        reasons.append("2022 Q1 average weight stayed too high for a defensive live upgrade.")
    if q1_2023["avg_weight"] is not None and q1_2023["avg_weight"] < 0.70:
        reasons.append("2023 Q1 average weight stayed too low for an aggressive recovery release.")

    if reasons:
        return "DO_NOT_LIVE_INTEGRATE_YET", reasons
    return "ELIGIBLE_FOR_GATED_LIVE_TRIAL", [
        "Review window metrics clear the current promotion bar."
    ]


def write_review_markdown(
    path: str | Path,
    review_window: pd.DataFrame,
    summary: dict[str, object],
    *,
    decision: str,
    reasons: list[str],
    title: str = "Recovery HMM 8-Year Review",
) -> None:
    start = review_window["date"].min().date().isoformat()
    end = review_window["date"].max().date().isoformat()
    shadow = summary["shadow"]
    qqq = summary["qqq"]
    production = summary["production"]
    q1_2022 = summary["windows"]["q1_2022"]
    q1_2023 = summary["windows"]["q1_2023"]

    lines = [
        f"# {title}",
        "",
        f"- Window: `{start}` to `{end}`",
        f"- Decision: `{decision}`",
        "",
        "## Performance",
        "",
        f"- Shadow total return: `{shadow['total_return']:.4f}`",
        f"- Shadow CAGR: `{shadow['cagr']:.4f}`",
        f"- Shadow max drawdown: `{shadow['max_drawdown']:.4f}`",
        f"- Shadow Sharpe: `{shadow['sharpe']:.4f}`"
        if shadow["sharpe"] is not None
        else "- Shadow Sharpe: `None`",
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
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_four_panel(
    review_window: pd.DataFrame, output_path: str | Path, *, title_prefix: str
) -> None:
    fig, axes = plt.subplots(
        4, 1, figsize=(18, 24), sharex=True, gridspec_kw={"height_ratios": [1.15, 0.8, 0.9, 1.0]}
    )
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
    axes[0].set_title(
        f"{title_prefix} | Panel A: Regime Probabilities", fontsize=15, fontweight="bold"
    )
    axes[0].legend(loc="upper left", ncol=4, frameon=True)
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)

    axes[1].plot(dates, review_window["entropy"], color="#7b2cbf", linewidth=2.0, label="Entropy")
    if "effective_entropy" in review_window.columns:
        axes[1].plot(
            dates,
            review_window["effective_entropy"],
            color="#4d908e",
            linewidth=1.8,
            linestyle="--",
            label="Effective Entropy",
        )
    axes[1].plot(
        dates,
        review_window["m_entropy"],
        color="#6a994e",
        linewidth=1.8,
        linestyle=":",
        label="Entropy Multiplier",
    )
    axes[1].axhline(0.65, color="#7b2cbf", linestyle=":", alpha=0.25)
    axes[1].set_title(
        f"{title_prefix} | Panel B: Entropy And Mechanical Haircut", fontsize=15, fontweight="bold"
    )
    axes[1].legend(loc="upper right", frameon=True)
    axes[1].grid(linestyle="--", alpha=0.25)

    axes[2].plot(
        dates, review_window["hy_ig_spread"], color="#e76f51", linewidth=2.0, label="HY-IG Spread"
    )
    axes[2].plot(dates, review_window["chicago_fci"], color="#264653", linewidth=1.8, label="NFCI")
    axes[2].plot(
        dates, review_window["vix_3m_1m_ratio"], color="#219ebc", linewidth=1.8, label="VIX 3M/1M"
    )
    axes[2].plot(
        dates,
        review_window["qqq_skew_20d_mean"],
        color="#ff006e",
        linewidth=1.6,
        label="QQQ Skew Proxy",
    )
    axes[2].set_title(
        f"{title_prefix} | Panel C: Stress And Proxy Driver Surface", fontsize=15, fontweight="bold"
    )
    axes[2].legend(loc="upper left", ncol=4, frameon=True)
    axes[2].grid(linestyle="--", alpha=0.25)

    axes[3].plot(dates, review_window["close"], color="black", linewidth=2.0, label="QQQ Close")
    ax_beta = axes[3].twinx()
    ax_beta.plot(
        dates, review_window["w_final"], color="#0b5fff", linewidth=1.8, label="Shadow Weight"
    )
    if "target_beta" in review_window.columns and review_window["target_beta"].notna().any():
        ax_beta.plot(
            dates,
            review_window["target_beta"],
            color="#f77f00",
            linewidth=1.5,
            linestyle="--",
            label="Production Target Beta",
        )
    axes[3].set_title(
        f"{title_prefix} | Panel D: QQQ Price Vs Shadow Weight", fontsize=15, fontweight="bold"
    )
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

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def build_variant_matrix(records: list[dict[str, object]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records).copy()
    frame["decision_priority"] = (
        frame["decision"]
        .map(
            {
                "ELIGIBLE_FOR_GATED_LIVE_TRIAL": 0,
                "DO_NOT_LIVE_INTEGRATE_YET": 1,
            }
        )
        .fillna(9)
    )
    sort_columns = [
        "decision_priority",
        "shadow_total_return",
        "shadow_sharpe",
        "q1_2022_avg_weight",
        "q1_2023_avg_weight",
    ]
    ascending = [True, False, False, True, False]
    frame = frame.sort_values(sort_columns, ascending=ascending, na_position="last").reset_index(
        drop=True
    )
    frame["rank"] = range(1, len(frame) + 1)
    return frame


def plot_variant_navs(nav_frame: pd.DataFrame, output_path: str | Path) -> None:
    if nav_frame.empty:
        return
    fig, ax = plt.subplots(figsize=(18, 8))
    for column in nav_frame.columns:
        if column == "date":
            continue
        ax.plot(nav_frame["date"], nav_frame[column], linewidth=1.8, label=column)
    ax.set_title(
        "Recovery HMM Variant Panorama | 8-Year NAV Comparison", fontsize=16, fontweight="bold"
    )
    ax.grid(linestyle="--", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, frameon=True)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def write_summary(path: str | Path, summary: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
