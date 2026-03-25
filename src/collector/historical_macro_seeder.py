import pandas as pd
import logging
from datetime import date
from typing import Optional, Dict, Any

from src.research.data_contracts import validate_historical_macro_frame

logger = logging.getLogger(__name__)


class HistoricalMacroSeeder:
    """Loads and provides historical macro indicators for backtesting."""

    def __init__(self, csv_path: Optional[str] = None, mock_df: Optional[pd.DataFrame] = None):
        self._canonical_mode = False
        if mock_df is not None:
            self.df = mock_df.copy()
            self._canonical_mode = self._looks_canonical(self.df)
        elif csv_path:
            try:
                self.df = pd.read_csv(csv_path)
                self._canonical_mode = True
            except Exception as exc:
                logger.error("Failed to load historical macro from %s: %s", csv_path, exc)
                self.df = pd.DataFrame()
        else:
            self.df = pd.DataFrame()

        if not self.df.empty:
            if self._canonical_mode:
                validate_historical_macro_frame(self.df)
                self.df = self._prepare_canonical_frame(self.df)
            else:
                self.df = self._prepare_legacy_mock_frame(self.df)

    @staticmethod
    def _looks_canonical(df: pd.DataFrame) -> bool:
        return {"observation_date", "effective_date"}.issubset(df.columns)

    @staticmethod
    def _prepare_canonical_frame(df: pd.DataFrame) -> pd.DataFrame:
        frame = df.copy()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
        frame["effective_date"] = pd.to_datetime(frame["effective_date"], errors="coerce")
        frame = frame.sort_values("effective_date").set_index("effective_date")
        return frame.resample("D").ffill()

    @staticmethod
    def _prepare_legacy_mock_frame(df: pd.DataFrame) -> pd.DataFrame:
        frame = df.copy()
        if "observation_date" in frame.columns:
            frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
            frame = frame.dropna(subset=["observation_date"]).sort_values("observation_date")
            frame = frame.set_index("observation_date")
        return frame.resample("D").ffill() if not frame.empty and isinstance(frame.index, pd.DatetimeIndex) else frame

    @staticmethod
    def _float_or_default(value: Any, default: float | None = None) -> float | None:
        if pd.isna(value):
            return default
        return float(value)

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
        
        if target_ts < self.df.index.min():
            return features

        idx = self.df.index.get_indexer([target_ts], method='ffill')[0]
        if idx == -1:
            return features

        row = self.df.iloc[idx]

        if self._canonical_mode:
            features["credit_spread"] = self._float_or_default(row.get("credit_spread_bps"))
            features["credit_accel"] = self._float_or_default(row.get("credit_acceleration_pct_10d"), 0.0) or 0.0
            features["real_yield"] = self._float_or_default(row.get("real_yield_10y_pct"))
            features["liquidity_roc"] = self._float_or_default(row.get("liquidity_roc_pct_4w"), 0.0) or 0.0
            funding_value = row.get("funding_stress_flag")
        else:
            features["credit_spread"] = self._float_or_default(row.get("BAMLH0A0HYM2"))
            features["credit_accel"] = self._float_or_default(row.get("credit_acceleration"), 0.0) or 0.0
            features["real_yield"] = self._float_or_default(row.get("real_yield"), None)
            features["liquidity_roc"] = self._float_or_default(row.get("liquidity_roc"), 0.0) or 0.0
            funding_value = row.get("is_funding_stressed")

        features["is_funding_stressed"] = bool(funding_value) if not pd.isna(funding_value) else False

        return features
