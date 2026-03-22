import pandas as pd
import logging
from datetime import date
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class HistoricalMacroSeeder:
    """Loads and provides historical macro indicators for backtesting."""
    
    def __init__(self, csv_path: Optional[str] = None, mock_df: Optional[pd.DataFrame] = None):
        if mock_df is not None:
            self.df = mock_df.copy()
        elif csv_path:
            try:
                self.df = pd.read_csv(csv_path)
            except Exception as exc:
                logger.error("Failed to load historical macro from %s: %s", csv_path, exc)
                self.df = pd.DataFrame()
        else:
            self.df = pd.DataFrame()
            
        if not self.df.empty:
            if "observation_date" in self.df.columns:
                self.df["observation_date"] = pd.to_datetime(self.df["observation_date"])
                self.df = self.df.sort_values("observation_date")
                self.df = self.df.set_index("observation_date")
            
            # Resample to daily and ffill to ensure no gaps
            self.df = self.df.resample("D").ffill()
            
    def get_features_for_date(self, target_date: date) -> Dict[str, Any]:
        """Retrieve macro features for a specific date, including acceleration."""
        features = {
            "credit_spread": None,
            "credit_accel": 0.0,
            "liquidity_roc": 0.0,
            "is_funding_stressed": False
        }
        
        if self.df.empty:
            return features
            
        target_ts = pd.Timestamp(target_date)
        
        # Check if date is in range
        if target_ts < self.df.index.min():
            return features
            
        # Use ffill indexer
        idx = self.df.index.get_indexer([target_ts], method='ffill')[0]
        if idx == -1:
            return features
            
        actual_ts = self.df.index[idx]
        row = self.df.iloc[idx]
        
        features["credit_spread"] = float(row.get("BAMLH0A0HYM2", 0.0))
        features["liquidity_roc"] = float(row.get("liquidity_roc", 0.0))
        features["is_funding_stressed"] = bool(row.get("is_funding_stressed", False))
        
        # Calculate 10-day acceleration
        try:
            start_ts = actual_ts - pd.Timedelta(days=10)
            if start_ts in self.df.index:
                start_val = float(self.df.loc[start_ts].get("BAMLH0A0HYM2", 0.0))
                if start_val > 0:
                    features["credit_accel"] = ((features["credit_spread"] - start_val) / start_val) * 100.0
        except Exception:
            pass
            
        return features
