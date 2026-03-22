import pytest
from datetime import date
from src.models import AllocationState, PortfolioState, SignalResult, Tier1Result, Tier2Result, Signal

def test_allocation_state_v6_2_enums():
    """验证 AllocationState 包含 v6.2 定义的防御性枚举"""
    # 预期包含的新状态
    assert AllocationState.WATCH_DEFENSE == "WATCH_DEFENSE"
    assert AllocationState.DELEVERAGE == "DELEVERAGE"
    assert AllocationState.CASH_FLIGHT == "CASH_FLIGHT"

def test_portfolio_state_model():
    """验证 PortfolioState 模型及其字段"""
    portfolio = PortfolioState(
        current_cash_pct=0.15,
        leverage_ratio=1.2,
        gross_exposure_pct=1.2,
        net_exposure_pct=1.0,
        core_equity_pct=0.8,
        tactical_equity_pct=0.2
    )
    assert portfolio.current_cash_pct == 0.15
    assert portfolio.leverage_ratio == 1.2
    assert portfolio.net_exposure_pct == 1.0

def test_signal_result_carries_portfolio_v6_2():
    """验证 SignalResult 能够承载组合状态（可选）"""
    # 构造一个模拟的 SignalResult
    # 注意：目前 SignalResult 可能还不支持 portfolio 字段，这会导致测试失败
    t1 = Tier1Result(score=50, drawdown_52w=None, ma200_deviation=None, vix=None, fear_greed=None, breadth=None)
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=True, gamma_source="yf", put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    portfolio = PortfolioState(current_cash_pct=0.3)
    
    result = SignalResult(
        date=date.today(),
        price=400.0,
        signal=Signal.NO_SIGNAL,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="Test",
        allocation_state=AllocationState.WATCH_DEFENSE,
        portfolio=portfolio # 预期此字段目前不存在
    )
    
    assert result.portfolio.current_cash_pct == 0.3
    assert result.allocation_state == AllocationState.WATCH_DEFENSE
