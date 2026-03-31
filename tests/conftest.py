"""Shared pytest fixtures for v11 Bayesian convergence."""
from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_macro_df() -> pd.DataFrame:
    """A minimal historical macro dataset for v11 feature seeding."""
    dates = pd.date_range(start="2020-01-01", periods=10, freq="D")
    data = {
        "observation_date": dates,
        "effective_date": dates + pd.Timedelta(days=1),
        "credit_spread_bps": [300.0, 310.0, 320.0, 350.0, 400.0, 450.0, 420.0, 400.0, 380.0, 360.0],
        "erp_pct": [0.04, 0.041, 0.042, 0.045, 0.05, 0.055, 0.052, 0.05, 0.048, 0.046],
        "real_yield_10y_pct": [0.01, 0.011, 0.012, 0.015, 0.02, 0.025, 0.022, 0.02, 0.018, 0.016],
        "net_liquidity_usd_bn": [6000.0, 5950.0, 5900.0, 5800.0, 5700.0, 5600.0, 5650.0, 5700.0, 5750.0, 5800.0],
        "vix": [15.0, 16.0, 18.0, 22.0, 30.0, 35.0, 28.0, 25.0, 22.0, 20.0],
        "qqq_close": [300.0, 298.0, 295.0, 280.0, 260.0, 250.0, 265.0, 275.0, 285.0, 290.0],
    }
    return pd.DataFrame(data).set_index("observation_date")
