import logging
import pandas as pd

logger = logging.getLogger(__name__)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

def fetch_credit_spread(series_id: str = "BAMLH0A0HYM2") -> float | None:
    """
    Fetch the latest Ice BofA US High Yield Index Option-Adjusted Spread.
    Uses public FRED CSV download endpoint without requiring an API key.
    Returns the latest available spread in basis points (e.g. 350 for 3.50%).
    """
    try:
        url = FRED_CSV_URL.format(series_id)
        df = pd.read_csv(url, na_values=".")
        if df.empty:
            logger.warning("FRED returned empty data for %s", series_id)
            return None
        
        # Clean data: drop NaNs
        df = df.dropna(subset=[series_id])
        if df.empty:
            logger.warning("No valid numeric data found for %s", series_id)
            return None
            
        # Extract the most recent value
        latest_val = float(df.iloc[-1][series_id])
        
        # The data is in percentage points (e.g. 3.42). Convert to basis points for easier thresholding (342).
        return latest_val * 100
        
    except Exception as exc:
        logger.warning("Failed to fetch FRED %s via CSV scraping: %s", series_id, exc)
        return None
