import pytest
from datetime import date
from src.models import (
    Signal, AllocationState, Tier1Result, Tier2Result, 
    SignalDetail, SignalResult
)
from src.store.db import _to_json_dict
import json

def test_logic_trace_persistence_serialization():
    # Setup data with a populated trace
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    t1 = Tier1Result(
        score=0, drawdown_52w=detail, ma200_deviation=detail, 
        vix=detail, fear_greed=detail, breadth=detail
    )
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=False, gamma_source="bs",
                    put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    trace = [{"step": "test", "decision": "OK"}]
    
    res = SignalResult(
        date=date.today(),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="test",
        logic_trace=trace
    )
    
    # Serialize
    json_dict = _to_json_dict(res)
    
    # Assert logic_trace is in the dict
    assert "logic_trace" in json_dict
    assert json_dict["logic_trace"] == trace
    
    # Round trip via JSON string
    blob = json.dumps(json_dict)
    back_dict = json.loads(blob)
    assert back_dict["logic_trace"] == trace
