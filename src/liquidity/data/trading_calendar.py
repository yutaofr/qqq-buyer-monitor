"""Trading calendar anchoring via yfinance-first strategy.

SRD v1.2 / Story 3.2 — Lookback Padding Architecture:
    The trading calendar is the single source of truth for day-counting.
    yfinance QQQ price index is used because:
      - It includes all market closures (9/11, COVID, etc.) automatically
      - It returns an exact DatetimeIndex of business days
      - It is always available, unlike exchange APIs

This eliminates the "timedelta approximation" pitfall where
504 trading days ≠ any fixed number of calendar days.

MAX_LOOKBACK = 504 (R_MAX, 2 years of trading)
CALENDAR_BUFFER = 800 (calendar days to pre-fetch — larger than 730 for safety margin)
"""

from datetime import timedelta

import pandas as pd
import yfinance as yf

MAX_LOOKBACK: int = 504       # largest rolling window across all signal modules
CALENDAR_BUFFER: int = 800   # calendar-day buffer: 504 TDs ≈ 730 cal days + 70 safety


def build_trading_calendar(start_date: str, end_date: str) -> pd.DatetimeIndex:
    """Fetch QQQ OHLC and extract its DatetimeIndex as the trading calendar.

    Fetch range = (start_date − CALENDAR_BUFFER calendar days) → end_date.
    This over-fetches on the left to ensure the calendar contains enough
    history for compute_padded_start() to back-count MAX_LOOKBACK trading days.

    Args:
        start_date: ISO date string — the intended backtest start (NOT the fetch start).
        end_date:   ISO date string — the backtest end.

    Returns:
        pd.DatetimeIndex of trading days spanning roughly
        (start_date − 800 cal days) to end_date.

    Raises:
        RuntimeError: if yfinance returns an empty DataFrame.
    """
    fetch_start = (
        pd.Timestamp(start_date) - timedelta(days=CALENDAR_BUFFER)
    ).strftime("%Y-%m-%d")

    hist = yf.download(
        "QQQ",
        start=fetch_start,
        end=end_date,
        progress=False,
        auto_adjust=True,
    )

    if hist.empty:
        raise RuntimeError(
            f"No price data returned by yfinance for QQQ "
            f"[{fetch_start} → {end_date}]. "
            f"Check network connectivity or date range."
        )

    # Normalise index: remove timezone, keep date precision
    idx = hist.index.normalize()
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_localize(None)

    return pd.DatetimeIndex(idx)


def compute_padded_start(
    trading_days: pd.DatetimeIndex,
    target_start: str,
    lookback: int = MAX_LOOKBACK,
) -> pd.Timestamp:
    """Locate target_start in the trading calendar and step back `lookback` days.

    This is the core of the Lookback Padding architecture.
    The returned date is the actual fetch start for all data sources.

    Args:
        trading_days: Full trading calendar from build_trading_calendar().
        target_start: The intended backtest start date (ISO string).
        lookback:     Number of trading days to pad. Default MAX_LOOKBACK=504.

    Returns:
        pd.Timestamp — the padded fetch start (a valid trading day).

    Raises:
        IndexError: if the calendar does not contain enough history before
                    target_start to provide `lookback` trading days of padding.
    """
    target_ts = pd.Timestamp(target_start)

    # Find the position of target_start in the calendar (bfill: snap to next TD)
    idx_pos = trading_days.searchsorted(target_ts, side="left")

    if idx_pos < lookback:
        raise IndexError(
            f"Insufficient history in trading calendar before {target_start}. "
            f"Need {lookback} trading days of padding, only {idx_pos} available. "
            f"Calendar starts at {trading_days[0].date()}. "
            f"Increase CALENDAR_BUFFER or move start_date later."
        )

    padded_start = trading_days[idx_pos - lookback]
    return padded_start
