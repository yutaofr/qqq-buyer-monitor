import os
import logging
import pandas as pd
import requests
import io
import time

logger = logging.getLogger(__name__)

FRED_CSV_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
    "&mode=fred&cosd=1776-07-04&coed=9999-12-31"
    "&fq=Daily&fam=avg&transformation=lin"
)

def fetch_fred_api(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Fetch FRED data using the official API (JSON format)."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None
        
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json"
    try:
        logger.debug("Fetching FRED %s via API...", series_id)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get("observations", [])
        if not observations:
            return None
            
        df = pd.DataFrame(observations)
        df = df.rename(columns={"date": "observation_date", "value": series_id})
        # Ensure numeric conversion
        df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
        return df[["observation_date", series_id]]
    except Exception as exc:
        logger.warning("FRED API fetch failed for %s: %s", series_id, exc)
        return None

def fetch_fred_data(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Unified FRED fetcher: API first, then CSV fallback."""
    # 1. API
    df = fetch_fred_api(series_id, timeout)
    if df is not None and not df.empty:
        return df
        
    # 2. CSV Fallback
    logger.info("Official FRED API failed or no key; falling back to CSV scraping for %s...", series_id)
    return fetch_fred_csv(series_id, timeout)

def fetch_fred_csv(series_id: str, timeout: int = 15, retries: int = 3) -> pd.DataFrame | None:
    """Helper to fetch FRED CSV data with timeout and retries."""
    url = FRED_CSV_URL.format(series_id)
    # Using a very standard browser user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/csv,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    for attempt in range(retries + 1):
        try:
            logger.debug("Fetching FRED %s (attempt %d)...", series_id, attempt + 1)
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return pd.read_csv(io.StringIO(response.text), na_values=".")
        except Exception as exc:
            if attempt < retries:
                logger.debug("FRED %s fetch attempt %d failed: %s. Retrying in 2s...", series_id, attempt + 1, exc)
                time.sleep(2) # Shorter wait between retries
            else:
                logger.warning("Failed to fetch FRED %s after %d retries: %s", series_id, retries + 1, exc)
    return None

def fetch_chicago_fed_nfci() -> float | None:
    """
    Fetch the National Financial Conditions Index (NFCI) from Chicago Fed.
    URL: https://www.chicagofed.org/~/media/publications/nfci/nfci-indexes-csv.csv
    Returns the latest NFCI value (Positive = tighter/stressed, Negative = looser/calm).
    """
    url = "https://www.chicagofed.org/-/media/publications/nfci/nfci-indexes-csv.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        # The Chicago Fed CSV has some header rows; find where the data starts
        content = response.text
        lines = content.splitlines()
        
        # Look for the line starting with 'Date' which is the header
        header_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Date"):
                header_idx = i
                break
        
        if header_idx == -1:
            return None
            
        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
        if df.empty:
            return None
            
        # NFCI is usually the second column
        latest_val = float(df.iloc[-1]["NFCI"])
        logger.info("Fetched NFCI from Chicago Fed: %.3f", latest_val)
        
        # NFCI is a standard deviation index. To "proxy" it as a spread (bps) for our engine:
        # A value of 0 is neutral. A value of 1.0 is high stress. 
        # Map 0 -> 350 bps (neutral spread), 1.0 -> 600 bps (stressed spread)
        return 350.0 + (latest_val * 250.0)
    except Exception as exc:
        logger.debug("Chicago Fed NFCI fetch failed: %s", exc)
        return None

def fetch_hyg_proxy() -> float | None:
    """
    Fallback: Use HYG (High Yield ETF) as a proxy for credit spreads.
    Lower HYG relative to its 200d MA implies widening spreads.
    """
    import yfinance as yf
    try:
        hyg = yf.Ticker("HYG")
        hist = hyg.history(period="1y")
        if hist.empty:
            return None
            
        price = float(hist["Close"].iloc[-1])
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1])
        
        # If HYG is 5% below its 200d MA, spreads are likely widening (bullish contrarian signal).
        # We return a synthetic "spread" to keep the engine happy.
        # price == ma200 -> 350 bps
        # price == 0.95 * ma200 -> 500 bps
        deviation = (ma200 - price) / ma200
        synthetic_spread = 350.0 + (deviation * 3000.0)
        logger.info("Fetched HYG proxy spread: %.0f bps (deviation from MA200: %.2f%%)", 
                    synthetic_spread, deviation * 100)
        return synthetic_spread
    except Exception as exc:
        logger.debug("HYG proxy fetch failed: %s", exc)
        return None

def fetch_credit_spread(series_id: str = "BAMLH0A0HYM2") -> float | None:
    """
    Fetch the latest Ice BofA US High Yield Index Option-Adjusted Spread.
    1. Primary: FRED
    2. Fallback: Chicago Fed NFCI
    3. Fallback: HYG Proxy
    """
    # 1. FRED
    try:
        df = fetch_fred_data(series_id)
        if df is not None and not df.empty:
            df = df.dropna(subset=[series_id])
            if not df.empty:
                latest_val = float(df.iloc[-1][series_id])
                return latest_val * 100
    except Exception as exc:
        logger.debug("Error processing FRED %s: %s", series_id, exc)

    # 2. Chicago Fed NFCI Fallback
    logger.info("FRED unavailable; attempting Chicago Fed NFCI fallback...")
    nfci_val = fetch_chicago_fed_nfci()
    if nfci_val is not None:
        return nfci_val
        
    # 3. HYG Proxy Fallback
    logger.info("Chicago Fed unavailable; attempting HYG proxy fallback...")
    return fetch_hyg_proxy()

def fetch_short_volume_proxy(ticker: str = "QQQ") -> float | None:
    """
    v5.0: Fetch Short Volume Ratio as an institutional sentiment proxy.
    Since real-time FINRA API is restricted, we use a rolling average 
    of put/call volume or a public scrape if available.
    
    For this implementation, we use Yahoo Finance volume metrics to 
    derive a 'De-facto' short ratio based on price action vs volume spikes.
    
    Logic: High volume on a down day without a breakdown often implies
    institutional absorption (bullish).
    """
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if len(hist) < 2:
            return None
            
        # Proxy: Volatility-adjusted Volume Ratio
        # In a real system, this would fetch from a FINRA CSV drop.
        # Here we simulate the 'Short Ratio' logic:
        # If today's volume is 1.5x average and price didn't crash, 
        # it implies high 'Short Exempt' or absorption.
        latest = hist.iloc[-1]
        avg_vol = hist["Volume"].mean()
        vol_ratio = latest["Volume"] / avg_vol
        
        # We return a synthetic ratio between 0.3 and 0.7
        # High vol on green days -> lower 'short ratio' (0.4)
        # High vol on red days -> higher 'short ratio' (0.65)
        base = 0.5
        price_change = (latest["Close"] - latest["Open"]) / latest["Open"]
        
        if price_change < -0.01:
            base += 0.1 * vol_ratio
        elif price_change > 0.01:
            base -= 0.05 * vol_ratio
            
        return min(0.8, max(0.2, base))
    except Exception as exc:
        logger.debug("Short volume proxy fetch failed: %s", exc)
        return None
