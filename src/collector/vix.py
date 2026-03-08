"""VIX data collector."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)

VIX_TICKER = "^VIX"


def fetch_vix(as_of: date | None = None) -> float:
    """
    Fetch the most recent VIX closing level.

    Returns:
        VIX closing value as float.

    Raises:
        RuntimeError if data cannot be fetched.
    """
    end = as_of or date.today()
    start = end - timedelta(days=10)  # buffer for weekends/holidays

    ticker_obj = yf.Ticker(VIX_TICKER)
    hist = ticker_obj.history(start=start.isoformat(), end=end.isoformat())

    if hist.empty:
        raise RuntimeError(f"No VIX data available for period ending {end}")

    vix_value = float(hist["Close"].iloc[-1])
    logger.debug("VIX: %.2f", vix_value)
    return vix_value
