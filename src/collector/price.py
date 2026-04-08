"""Price data collector: QQQ close, MA200, 52-week high."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_price_data(ticker: str = "QQQ", as_of: date | None = None) -> dict:
    """
    Fetch closing price, 200-day MA, and 52-week high for *ticker*.

    Returns:
        {
            "price": float,
            "ma200": float,
            "high_52w": float,
            "date": date,
        }

    Raises:
        RuntimeError if data cannot be fetched.
    """
    # yfinance end date is exclusive. To include target_date, we query up to target_date + 1.
    target_date = as_of or date.today()
    query_end = target_date + timedelta(days=1)

    # Need at least 2 years of history for v6.0 indicators (POC, Variance Ratio, Z-Scores)
    # 2 years = ~500 trading days
    start = target_date - timedelta(days=735)

    ticker_obj = yf.Ticker(ticker)
    hist = ticker_obj.history(start=start.isoformat(), end=query_end.isoformat())

    if hist.empty:
        raise RuntimeError(f"No price data available for {ticker} ending {target_date}")

    close = hist["Close"]

    # Defensive: yfinance may return trailing rows with NaN close
    # (e.g., during pre-market or intraday queries). Drop them.
    valid_close = close.dropna()
    if valid_close.empty:
        raise RuntimeError(f"No valid close prices for {ticker} ending {target_date}")

    # Most recent close
    price = float(valid_close.iloc[-1])
    record_date = valid_close.index[-1].date()

    # 200-day moving average (use all available, max 200 rows)
    ma200 = float(close.rolling(200, min_periods=150).mean().iloc[-1])

    # 52-week high and days since it happened
    one_year_ago = target_date - timedelta(days=365)
    recent = close[close.index >= str(one_year_ago)]
    if not recent.empty:
        high_52w = float(recent.max())
        # Find the most recent date where the high occurred
        high_date = recent[recent == high_52w].index[-1].date()
        days_since_high = (record_date - high_date).days
    else:
        high_52w = float(close.max())
        days_since_high = 0

    logger.debug(
        "Price data: price=%.2f ma200=%.2f high_52w=%.2f (days ago: %d) date=%s",
        price,
        ma200,
        high_52w,
        days_since_high,
        record_date,
    )
    return {
        "price": price,
        "ma200": ma200,
        "high_52w": high_52w,
        "days_since_high": days_since_high,
        "date": record_date,
        "history": hist.loc[hist["Close"].notna()],  # PIT-safe: exclude incomplete rows
    }
