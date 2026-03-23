import pytest
import os
import json
from datetime import date
from src.store.db import save_signal, load_history, _to_json_dict, _migrate_blob
from src.models import (
    SignalResult, Signal, Tier1Result, Tier2Result, AllocationState,
    CurrentPortfolioState, TargetAllocationState, SignalDetail
)

@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_v6_4.db")

def test_persistence_v6_4_fields(temp_db):
    """v6.4 fields survive save/load cycle."""
    t1 = Tier1Result(
        score=50,
        drawdown_52w=SignalDetail("dd", 0, 0, (0,0), False, False),
        ma200_deviation=SignalDetail("ma", 0, 0, (0,0), False, False),
        vix=SignalDetail("vix", 0, 0, (0,0), False, False),
        fear_greed=SignalDetail("fg", 0, 0, (0,0), False, False),
        breadth=SignalDetail("br", 0, 0, (0,0), False, False),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "yf", 0, 0)
    
    current = CurrentPortfolioState(current_cash_pct=0.2, qqq_pct=0.4, qld_pct=0.4)
    target = TargetAllocationState(target_cash_pct=0.1, target_qqq_pct=0.8, target_qld_pct=0.1, target_beta=1.0)
    
    result = SignalResult(
        date=date(2026, 3, 23),
        price=400.0,
        signal=Signal.TRIGGERED,
        final_score=60,
        tier1=t1,
        tier2=t2,
        explanation="Test",
        current_portfolio=current,
        target_allocation=target,
        effective_exposure=1.2,
        interval_beta_audit=[{"state": "FAST", "deviation": 0.01}]
    )
    
    save_signal(result, path=temp_db)
    history = load_history(n=1, path=temp_db)
    
    assert len(history) == 1
    blob = history[0]
    
    assert blob["current_portfolio"]["current_cash_pct"] == 0.2
    assert blob["target_allocation"]["target_beta"] == 1.0
    assert blob["effective_exposure"] == 1.2
    assert len(blob["interval_beta_audit"]) == 1

def test_migration_from_v6_2():
    """Verify lazy migration from older v6.2 style blobs."""
    old_blob = {
        "date": "2025-01-01",
        "price": 300.0,
        "signal": "WATCH",
        "portfolio": {
            "current_cash_pct": 0.5,
            "leverage_ratio": 1.0,
            "gross_exposure_pct": 0.5,
            "net_exposure_pct": 0.5
        }
    }
    
    migrated = _migrate_blob(old_blob)
    
    assert "current_portfolio" in migrated
    assert migrated["current_portfolio"]["current_cash_pct"] == 0.5
    assert "target_allocation" in migrated
    assert migrated["target_allocation"]["target_beta"] == 0.9 # default
    assert "interval_beta_audit" in migrated
