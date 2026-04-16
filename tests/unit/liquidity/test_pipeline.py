import numpy as np
import pandas as pd
import pytest

from src.liquidity.config import load_config
from src.liquidity.engine.pipeline import LiquidityPipeline, StaleTickError


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def test_pipeline(config):
    # Short burn-in for testing
    return LiquidityPipeline(config, burn_in=5)


def test_liquidity_pipeline_burn_in_state(test_pipeline):
    """Pipeline should emit burn_in state and 0.0 weight during the burn window."""
    raw_obs = {
        "vix": 15.0,
        "walcl": 4e6,
        "rrp": 0.0,
        "tga": 3e5,
        "sofr": 0.05,
        "constituent_returns": np.zeros(50)
    }

    # Burn-in is 5 ticks
    dt = pd.Timestamp("2024-01-01")
    for i in range(5):
        weight, log = test_pipeline.step(dt, raw_obs)
        assert weight == 0.0
        assert log["state"] == "burn_in"
        assert log["burn_in_remaining"] == 4 - i
        dt += pd.Timedelta(days=1)

    # The 6th tick should be active
    weight, log = test_pipeline.step(dt, raw_obs)
    assert log["state"] == "active"
    assert "burn_in_remaining" not in log
    assert "s_t" in log

    # Check monotonicity
    with pytest.raises(StaleTickError):
        test_pipeline.step(dt - pd.Timedelta(days=1), raw_obs)


def test_liquidity_pipeline_passes_diagnostics(test_pipeline):
    """Pipeline should correctly format the log with all expected diagnostic keys post-burn-in."""
    raw_obs = {
        "vix": 15.0,
        "walcl": 4e6,
        "rrp": 0.0,
        "tga": 3e5,
        "sofr": 0.05,
        "constituent_returns": np.zeros(50)
    }

    dt = pd.Timestamp("2024-01-01")
    for _ in range(5):
        test_pipeline.step(dt, raw_obs)
        dt += pd.Timedelta(days=1)

    weight, log = test_pipeline.step(dt, raw_obs)

    required_keys = {
        "state", "weight", "p_cp", "s_t", "s_cp_t", "s_level_t",
        "regime_severity", "vol_guard_cap", "dominant_run_length",
        "regime_sigma2_spread", "signal", "days_held", "l_target",
        "l_final", "qld", "qqq", "cash", "tau_t", "lambda_macro"
    }

    for key in required_keys:
        assert key in log, f"Missing required key: {key} in active log"
