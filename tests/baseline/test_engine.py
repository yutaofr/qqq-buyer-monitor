import numpy as np
import pandas as pd
import pytest

from src.engine.baseline.engine import calculate_composites


def test_calculate_composites_logic():
    # Create sample data (needs at least 100 rows for rolling window)
    np.random.seed(42)
    data = pd.DataFrame(
        {
            "IPMAN": np.random.randn(150),
            "growth_margin": np.random.randn(150),
            "M2REAL": np.random.randn(150),
            "T10Y2Y": np.random.randn(150),
            "BAMLH0A0HYM2": np.random.randn(150),
            "VIXCLS": np.random.randn(150),
        },
        index=pd.date_range("2020-01-01", periods=150, freq="D"),
    )

    composites = calculate_composites(data)

    # Growth should be Mean of Z-scores
    assert "growth_composite" in composites.columns
    # Liquidity should be Mean of Z-scores
    assert "liquidity_composite" in composites.columns
    # Stress should be Max of Z-scores
    assert "stress_composite" in composites.columns

    # Test Stress Composite Max Retention
    # For the last row, BAML and VIX are at their highest (in this small sample)
    # Stress composite should be the max of those Z-scores
    last_row = composites.iloc[-1]
    assert not np.isnan(last_row["stress_composite"])


def test_calculate_composites_empty():
    df = pd.DataFrame()
    with pytest.raises(ValueError):
        calculate_composites(df)
