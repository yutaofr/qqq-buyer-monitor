"""Statistical utility functions for QQQ monitor."""
from __future__ import annotations

import pandas as pd
import numpy as np

def calculate_zscore(value: float, series: pd.Series | list[float]) -> float:
    """
    Calculate the Z-score of a value relative to a historical series.
    Z = (x - mean) / std_dev
    """
    if not isinstance(series, pd.Series):
        series = pd.Series(series)
        
    series = series.dropna()
    if len(series) < 20: # Need enough data for stable std dev
        return 0.0
        
    mean = series.mean()
    std = series.std()
    
    if std == 0:
        return 0.0
        
    return (value - mean) / std
