import pytest
import pandas as pd
from datetime import date
from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.models import AllocationState

def test_backtester_manages_cash_levels():
    """验证回测引擎在极端风险下能动态调整现金水位"""
    # 模拟 20 周暴跌行情 (2022-01 到 2022-05)
    dates = pd.date_range(start="2022-01-01", periods=20, freq="W")
    mock_prices = pd.DataFrame({
        "Close": [400 - i*10 for i in range(20)], 
        "High": [405] * 20, "Low": [195] * 20, "Open": [400] * 20, "Volume": [100] * 20
    }, index=dates)
    
    # 模拟 L3 CASH_FLIGHT 三重共振数据 (从 2022-01-01 开始就是坏数据)
    mock_macro = pd.DataFrame({
        "observation_date": pd.date_range(start="2021-12-01", periods=300, freq="D"),
        "BAMLH0A0HYM2": [3.0] * 30 + [3.0 + i*0.2 for i in range(270)], # 持续恶化
        "liquidity_roc": [-5.0] * 300,
        "is_funding_stressed": [True] * 300
    })
    
    seeder = HistoricalMacroSeeder(mock_df=mock_macro)
    backtester = Backtester(initial_capital=100000)
    
    summary = backtester.simulate_portfolio(mock_prices, macro_seeder=seeder)
    
    assert hasattr(summary, "tactical_mdd")
    # 因为在暴跌一开始就切换到了 CASH_FLIGHT (50% 现金)，回撤应该比 100% 持仓的基准小
    assert summary.tactical_mdd > summary.baseline_mdd 

def test_rebalance_execution():
    """验证 DELEVERAGE 触发时的减仓动作"""
    # 模拟 10 周平盘数据
    dates = pd.date_range("2022-01-01", periods=10, freq="W")
    mock_prices = pd.DataFrame({
        "Close": [400] * 10,
        "High": [400]*10, "Low": [400]*10, "Open": [400]*10, "Volume": [100]*10
    }, index=dates)
    
    # 设置 L2 DELEVERAGE 因子 (利差加速 + 流动性负增长)
    # 确保利差加速在价格回测的每一周都能被 get_features_for_date 检测到
    mock_macro = pd.DataFrame({
        "observation_date": pd.date_range("2021-12-01", periods=200, freq="D"),
        "BAMLH0A0HYM2": [3.0]*30 + [3.0 + i*0.2 for i in range(170)], # 10日涨幅必定 > 15%
        "liquidity_roc": [-3.0]*200
    })
    
    seeder = HistoricalMacroSeeder(mock_df=mock_macro)
    backtester = Backtester(initial_capital=100000)
    
    summary = backtester.simulate_portfolio(mock_prices, macro_seeder=seeder)
    
    states = [e.state for e in summary.events]
    # L2 DELEVERAGE 应该被触发
    assert AllocationState.DELEVERAGE in states
    
    # 验证现金比例是否达到目标 (DELEVERAGE 目标现金为 30%)
    dele_events = [e for e in summary.events if e.state == AllocationState.DELEVERAGE]
    assert len(dele_events) > 0
    # 检查最后一个防御事件的现金比例
    assert dele_events[-1].cash_pct >= 29.0
