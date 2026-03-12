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
    
    # Need 260 trading days of history to compute MA200 reliably
    start = target_date - timedelta(days=400)

    ticker_obj = yf.Ticker(ticker)
    hist = ticker_obj.history(start=start.isoformat(), end=query_end.isoformat())

    if hist.empty:
        raise RuntimeError(f"No price data available for {ticker} ending {target_date}")

    close = hist["Close"]

    # Most recent close
    price = float(close.iloc[-1])
    record_date = close.index[-1].date()

    # 200-day moving average (use all available, max 200 rows)
    ma200 = float(close.rolling(200, min_periods=150).mean().iloc[-1])

    # 52-week high
    one_year_ago = target_date - timedelta(days=365)
    recent = close[close.index >= str(one_year_ago)]
    high_52w = float(recent.max()) if not recent.empty else float(close.max())

    logger.debug(
        "Price data: price=%.2f ma200=%.2f high_52w=%.2f date=%s",
        price, ma200, high_52w, record_date,
    )
    return {"price": price, "ma200": ma200, "high_52w": high_52w, "date": record_date}
