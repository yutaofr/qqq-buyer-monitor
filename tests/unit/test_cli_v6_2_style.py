import pytest
from datetime import date
from src.output.cli import print_signal
from src.models import SignalResult, AllocationState, Signal, Tier1Result, Tier2Result, SignalDetail

def create_mock_result(state: AllocationState):
    fg = SignalDetail(name="F&G", value=50, points=10, thresholds=(30, 70), triggered_half=False, triggered_full=False)
    t1 = Tier1Result(score=50, drawdown_52w=None, ma200_deviation=None, vix=None, fear_greed=fg, breadth=None)
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=True, gamma_source="yf", put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    return SignalResult(
        date=date.today(),
        price=400.0,
        signal=Signal.NO_SIGNAL,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="测试防御文案",
        allocation_state=state
    )

def test_cli_handles_defensive_states():
    """验证 CLI 能够渲染新的防御状态而不崩溃"""
    # 依次测试三个新状态
    for state in [AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT]:
        result = create_mock_result(state)
        # 如果内部缺少映射，这里会抛出 KeyError
        try:
            print_signal(result, use_color=False)
        except KeyError as e:
            pytest.fail(f"CLI crashed on state {state} with KeyError: {e}")
