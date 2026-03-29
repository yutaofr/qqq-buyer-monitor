import json
from datetime import date

from src.models import Signal, SignalDetail, SignalResult, Tier1Result, Tier2Result
from src.store.db import _to_json_dict, load_history, save_signal


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

def test_v6_3_strategic_fields_db_roundtrip(tmp_path):
    """验证 v6.3 战略配置字段在数据库保存/加载周期中的完整性"""
    from src.models import TargetAllocationState
    db_path = str(tmp_path / "test_v6_3.db")

    # 1. 构造带有战略字段的 Result
    t = TargetAllocationState(target_cash_pct=0.1, target_qqq_pct=0.9, target_qld_pct=0.0, target_beta=0.9)

    # 极简 t1/t2
    detail = SignalDetail("test", 0.0, 0, (0, 0), False, False)
    t1 = Tier1Result(score=0, drawdown_52w=detail, ma200_deviation=detail, vix=detail, fear_greed=detail, breadth=detail)
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None,
                    support_confirmed=False, support_broken=False, upside_open=False,
                    gamma_positive=False, gamma_source="bs",
                    put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)

    res = SignalResult(
        date=date.today(),
        price=400.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="v6.3 persistence test",
        target_allocation=t,
    )

    # 2. 保存并加载
    save_signal(res, path=db_path)
    history = load_history(n=1, path=db_path)
    loaded = history[0]

    # 3. 断言

    assert loaded["target_allocation"]["target_cash_pct"] == 0.1
    assert loaded["target_allocation"]["target_beta"] == 0.9
