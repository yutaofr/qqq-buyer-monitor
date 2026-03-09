import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Wilder's RSI for a given pandas Series."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Optional: Wilder's smoothing for more accuracy, but simple rolling mean is often acceptable for basic divergence
    return rsi

def check_divergences(
    current_price: float, 
    current_vix: float, 
    current_breadth: float, 
    df: pd.DataFrame | None,
    current_revision_breadth: float | None = None
) -> dict:
    """
    Check for technical divergences between current data and recent historical minimums.
    Also checks for Earnings Revision Divergence (v3.0).
    Returns a dict with boolean flags and a total divergence bonus score.
    """
    result = {
        "price_breadth": False,
        "price_vix": False,
        "price_rsi": False,
        "price_revision": False,
        "bonus_score": 0
    }
    
    if df is None or len(df) < 15:
        logger.debug("Not enough history to calculate divergence.")
        return result
        
    try:
        # Check if price is making a new low compared to the window (e.g., last 60 days)
        # Allow a small margin (e.g., 1%) to count as a "new low" zone.
        hist_min_price = df['price'].min()
        
        if current_price <= hist_min_price * 1.01:
            # Price is at or near the 60-day low. Find the date of the historic low.
            min_price_idx = df['price'].idxmin()
            # If the min price happened recently (e.g., today or yesterday), we compare it to the SECOND lowest dip
            # But for simplicity, we just compare current indicators against the minimal price context.
            hist_breadth_at_min = df.loc[min_price_idx, 'breadth']
            hist_vix_at_min = df.loc[min_price_idx, 'vix']
            
            # --- Price-Breadth Divergence ---
            # Current price is lower, but breadth is HIGHER (less stocks are participating in the drop)
            if current_breadth > hist_breadth_at_min:
                logger.info("🔥 Price-Breadth Divergence detected! Breadth improved while price dropped.")
                result["price_breadth"] = True
                result["bonus_score"] += 15
                
            # --- Price-VIX Divergence ---
            # Current price is lower, but VIX is LOWER (less panic/protection buying)
            if current_vix < hist_vix_at_min:
                logger.info("🔥 Price-VIX Divergence detected! VIX failed to make new highs on price lows.")
                result["price_vix"] = True
                result["bonus_score"] += 10
                
            # --- Price-RSI Divergence ---
            rsi_series = _calculate_rsi(df['price'])
            if not rsi_series.isna().all():
                hist_rsi_at_min = rsi_series.loc[min_price_idx]
                current_rsi = rsi_series.iloc[-1]
                
                # If RSI is higher now than at the previous price low
                if current_rsi > hist_rsi_at_min:
                    logger.info("🔥 Price-RSI Divergence detected! RSI making higher lows.")
                    result["price_rsi"] = True
                    result["bonus_score"] += 5
                    
            # --- Epic 4: Fundamental Earnings Revision Divergence ---
            if current_revision_breadth is not None:
                # If price is at low, but analysts are upwardly revising earnings on net (>50%)
                if current_revision_breadth > 50.0:
                    logger.info("🌟 FUNDAMENTAL DIVERGENCE: Price at new low, but Earnings Revisions > 50%% (%.1f%%). Strong Buy!", current_revision_breadth)
                    result["price_revision"] = True
                    result["bonus_score"] += 20
                    
    except Exception as exc:
        logger.warning("Failed to calculate divergences: %s", exc)
        
    return result
