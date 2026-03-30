import pytest

from src.engine.v11.signal.hysteresis_beta_mapper import HysteresisBetaMapper


@pytest.fixture
def base_betas():
    # v11.5 Standard Base Betas
    return {
        "BUST": 0.5,
        "CAPITULATION": 1.05,
        "RECOVERY": 1.1,
        "LATE_CYCLE": 0.8,
        "MID_CYCLE": 1.0
    }

def test_probabilistic_beta_expectation(base_betas):
    """验证从后验概率计算出期望 Target Beta"""
    mapper = HysteresisBetaMapper(base_betas)

    # 极度确定是 BUST
    bust_probs = {"BUST": 1.0, "MID_CYCLE": 0.0, "CAPITULATION": 0.0, "RECOVERY": 0.0, "LATE_CYCLE": 0.0}
    assert mapper.calculate_expectation(bust_probs) == 0.5

    # 平分秋色 (50% MID, 50% BUST)
    mixed_probs = {"BUST": 0.5, "MID_CYCLE": 0.5, "CAPITULATION": 0.0, "RECOVERY": 0.0, "LATE_CYCLE": 0.0}
    assert mapper.calculate_expectation(mixed_probs) == 0.75

def test_hysteresis_delta_deadband(base_betas):
    """验证 Delta 阈值能够拦截噪声引起的微调仓"""
    mapper = HysteresisBetaMapper(base_betas, delta_threshold=0.1)
    mapper.current_beta = 1.0

    # 微小变动 (1.0 -> 1.05) 应当被拦截
    assert mapper.apply_hysteresis(1.05) == 1.0

    # 实质变动 (1.0 -> 1.15 > 0.1) 应当触发
    assert mapper.apply_hysteresis(1.15) == 1.15

def test_settlement_t_plus_lock(base_betas):
    """验证 T+1 物理结算锁能够强行冷却调仓回路"""
    mapper = HysteresisBetaMapper(base_betas)
    mapper.current_beta = 1.0

    # 1. 发生调仓 (1.0 -> 0.5)
    assert mapper.apply_hysteresis(0.5) == 0.5
    assert mapper.cooldown_remaining == 1 # 进入 T+1 冷却

    # 2. 第二天立刻想调回去 (0.5 -> 1.0) 应当被物理锁拦截
    assert mapper.apply_hysteresis(1.0) == 0.5

    # 3. 冷却天数减少后，允许再次调仓
    mapper.tick_cooldown()
    assert mapper.cooldown_remaining == 0
    assert mapper.apply_hysteresis(1.0) == 1.0
