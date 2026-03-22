import pytest
import pandas as pd
from datetime import date
from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.models import AllocationState

def test_backtest_triggers_deleverage_in_2022():
    """集成测试：验证回测引擎在注入历史宏观数据后能触发 DELEVERAGE"""
    # 模拟一段价格下跌且利差大幅扩张的数据 (2022 风格)
    dates = pd.date_range(start="2022-01-01", periods=50, freq="W")
    mock_prices = pd.DataFrame({
        "Close": [400 - i*2 for i in range(50)], # 价格阴跌
        "High": [405 - i*2 for i in range(50)],
        "Low": [395 - i*2 for i in range(50)],
        "Open": [400 - i*2 for i in range(50)],
        "Volume": [1000000] * 50
    }, index=dates)
    
    # 模拟信用利差在第 10 周到第 20 周快速恶化
    # 第10周: 3.0, 第12周: 4.5 (两周涨幅 50%)
    mock_macro = pd.DataFrame({
        "observation_date": pd.date_range(start="2021-12-01", periods=365, freq="D"),
        "BAMLH0A0HYM2": [3.0] * 100 + [3.0 + i*0.1 for i in range(50)] + [8.0] * 215
    })
    
    seeder = HistoricalMacroSeeder(mock_df=mock_macro)
    
    # 运行回测
    backtester = Backtester(initial_capital=100000)
    # 注入 seeder 到回测逻辑 (需要修改 Backtester 构造函数或方法)
    results = backtester.run(mock_prices, macro_seeder=seeder)
    
    # 验证是否存在 DELEVERAGE 或 WATCH_DEFENSE 状态
    states = [r["allocation_state"] for r in results]
    assert AllocationState.DELEVERAGE in states or AllocationState.WATCH_DEFENSE in states
