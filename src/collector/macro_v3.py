import logging
import pandas as pd
import random
from src.collector.macro import FRED_CSV_URL

logger = logging.getLogger(__name__)

def fetch_us10y() -> float | None:
    """
    Fetch the latest 10-Year Treasury Constant Maturity Rate (DGS10) from FRED.
    Returns the yield as a percentage (e.g. 4.25 for 4.25%).
    """
    series_id = "DGS10"
    try:
        url = FRED_CSV_URL.format(series_id)
        df = pd.read_csv(url, na_values=".")
        if df.empty:
            return None
        
        df = df.dropna(subset=[series_id])
        if df.empty:
            return None
            
        return float(df.iloc[-1][series_id])
    except Exception as exc:
        logger.warning("Failed to fetch US10Y from FRED: %s", exc)
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
