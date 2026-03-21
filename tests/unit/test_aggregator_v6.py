import pytest
from datetime import date
from src.models import (
    Signal, AllocationState, Tier1Result, Tier2Result, 
    SignalDetail, MarketData, SignalResult
)
from src.engine.aggregator import aggregate

def test_aggregator_produces_logic_trace():
    # Setup minimal valid data
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    t1 = Tier1Result(
        score=50, drawdown_52w=detail, ma200_deviation=detail, 
        vix=detail, fear_greed=detail, breadth=detail,
        descent_velocity="NORMAL", stress_score=0, capitulation_score=0,
        persistence_score=0
    )
    t2 = Tier2Result(adjustment=0, put_wall=500.0, call_wall=600.0, gamma_flip=550.0, 
                    support_confirmed=True, support_broken=False, upside_open=True, 
                    gamma_positive=True, gamma_source="bs",
                    put_wall_distance_pct=0.02, call_wall_distance_pct=0.05)
    
    res = aggregate(
        market_date=date.today(),
        price=560.0,
        tier1=t1,
        tier2=t2,
        credit_spread=300.0,
        forward_pe=20.0,
        real_yield=1.5
    )
    
    # Assert trace exists and has expected steps
    assert len(res.logic_trace) > 0
    # Steps should follow the SDT: Regime -> Tactical -> Allocation -> Overlay -> Finalize
    steps = [node["step"] for node in res.logic_trace]
    assert "structural_regime" in steps
    assert "tactical_state" in steps
    assert "allocation_policy" in steps
    assert "overlay_refinement" in steps
    assert "finalize" in steps

def test_logic_trace_records_veto_constraint():
    # Setup scenario: High score but RICH_TIGHTENING regime should cap allocation
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    # 90 score usually means FAST_ACCUMULATE in NEUTRAL
    t1 = Tier1Result(
        score=90, drawdown_52w=detail, ma200_deviation=detail, 
        vix=detail, fear_greed=detail, breadth=detail,
        descent_velocity="NORMAL", stress_score=20, capitulation_score=40,
        persistence_score=0
    )
    t2 = Tier2Result(adjustment=0, put_wall=500.0, call_wall=600.0, gamma_flip=550.0, 
                    support_confirmed=True, support_broken=False, upside_open=True, 
                    gamma_positive=True, gamma_source="bs",
                    put_wall_distance_pct=0.02, call_wall_distance_pct=0.05)
    
    # RICH_TIGHTENING: spread=320, erp=3.5 (approx)
    res = aggregate(
        market_date=date.today(),
        price=560.0,
        tier1=t1,
        tier2=t2,
        credit_spread=320.0, # Elevated but below transition stress
        forward_pe=20.0,     # ERP = 5.0 - 1.5 = 3.5 (> 2.5)
        real_yield=1.5
    )
    
    # Verify the trace captures the "RICH_TIGHTENING" constraint
    allocation_step = next(node for node in res.logic_trace if node["step"] == "allocation_policy")
    assert "RICH_TIGHTENING" in allocation_step["reason"]
    assert res.allocation_state == AllocationState.SLOW_ACCUMULATE # Capped from FAST
