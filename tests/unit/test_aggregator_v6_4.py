import pytest
import pandas as pd
import numpy as np
from datetime import date
from src.engine.aggregator import aggregate, get_target_allocation
from src.models import AllocationState, TargetAllocationState, Tier1Result, Tier2Result, CurrentPortfolioState

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
    prices = 100.0 * (1 + 0.001 * np.arange(100))
    return pd.DataFrame({
        "Open": prices, "High": prices*1.01, "Low": prices*0.99, "Close": prices, "Volume": 1000
    }, index=dates)

def test_deterministic_selector_logic():
    """Selector should filter by AC-4 and pick best CAGR."""
    from src.engine.allocation_search import find_best_allocation
    from src.models import AllocationState, TargetAllocationState
    
    cand1 = TargetAllocationState(0.3, 0.5, 0.2, 0.9)
    cand2 = TargetAllocationState(0.3, 0.6, 0.1, 0.8)
    
    # Score 1: Better CAGR but higher Beta Deviation (invalid)
    # Score 2: Lower CAGR but valid Beta Deviation
    scores = [
        {"candidate": cand1, "cagr": 0.15, "max_drawdown": 0.25, "mean_interval_beta_deviation": 0.06, "turnover": 0.5},
        {"candidate": cand2, "cagr": 0.12, "max_drawdown": 0.20, "mean_interval_beta_deviation": 0.04, "turnover": 0.4},
    ]
    
    # Should pick cand2 because cand1 is invalid by AC-4 (0.06 > 0.05)
    best = find_best_allocation(AllocationState.BASE_DCA, scores)
    assert best == cand2

    # If both valid, pick highest CAGR
    scores[0]["mean_interval_beta_deviation"] = 0.03
    best = find_best_allocation(AllocationState.BASE_DCA, scores)
    assert best == cand1

def test_defensive_states_enforce_zero_qld():
    """AC-2: Target QLD% = 0 in all defensive states."""
    for state in [AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT]:
        target = get_target_allocation(state)
        assert target.target_qld_pct == 0.0
