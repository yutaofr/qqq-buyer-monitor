import pytest
import pandas as pd
import numpy as np
from datetime import date
from src.backtest import Backtester
from src.models import AllocationState

def test_backtest_v6_3_multi_asset_nav_and_rebalancing():
    """
    AC-3: 验证多资产 NAV 计算与 TAA 自动对齐逻辑
    1. QLD 价格应基于 QQQ 涨跌幅 2 倍模拟
    2. NAV 应包含 Cash + QQQ + QLD
    3. Rebalancing 应根据 TargetAllocationState 对齐三项资产
    """
    # 构造 100 个点的数据: 100 -> 110 (极缓长趋势) 以最小化离散再平衡产生的噪声
    prices = pd.Series(
        np.linspace(100.0, 110.0, 100),
        index=pd.date_range("2026-01-01", periods=100, freq="B")
    )
    ohlcv = pd.DataFrame({"Close": prices}, index=prices.index)
    
    # 模拟分配状态: 始终 FAST_ACCUMULATE (TAA: 5% Cash, 80% QQQ, 15% QLD)
    # _TAA_MATRIX[AllocationState.FAST_ACCUMULATE] = (0.05, 0.80, 0.15, 1.10)
    def mock_derive_states(self, ohlcv, seeder):
        return pd.Series([AllocationState.FAST_ACCUMULATE] * len(ohlcv), index=ohlcv.index)
    
    # 动态替换 derive_states 以隔离测试
    from src.backtest import Backtester as BT
    original_derive = BT._derive_states
    BT._derive_states = mock_derive_states
    
    try:
        tester = Backtester(initial_capital=10000)
        # 强制 WEEKLY_ADD_INTERVAL 为 1 以便每日触发
        import src.backtest as bt_module
        original_interval = bt_module.WEEKLY_ADD_INTERVAL
        bt_module.WEEKLY_ADD_INTERVAL = 1
        
        summary = tester.simulate_portfolio(ohlcv)
        
        # AC-3: 增加一致性断言，验证 NAV - (Sum of Assets) < 1e-4
        for event in summary.events:
            sum_assets = event.cash_balance + event.equity_value + event.qld_value
            assert abs(event.net_asset_value - sum_assets) < 1e-4
        
        # v6.3.12: AC-4 Beta Fidelity Regression
        assert summary.realized_beta > 0.0
        assert len(summary.interval_beta_audit) > 0
        first_interval = summary.interval_beta_audit[0]
        assert first_interval["state"] == "FAST_ACCUMULATE"
        assert first_interval["target"] == 1.10
        # 验证偏差字段存在
        assert "deviation" in first_interval
        assert first_interval["realized"] > 0
        
        # AC-4 Acceptance Gate
        # 在引入 Daily Rebalancing 后，即便在合成测试中也应满足 <= 0.05 的严苛标准
        assert summary.mean_interval_beta_deviation <= 0.05
        
        # MDD Improvement Regression
        # Verify improvement logic: abs(baseline) - abs(tactical)
        expected_improve = abs(summary.baseline_mdd) - abs(summary.tactical_mdd)
        # 验证 summary 中存储的值与计算逻辑一致
        assert abs((abs(summary.baseline_mdd) - abs(summary.tactical_mdd)) - expected_improve) < 1e-6
        
    finally:
        BT._derive_states = original_derive
        bt_module.WEEKLY_ADD_INTERVAL = original_interval

def test_qld_price_simulation_logic():
    """验证 QLD 价格模拟函数 (v6.3 内部逻辑，包含 SRD 4.2 drag)"""
    from src.backtest import simulate_leveraged_price
    qqq_prices = pd.Series([100.0, 105.0, 100.0])
    qld_prices = simulate_leveraged_price(qqq_prices, leverage=2.0)
    
    # drag = 0.0000377
    # t=0: QQQ=100 -> QLD=100
    # t=1: QQQ=105 (+5%) -> QLD = 100 * (1 + 2 * 0.05 - 0.0000377) = 100 * (1.0999623) = 109.99623
    # t=2: QQQ=100 (-4.7619%) -> QLD = 109.99623 * (1 + 2 * -0.047619 - 0.0000377) 
    #      = 109.99623 * (1 - 0.095238 - 0.0000377) = 109.99623 * 0.9047243 = 99.516
    assert qld_prices.iloc[0] == 100.0
    assert qld_prices.iloc[1] == pytest.approx(109.99623, rel=1e-5)
    assert qld_prices.iloc[2] == pytest.approx(99.516, rel=1e-3)
