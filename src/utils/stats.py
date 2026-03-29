"""Statistical utility functions for QQQ monitor."""
from __future__ import annotations

import numpy as np
import pandas as pd


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

def calculate_mean_reversion_score(price_series: pd.Series, window: int = 50) -> float:
    """
    Calculate a mean reversion score based on distance from moving average.
    Returns the Z-score of price relative to its window.
    Negative Score (< -2.0): Extreme oversold (Mean reversion likely).
    Positive Score (> 2.0): Extreme overbought.
    """
    if len(price_series) < window:
        return 0.0

    sma = price_series.rolling(window=window).mean()
    std = price_series.rolling(window=window).std()

    latest_price = price_series.iloc[-1]
    latest_sma = sma.iloc[-1]
    latest_std = std.iloc[-1]

    if latest_std == 0:
        return 0.0

    z_score = (latest_price - latest_sma) / latest_std
    return float(z_score)

def calculate_volume_poc(df: pd.DataFrame, bins: int = 50) -> float:
    """
    Identify the Point of Control (POC) - the price level with the highest volume.
    df must have 'Close' and 'Volume' columns.
    """
    if df.empty or 'Close' not in df.columns or 'Volume' not in df.columns:
        return 0.0

    price_min = df['Low'].min() if 'Low' in df.columns else df['Close'].min()
    price_max = df['High'].max() if 'High' in df.columns else df['Close'].max()

    if price_min == price_max:
        return price_min

    # Create price bins
    price_bins = np.linspace(price_min, price_max, bins + 1)

    # Aggregate volume by bin
    # We use 'Close' for the volume assignment
    df = df.copy()
    df['bin'] = pd.cut(df['Close'], bins=price_bins, include_lowest=True)
    bin_volumes = df.groupby('bin', observed=True)['Volume'].sum()

    if bin_volumes.empty:
        return df['Close'].iloc[-1]

    # Get the bin with max volume
    max_bin = bin_volumes.idxmax()
    # Return midpoint of the bin
    return max_bin.mid

def calculate_sma_deviation_zscore(price_series: pd.Series, window: int = 200, rolling_window: int = 500) -> float:
    """
    Calculate the rolling Z-score of the deviation from SMA.
    Deviation = (Price - SMA) / SMA
    """
    if len(price_series) < window + 20:
        return 0.0

    sma = price_series.rolling(window=window).mean()
    deviation = (price_series - sma) / sma

    # Drop NaNs
    deviation = deviation.dropna()
    if deviation.empty:
        return 0.0

    latest_val = deviation.iloc[-1]
    # Take the historical window for Z-score (at most rolling_window)
    hist_series = deviation.tail(rolling_window)

    if len(hist_series) < 20:
        return 0.0

    return calculate_zscore(latest_val, hist_series)
