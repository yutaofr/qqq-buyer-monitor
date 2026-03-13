import pytest
from datetime import date
from src.models import MarketData, Signal, Tier1Result, Tier2Result, SignalDetail
from src.engine.tier1 import calculate_descent_velocity
from src.engine.aggregator import aggregate

def test_descent_velocity_panic():
    # 10% drop in 10 days
    data = MarketData(
        date=date(2025, 1, 1),
        price=90.0,
        ma200=100.0,
        high_52w=100.0,
        vix=20.0,
        fear_greed=50,
        adv_dec_ratio=0.5,
        pct_above_50d=0.5,
        days_since_52w_high=10
    )
    velocity, days = calculate_descent_velocity(data)
    assert velocity == "PANIC"
    assert days == 10

def test_descent_velocity_grind():
    # 10% drop in 50 days
    data = MarketData(
        date=date(2025, 1, 1),
        price=90.0,
        ma200=100.0,
        high_52w=100.0,
        vix=20.0,
        fear_greed=50,
        adv_dec_ratio=0.5,
        pct_above_50d=0.5,
        days_since_52w_high=50
    )
    velocity, days = calculate_descent_velocity(data)
    assert velocity == "GRIND"
    assert days == 50

def test_greedy_signal_trigger():
    # Extreme greed + Overextended
    t1 = Tier1Result(
        score=5,
        drawdown_52w=SignalDetail("dd", 0.0, 0, (0.05, 0.10), False, False),
        ma200_deviation=SignalDetail("ma", 0.0, 0, (0.02, 0.05), False, False),
        vix=SignalDetail("vix", 15.0, 0, (20, 30), False, False),
        fear_greed=SignalDetail("fg", 85, 0, (30, 20), False, False),
        breadth=SignalDetail("b", 0.7, 0, (0.4, 0.3), False, False),
        market_regime="QUIET"
    )
    t2 = Tier2Result(0, None, None, None, False, False, True, True, "bs", 0, 0)
    
    # price=110, ma50=100 (10% overextended)
    result = aggregate(date(2025, 1, 1), 110.0, t1, t2, ma50=100.0)
    assert result.signal == Signal.GREEDY
