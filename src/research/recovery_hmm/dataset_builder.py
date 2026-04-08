"""Historical dataset builder for the recovery HMM shadow research track."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.collector.macro import fetch_historical_fred_series
from src.research.recovery_hmm.data_adapter import RecoveryHmmReadinessReport
from src.research.recovery_hmm.feature_space import REQUIRED_COLUMNS

_FRED_RELEASE_LAG = {
    "T10Y2Y": 1,
    "NFCI": 1,
    "VIXCLS": 1,
    "VXVCLS": 1,
    "NEWORDER": 30,
    "MNFCTRIMSA": 30,
}


def _load_macro_dump(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame = frame.dropna(subset=["observation_date"]).set_index("observation_date").sort_index()
    return frame


def _load_qqq_history(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    date_column = "Date" if "Date" in frame.columns else frame.columns[0]
    close_column = "Close" if "Close" in frame.columns else "close"
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce", utc=True).dt.tz_convert(None)
    frame["observation_date"] = frame[date_column].dt.normalize()
    frame["qqq_close"] = pd.to_numeric(frame[close_column], errors="coerce")
    frame = frame.dropna(subset=["observation_date", "qqq_close"])
    return frame.loc[:, ["observation_date", "qqq_close"]].drop_duplicates("observation_date").set_index(
        "observation_date"
    ).sort_index()


def _business_calendar(*indices: pd.Index) -> pd.DatetimeIndex:
    mins = [pd.Timestamp(idx.min()).normalize() for idx in indices if len(idx) > 0]
    maxs = [pd.Timestamp(idx.max()).normalize() for idx in indices if len(idx) > 0]
    return pd.bdate_range(min(mins), max(maxs))


def _align_series(frame: pd.DataFrame, column: str, calendar: pd.DatetimeIndex, lag_bdays: int) -> pd.Series:
    out = frame.copy()
    out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce").dt.normalize()
    out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["observation_date"]).sort_values("observation_date")
    out["effective_date"] = out["observation_date"] + pd.offsets.BDay(lag_bdays)
    out = out.drop_duplicates(subset=["effective_date"], keep="last").set_index("effective_date")
    return pd.to_numeric(out[column].reindex(calendar, method="ffill"), errors="coerce")


def _orders_inventory_proxy(series: pd.Series) -> pd.Series:
    return series.pct_change(12).mul(100.0)


def _qqq_skew_proxy(qqq_close: pd.Series) -> pd.Series:
    returns = qqq_close.pct_change()
    downside = returns.clip(upper=0.0).abs()
    upside = returns.clip(lower=0.0)
    downside_mean = downside.rolling(20, min_periods=20).mean()
    upside_mean = upside.rolling(20, min_periods=20).mean().replace(0.0, np.nan)
    return (downside_mean / upside_mean).replace([np.inf, -np.inf], np.nan)


def build_shadow_dataset(
    *,
    macro_dump_path: str | Path = "data/macro_historical_dump.csv",
    qqq_history_path: str | Path = "data/qqq_history_cache.csv",
    timeout: int = 15,
) -> RecoveryHmmReadinessReport:
    macro = _load_macro_dump(macro_dump_path)
    qqq = _load_qqq_history(qqq_history_path)

    fred_frames = {
        sid: fetch_historical_fred_series(sid, timeout=timeout)
        for sid in ("T10Y2Y", "NFCI", "VIXCLS", "VXVCLS", "NEWORDER", "MNFCTRIMSA")
    }

    indices = [macro.index, qqq.index]
    indices.extend(
        frame["observation_date"]
        for frame in fred_frames.values()
        if frame is not None and not frame.empty and "observation_date" in frame.columns
    )
    calendar = _business_calendar(*indices)

    frame = pd.DataFrame(index=calendar)
    source_notes: dict[str, str] = {}

    frame["hy_ig_spread"] = pd.to_numeric(macro["credit_spread_bps"], errors="coerce").reindex(calendar) / 100.0
    source_notes["hy_ig_spread"] = "mapped from macro_historical_dump.credit_spread_bps / 100"

    frame["real_yield_10y"] = pd.to_numeric(macro["real_yield_10y_pct"], errors="coerce").reindex(calendar) * 100.0
    source_notes["real_yield_10y"] = "mapped from macro_historical_dump.real_yield_10y_pct * 100"

    if fred_frames["T10Y2Y"] is not None and not fred_frames["T10Y2Y"].empty:
        frame["curve_10y_2y"] = _align_series(fred_frames["T10Y2Y"], "T10Y2Y", calendar, _FRED_RELEASE_LAG["T10Y2Y"])
        source_notes["curve_10y_2y"] = "direct:fred:T10Y2Y"

    if fred_frames["NFCI"] is not None and not fred_frames["NFCI"].empty:
        frame["chicago_fci"] = _align_series(fred_frames["NFCI"], "NFCI", calendar, _FRED_RELEASE_LAG["NFCI"])
        source_notes["chicago_fci"] = "direct:fred:NFCI"

    if fred_frames["VIXCLS"] is not None and fred_frames["VXVCLS"] is not None:
        vix = _align_series(fred_frames["VIXCLS"], "VIXCLS", calendar, _FRED_RELEASE_LAG["VIXCLS"])
        vxv = _align_series(fred_frames["VXVCLS"], "VXVCLS", calendar, _FRED_RELEASE_LAG["VXVCLS"]).replace(0.0, np.nan)
        frame["vix_3m_1m_ratio"] = vxv / vix
        source_notes["vix_3m_1m_ratio"] = "direct:fred:VXVCLS/VIXCLS"

    if fred_frames["NEWORDER"] is not None and not fred_frames["NEWORDER"].empty:
        orders = _align_series(fred_frames["NEWORDER"], "NEWORDER", calendar, _FRED_RELEASE_LAG["NEWORDER"])
        frame["ism_new_orders"] = _orders_inventory_proxy(orders)
        source_notes["ism_new_orders"] = "proxy:fred:NEWORDER 12m pct change"

    if fred_frames["MNFCTRIMSA"] is not None and not fred_frames["MNFCTRIMSA"].empty:
        inventories = _align_series(
            fred_frames["MNFCTRIMSA"],
            "MNFCTRIMSA",
            calendar,
            _FRED_RELEASE_LAG["MNFCTRIMSA"],
        )
        frame["ism_inventories"] = _orders_inventory_proxy(inventories)
        source_notes["ism_inventories"] = "proxy:fred:MNFCTRIMSA 12m pct change"

    qqq_close = pd.to_numeric(qqq["qqq_close"], errors="coerce").reindex(calendar).ffill()
    frame["qqq_skew_20d_mean"] = _qqq_skew_proxy(qqq_close)
    source_notes["qqq_skew_20d_mean"] = "proxy:local_qqq_history downside/upside 20d mean ratio"

    coverage = {
        column: float(frame[column].notna().mean()) if column in frame.columns else 0.0
        for column in sorted(REQUIRED_COLUMNS)
    }
    missing = tuple(sorted(column for column in REQUIRED_COLUMNS if coverage[column] <= 0.0))
    incomplete = tuple(sorted(column for column, ratio in coverage.items() if 0.0 < ratio < 1.0))
    return RecoveryHmmReadinessReport(
        frame=frame,
        coverage=coverage,
        mapped_columns=tuple(sorted(frame.columns)),
        missing_columns=missing,
        incomplete_columns=incomplete,
        source_notes=source_notes,
    )
