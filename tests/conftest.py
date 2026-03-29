"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.models import MarketData


@pytest.fixture
def sample_options_df() -> pd.DataFrame:
    """A minimal options chain with known OI and gamma values for deterministic tests."""
    rows = [
        # Calls
        {"strike": 400.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 1000, "impliedVolatility": 0.20, "gamma": 0.01, "gamma_source": "yfinance"},
        {"strike": 410.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 5000, "impliedVolatility": 0.20, "gamma": 0.02, "gamma_source": "yfinance"},
        {"strike": 420.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 8000, "impliedVolatility": 0.18, "gamma": 0.015, "gamma_source": "yfinance"},  # call wall
        {"strike": 430.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 2000, "impliedVolatility": 0.18, "gamma": 0.008, "gamma_source": "yfinance"},
        # Puts
        {"strike": 400.0, "expiration": "2026-03-21", "option_type": "put",
         "openInterest": 9000, "impliedVolatility": 0.25, "gamma": 0.018, "gamma_source": "yfinance"},  # put wall
        {"strike": 390.0, "expiration": "2026-03-21", "option_type": "put",
         "openInterest": 4000, "impliedVolatility": 0.28, "gamma": 0.012, "gamma_source": "yfinance"},
        {"strike": 380.0, "expiration": "2026-03-21", "option_type": "put",
         "openInterest": 2000, "impliedVolatility": 0.30, "gamma": 0.006, "gamma_source": "yfinance"},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def neutral_market_data(sample_options_df) -> MarketData:
    """Market data with neutral (mid-range) values — should score ~40."""
    return MarketData(
        date=date(2026, 3, 8),
        price=410.0,
        ma200=405.0,  # price slightly above MA200 → deviation ~+1.2% → 0 pts
        high_52w=440.0,  # drawdown ~6.8% → below 8% → 0 pts
        vix=18.0,  # below 22 → 0 pts
        fear_greed=50,  # neutral → 0 pts
        adv_dec_ratio=0.75,  # healthy breadth → 0 pts
        pct_above_50d=0.55,  # healthy → 0 pts
        options_df=sample_options_df,
    )


@pytest.fixture
def bullish_market_data(sample_options_df) -> MarketData:
    """Market data with extremely bullish (contrarian) values — should score high."""
    return MarketData(
        date=date(2026, 3, 8),
        price=412.0,
        ma200=450.0,  # price below MA200 by ~8.4% → 20 pts
        high_52w=480.0,  # drawdown ~14.2% → 20 pts
        vix=35.0,  # above 30 → 20 pts
        fear_greed=15,  # extreme fear (<=20) → 20 pts
        adv_dec_ratio=0.35,  # capitulation → 20 pts
        pct_above_50d=0.20,  # extreme → 20 pts (full breadth)
        options_df=sample_options_df,
    )
