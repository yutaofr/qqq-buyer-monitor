"""Performance reporting helpers for recovery HMM shadow audits."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


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
    qqq["date"] = pd.to_datetime(qqq["Date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
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
    review["production_weight_lag"] = pd.to_numeric(review.get("target_beta"), errors="coerce").shift(1)
    review["production_weight_lag"] = review["production_weight_lag"].ffill().bfill().fillna(1.0)
    review["production_ret"] = review["production_weight_lag"] * review["ret"]

    q1_2022 = review[(review["date"] >= "2022-01-01") & (review["date"] <= "2022-03-31")]
    q1_2023 = review[(review["date"] >= "2023-01-01") & (review["date"] <= "2023-02-28")]

    return {
        "shadow": _metric_block(review["shadow_ret"]),
        "qqq": _metric_block(review["qqq_ret"]),
        "production": _metric_block(review["production_ret"]),
        "turnover": {
            "mean_abs_daily_change": float(pd.to_numeric(review["w_final"], errors="coerce").diff().abs().mean())
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


def write_summary(path: str | Path, summary: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
