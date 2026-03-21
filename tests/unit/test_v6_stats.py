import pandas as pd
import numpy as np
import pytest
from src.utils.stats import calculate_mean_reversion_score, calculate_volume_poc, calculate_sma_deviation_zscore

def test_calculate_mean_reversion_score_high():
    # Extreme deviation (Z-score > 2)
    steady = [100.0] * 50
    spike = [120.0]
    series = pd.Series(steady + spike)
    # 50-day SMA=100, StdDev=~2.8 (with one 120), Z=~7
    score = calculate_mean_reversion_score(series, window=50)
    assert score > 2.0

def test_calculate_mean_reversion_score_low():
    # Steady trend with low deviation
    series = pd.Series(np.linspace(100, 110, 100))
    score = calculate_mean_reversion_score(series, window=50)
    # Z-score of a perfect linear trend relative to its SMA is around 1.7, 
    # but with more data it stabilizes.
    assert score < 2.0

def test_calculate_volume_poc_simple():
    # Create a DataFrame where price 100 has the most volume
    data = {
        'Close': [90, 100, 100, 100, 110],
        'Volume': [1000, 5000, 5000, 5000, 1000]
    }
    df = pd.DataFrame(data)
    poc = calculate_volume_poc(df, bins=10)
    # POC should be near 100
    assert 95 <= poc <= 105

def test_calculate_sma_deviation_zscore_extreme():
    # Create a series that is steady at 100, then drops to 50 (extreme deviation)
    # Window 200, history 500
    steady = [100.0] * 300
    crash = [50.0]
    series = pd.Series(steady + crash)
    
    zs = calculate_sma_deviation_zscore(series, window=200, rolling_window=500)
    # Deviation should be extreme negative
    assert zs < -3.0

def test_calculate_sma_deviation_zscore_insufficient():
    series = pd.Series([100.0] * 50)
    zs = calculate_sma_deviation_zscore(series, window=200)
    assert zs == 0.0
