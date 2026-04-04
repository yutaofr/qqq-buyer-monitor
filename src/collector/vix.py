"""VIX data collector."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)

VIX_TICKER = "^VIX"
VIX3M_TICKER = "^VIX3M"


def fetch_vix(as_of: date | None = None) -> float:
    """
    Fetch the most recent VIX closing level.

    Returns:
        VIX closing value as float.

    Raises:
        RuntimeError if data cannot be fetched.
    """
    target_date = as_of or date.today()
    query_end = target_date + timedelta(days=1)
    start = target_date - timedelta(days=10)  # buffer for weekends/holidays

    ticker_obj = yf.Ticker(VIX_TICKER)
    hist = ticker_obj.history(start=start.isoformat(), end=query_end.isoformat())

    if hist.empty:
        raise RuntimeError(f"No VIX data available for period ending {target_date}")

    vix_value = float(hist["Close"].iloc[-1])
    logger.debug("VIX: %.2f", vix_value)
    return vix_value


def _fetch_single_ticker_close(ticker: str, target_date: date) -> float:
    query_end = target_date + timedelta(days=1)
    start = target_date - timedelta(days=10)
    ticker_obj = yf.Ticker(ticker)
    hist = ticker_obj.history(start=start.isoformat(), end=query_end.isoformat())
    if hist.empty:
        raise RuntimeError(f"No price data available for {ticker} ending {target_date}")
    return float(hist["Close"].iloc[-1])


def fetch_vix_term_structure(as_of: date | None = None) -> dict[str, float | None]:
    """Fetch the current VIX and VIX3M closes."""
    target_date = as_of or date.today()
    vix = _fetch_single_ticker_close(VIX_TICKER, target_date)
    try:
        vix3m = _fetch_single_ticker_close(VIX3M_TICKER, target_date)
    except Exception:  # noqa: BLE001
        vix3m = None
    return {"vix": vix, "vix3m": vix3m}
