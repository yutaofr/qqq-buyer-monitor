import logging
import pandas as pd
import random
from src.collector.macro import fetch_fred_csv

logger = logging.getLogger(__name__)

import yfinance as yf
from datetime import date, timedelta

def fetch_us10y() -> float | None:
    """
    Fetch the latest 10-Year Treasury Constant Maturity Rate (DGS10) from FRED.
    Falls back to Yahoo Finance (^TNX) if FRED is unavailable.
    Returns the yield as a percentage (e.g. 4.25 for 4.25%).
    """
    series_id = "DGS10"
    # 1. Primary: FRED
    try:
        df = fetch_fred_csv(series_id)
        if df is not None and not df.empty:
            df = df.dropna(subset=[series_id])
            if not df.empty:
                val = float(df.iloc[-1][series_id])
                logger.debug("Fetched US10Y from FRED: %.2f", val)
                return val
    except Exception as exc:
        logger.debug("FRED US10Y fetch failed: %s", exc)

    # 2. Secondary: Yahoo Finance (^TNX)
    try:
        logger.info("FRED unavailable; attempting yfinance fallback for US10Y (^TNX)...")
        tnx = yf.Ticker("^TNX")
        # Query a small window to ensure we get the latest close
        hist = tnx.history(period="5d")
        if not hist.empty:
            # ^TNX value is 10x the yield (e.g. 42.50 = 4.25%)
            val = float(hist["Close"].iloc[-1]) / 10.0
            logger.info("Fetched US10Y from yfinance (^TNX): %.2f", val)
            return val
    except Exception as exc:
        logger.warning("All US10Y sources failed (FRED & yfinance): %s", exc)
        
    return None

def fetch_fcf_yield(ticker: str = "QQQ") -> float | None:
    """
    Fetch the Free Cash Flow Yield for the given ticker.
    Without a commercial API, calculating highly accurate aggregate FCF yield 
    for an ETF is difficult. We return a mock plausible value for v3.0 PoC.
    Returns percentage (e.g. 3.5 for 3.5%).
    """
    # In a real production system, this would scrape yfinance or AlphaVantage
    # For now, return a mock value oscillating around 3.0% - 5.0%
    logger.debug("Using simulated FCF Yield for %s due to keyless constraint", ticker)
    val = round(3.5 + random.uniform(-1.0, 1.5), 2)
    return val

def fetch_earnings_revisions_breadth(ticker: str = "QQQ") -> float | None:
    """
    Fetch the percentage of analyst upward revisions for the ETF components.
    Without a Bloomberg terminal, this is simulated.
    Returns percentage 0-100 (e.g. 55.0 for 55% upward revisions).
    """
    logger.debug("Using simulated Earnings Revisions Breadth for %s", ticker)
    return round(50.0 + random.uniform(-15.0, 15.0), 2)
