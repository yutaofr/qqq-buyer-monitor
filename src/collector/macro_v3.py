import logging
import pandas as pd
import random
from src.collector.macro import fetch_fred_data

logger = logging.getLogger(__name__)

import yfinance as yf
from datetime import date, timedelta

def fetch_real_yield() -> float | None:
    """
    Fetch the latest 10-Year Treasury Inflation-Indexed Security (TIPS) Rate (DFII10) from FRED.
    Falls back to Yahoo Finance (^TNX) minus 2.0% inflation expectation proxy if FRED is unavailable.
    Returns the real yield as a percentage (e.g. 2.25 for 2.25%).
    """
    series_id = "DFII10"
    # 1. Primary: FRED
    try:
        df = fetch_fred_data(series_id)
        if df is not None and not df.empty:
            df = df.dropna(subset=[series_id])
            if not df.empty:
                val = float(df.iloc[-1][series_id])
                logger.debug("Fetched Real Yield (TIPS) from FRED: %.2f", val)
                return val
    except Exception as exc:
        logger.debug("FRED DFII10 fetch failed: %s", exc)

    # 2. Secondary: Yahoo Finance (^TNX) proxy
    try:
        logger.info("FRED unavailable; attempting yfinance fallback using ^TNX minus 2.0% proxy...")
        tnx = yf.Ticker("^TNX")
        # Query a small window to ensure we get the latest close
        hist = tnx.history(period="5d")
        if not hist.empty:
            # ^TNX value is 10x the yield (e.g. 42.50 = 4.25%), minus hardcoded 2% for real yield proxy
            val = (float(hist["Close"].iloc[-1]) / 10.0) - 2.0
            logger.info("Fetched Real Yield proxy from yfinance (^TNX - 2%%): %.2f", val)
            return val
    except Exception as exc:
        logger.warning("All Real Yield sources failed (FRED & yfinance): %s", exc)
        
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

def fetch_net_liquidity() -> tuple[float | None, float | None]:
    """
    Calculate Fed Net Liquidity: Total Assets (WALCL) - TGA (WTREASMS) - RRP (RRPONTSYD).
    Returns (current_liquidity_in_billions, 4_week_roc_percentage).
    """
    series = ["WALCL", "WDTGAL", "RRPONTSYD"]
    data = {}
    
    try:
        combined_df = pd.DataFrame()
        for s in series:
            try:
                df = fetch_fred_data(s)
                if df is not None and not df.empty:
                    df = df.rename(columns={s: "value"})
                    df["observation_date"] = pd.to_datetime(df["observation_date"])
                    df.set_index("observation_date", inplace=True)
                    data[s] = df
            except Exception as exc:
                logger.debug("Failed to fetch %s: %s", s, exc)

        # Reconstruct combined_df from the fetched data
        if not data:
            return None, None

        for s_id, df_s in data.items():
            if combined_df.empty:
                combined_df = df_s.rename(columns={"value": s_id})
            else:
                combined_df = combined_df.join(df_s.rename(columns={"value": s_id}), how="outer")
        
        if combined_df.empty:
            return None, None
            
        combined_df = combined_df.ffill().dropna()
        required = ["WALCL", "WDTGAL", "RRPONTSYD"]
        if not all(col in combined_df.columns for col in required):
            logger.warning("Missing required Fed components for Net Liquidity. Found: %s", combined_df.columns.tolist())
            return None, None
            
        # Calculate Net Liquidity: WALCL - TGA - RRP
        # WALCL (Millions), WDTGAL (Millions), RRPONTSYD (Billions)
        walcl = combined_df["WALCL"] / 1000.0  # M -> B
        tga = combined_df["WDTGAL"] / 1000.0   # M -> B
        rrp = combined_df["RRPONTSYD"]        # B
        
        net_liq = walcl - tga - rrp
        current_liq = float(net_liq.iloc[-1])
        
        # Calculate 4-week ROC (roughly 4 records if weekly)
        if len(net_liq) >= 5:
            prev_liq = float(net_liq.iloc[-5])
            roc = (current_liq - prev_liq) / prev_liq * 100
        else:
            roc = 0.0
            
        logger.info("Fed Net Liquidity: $%.2fB (4W ROC: %.2f%%)", current_liq, roc)
        return current_liq, roc
        
    except Exception as exc:
        logger.warning("Failed to calculate Fed Net Liquidity: %s", exc)
        return None, None

def fetch_move_index() -> float | None:
    """Fetch the latest MOVE Index (^MOVE) from Yahoo Finance."""
    try:
        ticker = yf.Ticker("^MOVE")
        hist = ticker.history(period="5d")
        if not hist.empty:
            val = float(hist["Close"].iloc[-1])
            logger.info("Fetched MOVE Index: %.2f", val)
            return val
    except Exception as exc:
        logger.warning("FAILED to fetch MOVE Index: %s", exc)
    return None

def fetch_sector_rotation() -> float | None:
    """
    Calculate Sector Rotation: 20-day relative strength of XLP (Defensive) vs QQQ (Growth).
    A decrease in this ratio indicates a shift back to growth stocks.
    Returns the 20-day change in the XLP/QQQ ratio.
    """
    try:
        tickers = ["XLP", "QQQ"]
        # Use simple period string for yfinance
        data = yf.download(tickers, period="40d", interval="1d", progress=False)["Close"]
        if data.empty:
            return None
            
        ratio = data["XLP"] / data["QQQ"]
        current_ratio = ratio.iloc[-1]
        prev_ratio = ratio.iloc[-21] if len(ratio) >= 21 else ratio.iloc[0]
        
        # Relative change in ratio
        rel_change = (current_ratio - prev_ratio) / prev_ratio * 100
        logger.info("Sector Rotation (XLP/QQQ) 20D Change: %.2f%%", rel_change)
        return rel_change
    except Exception as exc:
        logger.warning("FAILED to fetch Sector Rotation: %s", exc)
    return None
