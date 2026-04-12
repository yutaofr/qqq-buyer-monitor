"""TDD tests for Kelly PnL backtest computation."""
import pandas as pd
import numpy as np

# This will fail on import until B-02 is implemented
from scripts.kelly_pnl_backtest import _compute_pnl_curve, _compute_performance_metrics

def test_pnl_flat_market_zero_return():
    """价格不变时，净值接近 1.0（仅扣交易成本）"""
    trace = pd.DataFrame({
        "close": [100.0, 100.0, 100.0],
        "multiplier": [1.0, 1.0, 1.0]
    })
    nav = _compute_pnl_curve(trace, "multiplier", base_daily_deploy=0.01, transaction_cost=0.0005)
    
    assert len(nav) == 3
    # 净值几乎无变化，可能第一天因无收益仅有初始成本或无成本，最终接近 1.0
    assert abs(nav.iloc[-1] - 1.0) < 1e-3

def test_pnl_rising_market_generates_positive_nav():
    """价格持续上涨时，净值 > 1.0"""
    trace = pd.DataFrame({
        "close": [100.0, 105.0, 110.25], # 连续上涨 5%
        "multiplier": [1.0, 1.0, 1.0]
    })
    nav = _compute_pnl_curve(trace, "multiplier", base_daily_deploy=1.0, transaction_cost=0.0) 
    assert nav.iloc[-1] > 1.0

def test_pnl_higher_multiplier_amplifies_return():
    """更高的 deployment_multiplier 在上涨市场中产生更高净值"""
    trace = pd.DataFrame({
        "close": [100.0, 105.0, 110.25],
        "mult_low": [0.5, 0.5, 0.5],
        "mult_high": [2.0, 2.0, 2.0]
    })
    nav_low = _compute_pnl_curve(trace, "mult_low", base_daily_deploy=0.5, transaction_cost=0.0)
    nav_high = _compute_pnl_curve(trace, "mult_high", base_daily_deploy=0.5, transaction_cost=0.0)
    
    assert nav_high.iloc[-1] > nav_low.iloc[-1]

def test_performance_metrics_known_steady_return():
    """已知稳定且有波动收益率序列 → 验证 CAGR/Sharpe 计算正确性"""
    # 模拟平均每天 0.04% 收益，包含略微波动
    returns = []
    for i in range(252):
        if i % 2 == 0:
            returns.append(1.0006)
        else:
            returns.append(1.0002)
    returns = np.array(returns)
    nav_series = pd.Series(np.cumprod(np.insert(returns, 0, 1.0)))
    
    metrics = _compute_performance_metrics(nav_series, risk_free_rate=0.0)
    
    # 期望 CAGR ≈ 1.0004^252 - 1 ≈ 10.59%
    assert abs(metrics["cagr"] - 0.1059) < 0.05
    
    # 期望 Sharpe 计算存在，且为正数因为现在有方差了
    assert metrics["sharpe"] > 0

def test_max_drawdown_is_correct():
    """已知先涨后跌序列 → 验证 MDD 计算"""
    # NAV: 1.0 → 1.2 → 0.9 → 1.0
    nav_series = pd.Series([1.0, 1.2, 0.9, 1.0])
    metrics = _compute_performance_metrics(nav_series, risk_free_rate=0.0)
    
    # MDD = (0.9 - 1.2) / 1.2 = -0.25 (即 -25%)
    assert abs(metrics["max_drawdown"] - (-0.25)) < 1e-6
