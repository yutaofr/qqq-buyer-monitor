import os
import pytest
from src.models import CurrentPortfolioState, TargetAllocationState, SignalResult, Signal, Tier1Result, Tier2Result, AllocationState
from datetime import date

def test_current_portfolio_state_from_env_fallback():
    """AC-1: CurrentPortfolioState.from_env() falls back to 100% cash on all-zero or invalid inputs."""
    # Test all zeros
    os.environ["CASH_LEVEL"] = "0"
    os.environ["QQQ_LEVEL"] = "0"
    os.environ["QLD_LEVEL"] = "0"
    state = CurrentPortfolioState.from_env()
    assert state.current_cash_pct == 1.0
    assert state.qqq_pct == 0.0
    assert state.qld_pct == 0.0

    # Test invalid inputs
    os.environ["CASH_LEVEL"] = "invalid"
    os.environ["QQQ_LEVEL"] = "None"
    os.environ["QLD_LEVEL"] = "NaN"
    state = CurrentPortfolioState.from_env()
    assert state.current_cash_pct == 1.0
    assert state.qqq_pct == 0.0
    assert state.qld_pct == 0.0

    # Test negative values (clipping)
    os.environ["CASH_LEVEL"] = "-100"
    os.environ["QQQ_LEVEL"] = "0"
    os.environ["QLD_LEVEL"] = "0"
    state = CurrentPortfolioState.from_env()
    assert state.current_cash_pct == 1.0

def test_target_allocation_state_serialization():
    """TargetAllocationState round-trips through to_dict() / from_dict() if present."""
    original = TargetAllocationState(
        target_cash_pct=0.2,
        target_qqq_pct=0.4,
        target_qld_pct=0.4,
        target_beta=1.2
    )
    
    # Check if methods exist and work
    assert hasattr(original, 'to_dict')
    data = original.to_dict()
    assert data["target_cash_pct"] == 0.2
    assert data["target_qqq_pct"] == 0.4
    assert data["target_qld_pct"] == 0.4
    assert data["target_beta"] == 1.2

    assert hasattr(TargetAllocationState, 'from_dict')
    recovered = TargetAllocationState.from_dict(data)
    assert recovered == original

def test_signal_result_v6_4_fields():
    """SignalResult can carry current_portfolio, target_allocation, effective_exposure, and interval_beta_audit."""
    # We don't need a full Tier1Result/Tier2Result for this test if we use mocks or empty objects
    # but let's just use defaults if possible.
    
    current = CurrentPortfolioState(current_cash_pct=0.5, qqq_pct=0.5)
    target = TargetAllocationState(target_cash_pct=0.3, target_qqq_pct=0.7)
    
    result = SignalResult(
        date=date(2026, 3, 23),
        price=400.0,
        signal=Signal.NO_SIGNAL,
        final_score=50,
        tier1=None, # In real usage this would be a Tier1Result
        tier2=None, # In real usage this would be a Tier2Result
        explanation="Test",
        current_portfolio=current,
        target_allocation=target,
        effective_exposure=0.7,
        interval_beta_audit=[{"date": "2026-03-23", "beta": 0.7}]
    )
    
    assert result.current_portfolio == current
    assert result.target_allocation == target
    assert result.effective_exposure == 0.7
    assert len(result.interval_beta_audit) == 1
