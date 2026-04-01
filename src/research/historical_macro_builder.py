"""Canonical v12 historical macro dataset builder."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.collector import global_macro, macro_v3
from src.research.data_contracts import (
    summarize_historical_macro_coverage,
    validate_historical_macro_frame,
)

BUILD_VERSION = "v12.0-orthogonal-factor-r1"
_LIQUIDITY_SERIES: tuple[str, ...] = ("WALCL", "WDTGAL", "RRPONTSYD")


def _asof_align_from_date_column(
    series_frame: pd.DataFrame,
    date_column: str,
    value_column: str,
    calendar: pd.DatetimeIndex,
) -> pd.Series:
    if series_frame is None or series_frame.empty:
        return pd.Series(index=calendar, dtype=float)

    frame = series_frame.copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna(subset=[date_column]).sort_values(date_column)
    frame = frame.drop_duplicates(subset=[date_column], keep="last").set_index(date_column)
    return pd.to_numeric(frame[value_column].reindex(calendar, method="ffill"), errors="coerce")


def _next_business_day(series: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(series, errors="coerce") + pd.offsets.BDay(1))


def _build_business_calendar(*frames: pd.DataFrame) -> pd.DatetimeIndex:
    points: list[pd.Timestamp] = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        for column in ("observation_date", "effective_date"):
            if column in frame.columns:
                parsed = pd.to_datetime(frame[column], errors="coerce").dropna()
                points.extend(parsed.tolist())

    if not points:
        return pd.DatetimeIndex([])

    start = min(points)
    end = max(points)
    return pd.bdate_range(start.normalize(), end.normalize())


def _prepare_credit_spread_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["observation_date", "effective_date", "credit_spread_bps"])

    out = frame.copy()
    if "BAMLH0A0HYM2" in out.columns:
        out["credit_spread_bps"] = pd.to_numeric(out["BAMLH0A0HYM2"], errors="coerce") * 100.0
    out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce").dt.normalize()
    out["effective_date"] = _next_business_day(out["observation_date"])
    return out.loc[:, ["observation_date", "effective_date", "credit_spread_bps"]]


def _prepare_real_yield_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["observation_date", "effective_date", "real_yield_10y_pct"])

    out = frame.copy()
    if "DFII10" in out.columns:
        out["real_yield_10y_pct"] = pd.to_numeric(out["DFII10"], errors="coerce") / 100.0
    out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce").dt.normalize()
    out["effective_date"] = _next_business_day(out["observation_date"])
    return out.loc[:, ["observation_date", "effective_date", "real_yield_10y_pct"]]


def _build_weekly_liquidity_frame(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    missing = [series for series in _LIQUIDITY_SERIES if series not in frames]
    if missing:
        raise ValueError(f"Missing weekly liquidity series: {', '.join(missing)}")

    walcl = frames["WALCL"].copy()
    walcl["observation_date"] = pd.to_datetime(walcl["observation_date"], errors="coerce").dt.normalize()
    weekly_dates = walcl["observation_date"].dropna().drop_duplicates().sort_values()
    weekly = pd.DataFrame(index=pd.DatetimeIndex(weekly_dates))
    weekly["observation_date"] = weekly.index

    for series_id in _LIQUIDITY_SERIES:
        weekly[series_id] = _asof_align_from_date_column(frames[series_id], "observation_date", series_id, weekly.index)

    weekly["net_liquidity_usd_bn"] = (weekly["WALCL"] - weekly["WDTGAL"]) / 1000.0 - weekly["RRPONTSYD"]
    weekly["effective_date"] = _next_business_day(weekly["observation_date"])
    return weekly.reset_index(drop=True).loc[:, ["observation_date", "effective_date", "net_liquidity_usd_bn"]]


def _harmonize_v12_bundle(bundle: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "credit_spread": _prepare_credit_spread_frame(bundle.get("credit_spread")),
        "real_yield": _prepare_real_yield_frame(bundle.get("real_yield")),
        "treasury_vol": bundle.get("treasury_vol", pd.DataFrame()),
        "breakeven": bundle.get("breakeven", pd.DataFrame()),
        "capex": bundle.get("capex", pd.DataFrame()),
        "copper_gold": bundle.get("copper_gold", pd.DataFrame()),
        "usdjpy": bundle.get("usdjpy", pd.DataFrame()),
        "erp_ttm": bundle.get("erp_ttm", pd.DataFrame()),
    }


def _load_existing_visible_frame(
    base_dataset_path: str | Path | None,
    *,
    value_column: str,
) -> pd.DataFrame:
    if base_dataset_path is None:
        return pd.DataFrame(columns=["observation_date", "effective_date", value_column])

    path = Path(base_dataset_path)
    if not path.exists():
        return pd.DataFrame(columns=["observation_date", "effective_date", value_column])

    frame = pd.read_csv(path, parse_dates=["observation_date", "effective_date"])
    if value_column not in frame.columns:
        return pd.DataFrame(columns=["observation_date", "effective_date", value_column])

    out = frame.loc[:, ["observation_date", "effective_date", value_column]].copy()
    out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce").dt.normalize()
    out["effective_date"] = pd.to_datetime(out["effective_date"], errors="coerce").dt.normalize()
    out[value_column] = pd.to_numeric(out[value_column], errors="coerce")
    return out.dropna(subset=["observation_date"]).sort_values("observation_date")


def _combine_preferred_frame(primary: pd.DataFrame, fallback: pd.DataFrame) -> pd.DataFrame:
    if primary is not None and not primary.empty:
        return primary
    return fallback


def build_historical_macro_dataset(
    output_path: str | Path | None = None,
    *,
    base_dataset_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Build the canonical PIT-safe v12 macro dataset used by backtests and production.
    """
    bundle = _harmonize_v12_bundle(global_macro.fetch_v12_historical_series_bundle())
    credit_spread_fallback = _load_existing_visible_frame(base_dataset_path, value_column="credit_spread_bps")
    real_yield_fallback = _load_existing_visible_frame(base_dataset_path, value_column="real_yield_10y_pct")
    liquidity_fallback = _load_existing_visible_frame(base_dataset_path, value_column="net_liquidity_usd_bn")

    bundle["credit_spread"] = _combine_preferred_frame(bundle["credit_spread"], credit_spread_fallback)
    bundle["real_yield"] = _combine_preferred_frame(bundle["real_yield"], real_yield_fallback)

    if liquidity_fallback.empty:
        weekly_frames = macro_v3.fetch_research_historical_primary_series(series_ids=_LIQUIDITY_SERIES)
        liquidity = _build_weekly_liquidity_frame(weekly_frames)
    else:
        liquidity = liquidity_fallback

    calendar = _build_business_calendar(
        liquidity,
        bundle["credit_spread"],
        bundle["real_yield"],
        bundle["treasury_vol"],
        bundle["breakeven"],
        bundle["capex"],
        bundle["copper_gold"],
        bundle["usdjpy"],
    )
    if calendar.empty:
        raise ValueError("No historical v12 macro dates available")

    daily = pd.DataFrame(index=calendar)
    daily["observation_date"] = daily.index
    daily["effective_date"] = daily.index

    daily["credit_spread_bps"] = _asof_align_from_date_column(
        bundle["credit_spread"], "effective_date", "credit_spread_bps", calendar
    )
    daily["real_yield_10y_pct"] = _asof_align_from_date_column(
        bundle["real_yield"], "effective_date", "real_yield_10y_pct", calendar
    )
    daily["net_liquidity_usd_bn"] = _asof_align_from_date_column(
        liquidity, "effective_date", "net_liquidity_usd_bn", calendar
    )
    daily["treasury_vol_21d"] = _asof_align_from_date_column(
        bundle["treasury_vol"], "effective_date", "treasury_vol_21d", calendar
    )
    daily["copper_gold_ratio"] = _asof_align_from_date_column(
        bundle["copper_gold"], "effective_date", "copper_gold_ratio", calendar
    )
    daily["breakeven_10y"] = _asof_align_from_date_column(
        bundle["breakeven"], "effective_date", "breakeven_10y", calendar
    )
    daily["core_capex_mm"] = _asof_align_from_date_column(
        bundle["capex"], "effective_date", "core_capex_mm", calendar
    )
    daily["usdjpy"] = _asof_align_from_date_column(
        bundle["usdjpy"], "effective_date", "usdjpy", calendar
    )
    daily["erp_ttm_pct"] = _asof_align_from_date_column(
        bundle["erp_ttm"], "effective_date", "erp_ttm_pct", calendar
    )

    # v12.2: Add Hybrid-PIT Real-time Features (T+0 price context)
    # We fetch QQQ history from price collector to ensure T+0 sync
    from src.collector.price import fetch_price_data
    price_data = fetch_price_data()
    price_hist = price_data["history"].copy()

    # Force tz-naive and normalized index for alignment
    if price_hist.index.tz is not None:
        price_hist.index = price_hist.index.tz_localize(None)
    price_hist.index = price_hist.index.normalize()

    daily["qqq_close"] = _asof_align_from_date_column(
        price_hist.reset_index().rename(columns={"Date": "effective_date"}),
        "effective_date", "Close", calendar
    )
    daily["qqq_volume"] = _asof_align_from_date_column(
        price_hist.reset_index().rename(columns={"Date": "effective_date"}),
        "effective_date", "Volume", calendar
    )

    daily["credit_acceleration_pct_10d"] = daily["credit_spread_bps"].pct_change(periods=10).mul(100.0)
    daily["liquidity_roc_pct_4w"] = daily["net_liquidity_usd_bn"].pct_change(periods=20).mul(100.0)
    daily["forward_pe"] = np.nan
    daily["erp_pct"] = np.nan
    daily["funding_stress_flag"] = (daily["credit_spread_bps"].fillna(0.0) >= 500.0).astype(int)

    daily["source_credit_spread"] = "fred:BAMLH0A0HYM2"
    daily["source_real_yield"] = "fred:DFII10"
    daily["source_net_liquidity"] = "derived:fred:WALCL-WDTGAL-RRPONTSYD"
    daily["source_treasury_vol"] = "direct:fred_dgs10"
    daily["source_copper_gold"] = "direct:yfinance"
    daily["source_breakeven"] = "direct:fred_t10yie"
    daily["source_core_capex"] = "direct:fred_neworder"
    daily["source_usdjpy"] = "direct:yfinance"
    daily["source_erp_ttm"] = "direct:shiller"
    daily["source_forward_pe"] = "deprecated:v12"
    daily["source_erp"] = "deprecated:v12"
    daily["source_funding_stress"] = "derived:v12_credit_spread"
    daily["build_version"] = BUILD_VERSION

    canonical = daily.reset_index(drop=True)
    validate_historical_macro_frame(canonical)

    if output_path is not None:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canonical.to_csv(out_path, index=False)

    return canonical


def build_and_summarize(output_path: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    df = build_historical_macro_dataset(output_path=output_path)
    return df, summarize_historical_macro_coverage(df)
