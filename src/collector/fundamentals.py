import logging
import yfinance as yf

logger = logging.getLogger(__name__)

def fetch_forward_pe(ticker: str = "QQQ") -> dict:
    """
    Fetch trailing and forward PE ratios.
    For ETFs like QQQ, yfinance may only provide trailingPE. Forward PE might be None.
    Returns:
        dict: {'trailing_pe': float | None, 'forward_pe': float | None}
    """
    result = {"trailing_pe": None, "forward_pe": None}
    try:
        q = yf.Ticker(ticker)
        info = q.info
        
        # Use .get() to avoid KeyError if the fields are surprisingly absent
        result["trailing_pe"] = info.get("trailingPE")
        result["forward_pe"] = info.get("forwardPE")
        
        # If ETF data is sparse, we could optionally scrape Yahoo's actual HTML or Invesco 
        # but yfinance info is the most stable keyless entry point for now.
        if result["trailing_pe"] is None:
            logger.warning("yfinance did not return trailingPE for %s", ticker)
            
    except Exception as exc:
        logger.warning("Failed to fetch fundamentals for %s: %s", ticker, exc)
        
    return result
