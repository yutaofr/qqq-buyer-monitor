import pytest
import os
from src.models import CurrentPortfolioState, TargetAllocationState, SignalResult, AllocationState

def test_target_allocation_state_model():
    """验证目标配置模型的数据结构"""
    target = TargetAllocationState(
        target_cash_pct=0.1,
        target_qqq_pct=0.9,
        target_qld_pct=0.0,
        target_beta=0.9
    )
    assert target.target_cash_pct == 0.1
    assert target.target_beta == 0.9

def test_current_portfolio_normalization_normal(monkeypatch):
    """验证正常输入的归一化逻辑"""
    envs = {
        "CASH_LEVEL": "10",
        "QQQ_LEVEL": "30",
        "QLD_LEVEL": "10"
    }
    for k, v in envs.items():
        monkeypatch.setenv(k, v)
    
    portfolio = CurrentPortfolioState.from_env()
    # 总和 50, 归一化后应为 [0.2, 0.6, 0.2]
    assert portfolio.current_cash_pct == pytest.approx(0.2)
    assert portfolio.qqq_pct == pytest.approx(0.6)
    assert portfolio.qld_pct == pytest.approx(0.2)
    # 有效敞口 = 0.6 + 2 * 0.2 = 1.0
    assert portfolio.gross_exposure_pct == pytest.approx(1.0)

def test_current_portfolio_normalization_safety_fallback(monkeypatch):
    """验证全零输入的防御性降级逻辑 (AC-1)"""
    envs = {"CASH_LEVEL": "0", "QQQ_LEVEL": "0", "QLD_LEVEL": "0"}
    for k, v in envs.items():
        monkeypatch.setenv(k, v)
    
    portfolio = CurrentPortfolioState.from_env()
    # 预期降级为 100% 现金
    assert portfolio.current_cash_pct == 1.0
    assert portfolio.qqq_pct == 0.0
    assert portfolio.qld_pct == 0.0

def test_current_portfolio_negative_clipping(monkeypatch):
    """验证负数输入的自动截断"""
    envs = {"CASH_LEVEL": "10", "QQQ_LEVEL": "-5", "QLD_LEVEL": "0"}
    for k, v in envs.items():
        monkeypatch.setenv(k, v)
    
    portfolio = CurrentPortfolioState.from_env()
    # -5 应被截断为 0, 最终 [1.0, 0.0, 0.0]
    assert portfolio.current_cash_pct == 1.0
    assert portfolio.qqq_pct == 0.0
