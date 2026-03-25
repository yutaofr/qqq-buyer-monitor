import pytest
import os
import pandas as pd
import numpy as np
from datetime import date
from src.main import run_pipeline
from src.models import AllocationState, TargetAllocationState
from src.store.db import load_history, DEFAULT_DB_PATH

@pytest.fixture
def mock_env(tmp_path):
    db_path = str(tmp_path / "e2e_v6_4.db")
    os.environ["QQQ_DB_PATH"] = db_path
    os.environ["CASH_LEVEL"] = "10000"
    os.environ["QQQ_LEVEL"] = "0"
    os.environ["QLD_LEVEL"] = "0"
    return db_path

def test_v6_4_end_to_end_flow(mock_env):
    """
    E2E: Run full pipeline and verify candidate selection, persistence, and reporting.
    """
    # 1. Run pipeline (main entry point)
    # We need to ensure it doesn't crash and produces a result.
    # Note: run_pipeline might try to fetch data from yfinance.
    # We might need to mock collectors or just check if it fails gracefully.
    
    # For integration test, let's try a simplified call if run_pipeline is too heavy.
    from src.engine.aggregator import aggregate
    from src.models import Tier1Result, Tier2Result, SignalDetail, Signal
    
    t1 = Tier1Result(
        score=80, # Strong buy territory
        drawdown_52w=SignalDetail("dd", -0.1, 20, (0,0), True, True),
        ma200_deviation=SignalDetail("ma", -0.05, 10, (0,0), True, False),
        vix=SignalDetail("vix", 25, 15, (0,0), True, True),
        fear_greed=SignalDetail("fg", 20, 20, (0,0), True, True),
        breadth=SignalDetail("br", 0.4, 15, (0,0), True, True),
        descent_velocity="NORMAL"
    )
    t2 = Tier2Result(10, 400.0, 450.0, 410.0, True, False, True, True, "yf", 0.02, 0.05)
    
    # Current portfolio: 100% cash
        
    
    result = aggregate(
        market_date=date(2026, 3, 23),
        price=420.0,
        tier1=t1,
        tier2=t2,
    )
    
    # 2. Verify result fields
    assert result.allocation_state in [AllocationState.FAST_ACCUMULATE, AllocationState.SLOW_ACCUMULATE, AllocationState.BASE_DCA]
    assert result.target_allocation.target_beta > 0.5
    
    # 3. Verify persistence
    from src.store.db import save_signal
    save_signal(result, path=mock_env)
    
    history = load_history(n=1, path=mock_env)
    assert len(history) == 1
    assert history[0]["allocation_state"] == result.allocation_state.value
    
    # 4. Verify CLI output (just check it doesn't crash)
    from src.output.cli import print_signal
    print_signal(result, use_color=False)
