import pandas as pd

from src.engine.fundamentals import (
    CHEAP_PE_THRESHOLD,
    EXPENSIVE_PE_THRESHOLD,
    calculate_pe_zscore,
    calculate_valuation_weight,
)


def test_calculate_pe_zscore_none():
    assert calculate_pe_zscore(None, None) is None
    assert calculate_pe_zscore(25.0, None) is None
    series = pd.Series([20.0, 21.0]) # Less than 10
    assert calculate_pe_zscore(25.0, series) is None

def test_calculate_pe_zscore_zero_std():
    series = pd.Series([25.0] * 15)
    assert calculate_pe_zscore(26.0, series) == 0.0

def test_calculate_pe_zscore_valid():
    series = pd.Series([20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0])
    mean = series.mean() # 24.5
    std = series.std()

    current = 28.0
    expected_z = (current - mean) / std

    assert calculate_pe_zscore(current, series) == expected_z

def test_calculate_valuation_weight_none():
    assert calculate_valuation_weight(None, None) == 0

def test_calculate_valuation_weight_with_zscore():
    # Mean 24.5, std ~3.027
    series = pd.Series([20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0])

    # 1 SD below (Z < -1.0) -> +10
    assert calculate_valuation_weight(20.0, series) == 10

    # -1.0 <= Z <= -0.5 -> +5
    assert calculate_valuation_weight(22.0, series) == 5

    # 2 SD above (Z > 2.0) -> -10
    assert calculate_valuation_weight(31.0, series) == -10

    # 1.5 <= Z < 2.0 -> -5
    assert calculate_valuation_weight(29.5, series) == -5

    # -0.5 < Z < 1.5 -> 0
    assert calculate_valuation_weight(25.0, series) == 0

def test_calculate_valuation_weight_absolute_fallback():
    # Use thresholds if no series
    assert calculate_valuation_weight(CHEAP_PE_THRESHOLD, None) == 10
    assert calculate_valuation_weight(CHEAP_PE_THRESHOLD - 1.0, None) == 10

    assert calculate_valuation_weight(EXPENSIVE_PE_THRESHOLD, None) == -10
    assert calculate_valuation_weight(EXPENSIVE_PE_THRESHOLD + 1.0, None) == -10

    assert calculate_valuation_weight(25.0, None) == 0

def test_calculate_fcf_bonus():
    from src.engine.fundamentals import calculate_fcf_bonus
    assert calculate_fcf_bonus(None) == 0
    assert calculate_fcf_bonus(3.0) == 0
    assert calculate_fcf_bonus(4.5) == 0
    assert calculate_fcf_bonus(4.6) == 15
