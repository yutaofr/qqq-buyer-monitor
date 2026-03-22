import pytest
from datetime import date
from src.engine.aggregator import aggregate
from src.models import AllocationState, Tier1Result, Tier2Result, SignalDetail

def create_mock_results(score=50):
    fg = SignalDetail(name="F&G", value=50, points=10, thresholds=(30, 70), triggered_half=False, triggered_full=False)
    t1 = Tier1Result(
        score=score, 
        drawdown_52w=None, 
        ma200_deviation=None, 
        vix=None, 
        fear_greed=fg, 
        breadth=None
    )
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=True, gamma_source="yf", put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    return t1, t2

def test_l1_watch_defense_trigger():
    """验证 L1: 仅信用利差加速触发 WATCH_DEFENSE"""
    t1, t2 = create_mock_results()
    # 模拟信用利差 10 日扩张 16% (> 15%)
    result = aggregate(
        market_date=date.today(),
        price=400.0,
        tier1=t1,
        tier2=t2,
        credit_accel=16.0 # 新增参数
    )
    assert result.allocation_state == AllocationState.WATCH_DEFENSE
    assert result.portfolio.leverage_ratio == 1.0

def test_l2_deleverage_trigger():
    """验证 L2: 信用加速 + 流动性负增长触发 DELEVERAGE"""
    t1, t2 = create_mock_results()
    result = aggregate(
        market_date=date.today(),
        price=400.0,
        tier1=t1,
        tier2=t2,
        credit_accel=16.0,
        liquidity_roc=-2.5 # 新增参数
    )
    assert result.allocation_state == AllocationState.DELEVERAGE
    assert 20.0 <= result.target_cash_pct <= 35.0

def test_l3_cash_flight_trigger():
    """验证 L3: 三重共振触发 CASH_FLIGHT"""
    t1, t2 = create_mock_results()
    result = aggregate(
        market_date=date.today(),
        price=400.0,
        tier1=t1,
        tier2=t2,
        credit_accel=16.0,
        liquidity_roc=-2.5,
        is_funding_stressed=True # 新增参数
    )
    assert result.allocation_state == AllocationState.CASH_FLIGHT
    assert result.daily_tranche_pct == 0.0
    assert result.target_cash_pct >= 50.0
