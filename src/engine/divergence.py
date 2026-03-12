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

def _calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Money Flow Index (MFI) for a given DataFrame containing High, Low, Close, Volume."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    
    delta = typical_price.diff()
    positive_flow = money_flow.where(delta > 0, money_flow * 0)
    negative_flow = money_flow.where(delta < 0, money_flow * 0)
    
    pos_sum = positive_flow.rolling(window=period).sum()
    neg_sum = negative_flow.rolling(window=period).sum()
    
    # Avoid division by zero
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mfr))
    return mfi.fillna(50)

def check_divergences(
    current_price: float, 
    current_vix: float, 
    current_breadth: float, 
    df: pd.DataFrame | None,
    current_revision_breadth: float | None = None,
    current_hist_df: pd.DataFrame | None = None
) -> dict:
    """
    Check for technical divergences between current data and recent historical minimums.
    Includes MFI (Money Flow Index) divergence for v4.2.
    """
    result = {
        "price_breadth": False,
        "price_vix": False,
        "price_rsi": False,
        "price_mfi": False,
        "price_revision": False,
        "bonus_score": 0
    }
    
    # We need history to calculate divergence
    if df is None or len(df) < 15:
        logger.debug("Not enough history to calculate divergence.")
        return result
        
    try:
        # Price low detection (relative to last ~30-60 records in signals DB)
        hist_min_price = df['price'].min()
        
        if current_price <= hist_min_price * 1.01:
            min_price_idx = df['price'].idxmin()
            
            # 1. Breadth Divergence
            hist_breadth_at_min = df.loc[min_price_idx, 'breadth']
            if current_breadth > hist_breadth_at_min:
                logger.info("🔥 Price-Breadth Divergence detected! Breadth improved while price dropped.")
                result["price_breadth"] = True
                result["bonus_score"] += 15
                
            # 2. VIX Divergence
            hist_vix_at_min = df.loc[min_price_idx, 'vix']
            if current_vix < hist_vix_at_min:
                logger.info("🔥 Price-VIX Divergence detected! VIX failed to make new highs on price lows.")
                result["price_vix"] = True
                result["bonus_score"] += 10
                
            # 3. RSI Divergence
            rsi_series = _calculate_rsi(df['price'])
            if not rsi_series.isna().all():
                hist_rsi_at_min = rsi_series.loc[min_price_idx]
                current_rsi = rsi_series.iloc[-1]
                if current_rsi > hist_rsi_at_min:
                    logger.info("🔥 Price-RSI Divergence detected! RSI making higher lows.")
                    result["price_rsi"] = True
                    result["bonus_score"] += 5

            # 4. MFI Divergence (v4.2)
            if current_hist_df is not None and not current_hist_df.empty:
                mfi_series = _calculate_mfi(current_hist_df)
                if not mfi_series.isna().all():
                    # Find price low in historical OHLCV df
                    ohlc_min_idx = current_hist_df['Close'].idxmin()
                    hist_mfi_at_min = mfi_series.loc[ohlc_min_idx]
                    current_mfi = mfi_series.iloc[-1]
                    
                    if current_mfi > hist_mfi_at_min:
                        logger.info("🔥 Price-MFI Divergence detected! Strong money flow on price low.")
                        result["price_mfi"] = True
                        result["bonus_score"] += 10
                    
            # 5. Fundamental Earnings Revision Divergence
            if current_revision_breadth is not None:
                if current_revision_breadth > 50.0:
                    logger.info("🌟 FUNDAMENTAL DIVERGENCE: Price at new low, but Earnings Revisions > 50%% (%.1f%%). Strong Buy!", current_revision_breadth)
                    result["price_revision"] = True
                    result["bonus_score"] += 20
                    
    except Exception as exc:
        logger.warning("Failed to calculate divergences: %s", exc)
        
    return result
