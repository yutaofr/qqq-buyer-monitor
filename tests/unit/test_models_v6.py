import pytest
from datetime import date
from src.models import SignalResult, Signal, AllocationState, Tier1Result, Tier2Result, SignalDetail

def test_signal_result_has_logic_trace():
    # Setup dummy data
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    t1 = Tier1Result(
        score=0, drawdown_52w=detail, ma200_deviation=detail, 
        vix=detail, fear_greed=detail, breadth=detail
    )
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=False, gamma_source="bs", 
                    put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    res = SignalResult(
        date=date.today(),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="test"
    )
    
    # Check if logic_trace exists and is a list (per ADR-006)
    assert hasattr(res, "logic_trace")
    assert isinstance(res.logic_trace, list)
    assert len(res.logic_trace) == 0
