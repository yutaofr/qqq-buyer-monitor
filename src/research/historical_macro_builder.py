"""Canonical v7.0 historical macro dataset builder for Class A research inputs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.collector import macro_v3
from src.research.data_contracts import (
    summarize_historical_macro_coverage,
    validate_historical_macro_frame,
)

BUILD_VERSION = "v7.0-class-a-research-r1"
_CORE_SERIES: tuple[str, ...] = macro_v3.RESEARCH_PRIMARY_SERIES


def _asof_align(series_frame: pd.DataFrame, series_id: str, calendar: pd.DatetimeIndex) -> pd.Series:
    frame = series_frame.reset_index(drop=True).loc[:, ["observation_date", series_id]].copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame = frame.dropna(subset=["observation_date"]).sort_values("observation_date")
    frame = frame.drop_duplicates(subset=["observation_date"], keep="last")
    frame = frame.set_index("observation_date")
    aligned = frame[series_id].reindex(calendar, method="ffill")
    return pd.to_numeric(aligned, errors="coerce")


def _pct_change(series: pd.Series, periods: int) -> pd.Series:
    prev = series.shift(periods)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (series - prev) / prev * 100.0
    out = out.where(prev.notna() & (prev != 0), np.nan)
    return out


def _next_business_day(series: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Apply a conservative next-business-day visibility lag."""
    dates = pd.to_datetime(series, errors="coerce")
    return pd.DatetimeIndex(dates + pd.offsets.BDay(1))


def _build_calendar(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    dates: list[pd.Timestamp] = []
    for frame in frames.values():
        if "observation_date" not in frame.columns:
            continue
        parsed = pd.to_datetime(frame["observation_date"], errors="coerce").dropna()
        dates.extend(parsed.tolist())
    if not dates:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(sorted(pd.unique(pd.Index(dates))))


def _build_weekly_liquidity_series(
    walcl_frame: pd.DataFrame,
    wdtgal_frame: pd.DataFrame,
    rrp_frame: pd.DataFrame,
) -> pd.DataFrame:
    walcl_dates = pd.to_datetime(walcl_frame["observation_date"], errors="coerce").dropna()
    weekly = pd.DataFrame(index=pd.DatetimeIndex(walcl_dates))
    weekly["observation_date"] = weekly.index
    weekly["WALCL"] = _asof_align(walcl_frame, "WALCL", pd.DatetimeIndex(walcl_dates))
    weekly["WDTGAL"] = _asof_align(wdtgal_frame, "WDTGAL", pd.DatetimeIndex(walcl_dates))
    weekly["RRPONTSYD"] = _asof_align(rrp_frame, "RRPONTSYD", pd.DatetimeIndex(walcl_dates))
    weekly["net_liquidity_usd_bn"] = (weekly["WALCL"] - weekly["WDTGAL"]) / 1000.0 - weekly["RRPONTSYD"]
    weekly["liquidity_roc_pct_4w"] = _pct_change(weekly["net_liquidity_usd_bn"], 4)
    return weekly


def build_historical_macro_dataset(output_path: str | Path | None = None) -> pd.DataFrame:
    """
    Build the canonical historical macro dataset used by v7.0 research.

    The builder is pure apart from an optional CSV write. Tests may monkeypatch
    the research-series loader to avoid network access.
    """
    frames = macro_v3.fetch_research_historical_primary_series()
    missing_core = [series_id for series_id in _CORE_SERIES if series_id not in frames]
    if missing_core:
        raise ValueError(f"Missing core historical research series: {', '.join(missing_core)}")

    calendar = _build_calendar(frames)
    if calendar.empty:
        raise ValueError("No historical research dates available")

    daily = pd.DataFrame(index=calendar)
    daily["observation_date"] = daily.index
    daily["effective_date"] = _next_business_day(daily.index)

    for series_id in ("BAMLH0A0HYM2", "DFII10", "WALCL", "WDTGAL", "RRPONTSYD", "NFCI"):
        daily[series_id] = _asof_align(frames[series_id], series_id, calendar)

    cpff_frame = frames.get("CPFF")
    if cpff_frame is not None and not cpff_frame.empty:
        daily["CPFF"] = _asof_align(cpff_frame, "CPFF", calendar)
        funding_source = "fred:NFCI+fred:CPFF"
    else:
        daily["CPFF"] = np.nan
        funding_source = "fred:NFCI"

    weekly_liquidity = _build_weekly_liquidity_series(
        frames["WALCL"],
        frames["WDTGAL"],
        frames["RRPONTSYD"],
    )
    daily["credit_spread_bps"] = daily["BAMLH0A0HYM2"] * 100.0
    daily["credit_acceleration_pct_10d"] = _pct_change(daily["credit_spread_bps"], 10)
    daily["real_yield_10y_pct"] = daily["DFII10"]
    daily["net_liquidity_usd_bn"] = _asof_align(
        weekly_liquidity.loc[:, ["observation_date", "net_liquidity_usd_bn"]],
        "net_liquidity_usd_bn",
        calendar,
    )
    daily["liquidity_roc_pct_4w"] = _asof_align(
        weekly_liquidity.loc[:, ["observation_date", "liquidity_roc_pct_4w"]],
        "liquidity_roc_pct_4w",
        calendar,
    )
    daily["funding_stress_flag"] = (
        (daily["NFCI"] > 0)
        | (daily["CPFF"].fillna(0) > 0)
    ).astype(int)

    daily["source_credit_spread"] = "fred:BAMLH0A0HYM2"
    daily["source_real_yield"] = "fred:DFII10"
    daily["source_net_liquidity"] = "derived:WALCL-WDTGAL-RRPONTSYD"
    daily["source_funding_stress"] = funding_source
    daily["build_version"] = BUILD_VERSION

    canonical = daily.loc[:, [
        "observation_date",
        "effective_date",
        "credit_spread_bps",
        "credit_acceleration_pct_10d",
        "real_yield_10y_pct",
        "net_liquidity_usd_bn",
        "liquidity_roc_pct_4w",
        "funding_stress_flag",
        "source_credit_spread",
        "source_real_yield",
        "source_net_liquidity",
        "source_funding_stress",
        "build_version",
    ]].copy()

    validate_historical_macro_frame(canonical)

    if output_path is not None:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canonical.to_csv(out_path, index=False)

    return canonical


def build_and_summarize(output_path: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    df = build_historical_macro_dataset(output_path=output_path)
    return df, summarize_historical_macro_coverage(df)
