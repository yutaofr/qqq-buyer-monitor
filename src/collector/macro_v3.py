import os
import logging
import pandas as pd
from typing import Optional, Tuple
from src.collector.macro import fetch_fred_data, fetch_fred_api

logger = logging.getLogger(__name__)

def fetch_real_yield() -> Optional[float]:
    """Fetch 10-Year Treasury Real Yield (DFII10)."""
    df = fetch_fred_data("DFII10")
    if df is not None and not df.empty:
        return float(df.iloc[-1]["DFII10"])
    return None

def fetch_fcf_yield() -> Optional[float]:
    """
    Fetch Free Cash Flow Yield proxy for QQQ.
    Currently a simplified placeholder (e.g. inverse of P/FCF).
    """
    return 3.5 # Fixed proxy for now

def fetch_earnings_revisions_breadth() -> Optional[float]:
    """Fetch analyst earnings revisions breadth (Estimate revisions)."""
    return 10.0 # Placeholder for revision breadth

def fetch_move_index() -> Optional[float]:
    """Fetch Bond Volatility Index (MOVE Index)."""
    return 100.0 # Placeholder

def fetch_sector_rotation() -> Optional[float]:
    """Analyze cyclical vs defensive sector rotation."""
    return 1.0 # Placeholder

def fetch_short_volume_proxy() -> Optional[float]:
    """Fetch FINRA short volume ratio for QQQ."""
    return 0.45 # Placeholder

def fetch_net_liquidity(series_id: str = "WDTGAL") -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate Net Liquidity = WALCL - WDTGAL - RRPONTSYD.
    Returns (Latest_Value, 4-Week_ROC).
    
    WALCL: Fed Total Assets
    WDTGAL: Treasury General Account (SSoT prioritizes WDTGAL over WTREGEN)
    RRPONTSYD: Overnight Reverse Repos
    """
    try:
        walcl = fetch_fred_data("WALCL")
        tga = fetch_fred_data(series_id)
        rrp = fetch_fred_data("RRPONTSYD")
        
        if walcl is None or tga is None or rrp is None:
            return None, None
            
        # Merge on date
        merged = pd.merge(walcl, tga, on="observation_date", how="inner")
        merged = pd.merge(merged, rrp, on="observation_date", how="inner")
        
        # Calculate Net Liquidity
        # WALCL is in millions, TGA is in millions, RRP is in billions
        merged["net_liq"] = merged["WALCL"] - merged[series_id] - (merged["RRPONTSYD"] * 1000)
        
        latest_val = float(merged["net_liq"].iloc[-1])
        
        # Calculate 4-Week ROC (roughly 4 data points if weekly)
        # Note: WALCL is weekly (Wednesday). 4 points = 28 days.
        if len(merged) >= 5:
            prev_val = float(merged["net_liq"].iloc[-5])
            roc = ((latest_val - prev_val) / prev_val) * 100.0
        else:
            roc = 0.0
            
        logger.info("Net Liquidity: %.0f M, 4-Week ROC: %.2f%%", latest_val, roc)
        return latest_val, roc
    except Exception as exc:
        logger.error("Failed to calculate net liquidity: %s", exc)
        return None, None

def fetch_credit_acceleration(window: int = 10) -> Optional[float]:
    """
    Calculate high yield credit spread acceleration (BAMLH0A0HYM2).
    Returns the percentage expansion over the specified window (default 10d).
    """
    try:
        series_id = "BAMLH0A0HYM2"
        df = fetch_fred_data(series_id)
        if df is None or len(df) < window:
            return None
            
        latest = float(df.iloc[-1][series_id])
        start = float(df.iloc[-window][series_id])
        
        if start <= 0:
            return 0.0
            
        accel_pct = ((latest - start) / start) * 100.0
        logger.info("Credit Spread Acceleration (10d): %.2f%% (%.2f -> %.2f)", 
                    accel_pct, start, latest)
        return accel_pct
    except Exception as exc:
        logger.error("Failed to calculate credit acceleration: %s", exc)
        return None

def fetch_funding_stress() -> dict:
    """
    Monitor funding market stress via NFCI and CPFF.
    NFCI: National Financial Conditions Index (Positive = Tightening)
    CPFF: Commercial Paper Funding Facility (Or proxy for CP stress)
    """
    stress_info = {"nfci": 0.0, "cpff": 0.0, "is_stressed": False}
    try:
        # NFCI via official API
        nfci_df = fetch_fred_api("NFCI")
        if nfci_df is not None and not nfci_df.empty:
            stress_info["nfci"] = float(nfci_df.iloc[-1]["NFCI"])
            
        # CPFF (Commercial Paper) via API
        cpff_df = fetch_fred_api("CPFF") # Proxy ID
        if cpff_df is not None and not cpff_df.empty:
            stress_info["cpff"] = float(cpff_df.iloc[-1]["CPFF"])
            
        # Logic Gate: NFCI > 0 indicates tighter than average financial conditions
        if stress_info["nfci"] > 0:
            stress_info["is_stressed"] = True
            logger.warning("Funding Stress detected: NFCI=%.3f", stress_info["nfci"])
            
        return stress_info
    except Exception as exc:
        logger.error("Failed to fetch funding stress: %s", exc)
        return stress_info
