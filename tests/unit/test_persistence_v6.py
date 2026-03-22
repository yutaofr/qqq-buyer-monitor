import pytest
import os
from datetime import date
from src.models import (
    Signal, AllocationState, Tier1Result, Tier2Result, 
    SignalDetail, SignalResult
)
from src.store.db import _to_json_dict, save_signal, load_history
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

def test_logic_trace_db_roundtrip(tmp_path):
    # End-to-end test for DB persistence
    db_file = tmp_path / "test_signals.db"
    db_path = str(db_file)
    
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    t1 = Tier1Result(
        score=50, drawdown_52w=detail, ma200_deviation=detail, 
        vix=detail, fear_greed=detail, breadth=detail
    )
    t2 = Tier2Result(adjustment=0, put_wall=500.0, call_wall=600.0, gamma_flip=None, 
                    support_confirmed=True, support_broken=False, upside_open=True, 
                    gamma_positive=False, gamma_source="bs",
                    put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    trace = [
        {"step": "step1", "decision": "VAL1"},
        {"step": "step2", "decision": "VAL2"}
    ]
    
    res = SignalResult(
        date=date.today(),
        price=550.0,
        signal=Signal.WATCH,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="test trip",
        logic_trace=trace
    )
    
    # Save to DB
    save_signal(res, path=db_path)
    
    # Load from DB
    history = load_history(n=1, path=db_path)
    
    assert len(history) == 1
    loaded_signal = history[0]
    
    assert "logic_trace" in loaded_signal
    assert loaded_signal["logic_trace"] == trace
    assert loaded_signal["logic_trace"][0]["step"] == "step1"
