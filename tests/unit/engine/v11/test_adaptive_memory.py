import pytest
import pandas as pd
import numpy as np

from src.engine.v11.core.adaptive_memory import ExogenousMemoryOperator

def test_memory_baseline_stability():
    """验证平稳期半衰期维持基准值"""
    engine = ExogenousMemoryOperator(base_half_life=10.0, kappa=5.0)
    
    # 模拟平稳利差: 400bps 持续 30 天
    spreads = pd.Series([400.0] * 30)
    lambdas = engine.compute_adaptive_lambda(spreads)
    
    # 因为 delta 为 0，exp(0) = 1，结果应为 base_half_life
    assert np.isclose(lambdas.iloc[-1], 10.0)

def test_memory_collapse_on_stress():
    """验证信贷利差暴涨时半衰期非线性坍塌"""
    # 降低 kappa，防止瞬间触底 0.5
    engine = ExogenousMemoryOperator(base_half_life=10.0, kappa=1.0)
    
    # 模拟利差从 400 持续上升: 400 -> 450 -> 500 -> 550 -> 600
    spreads = pd.Series([400.0] * 20 + [450.0, 500.0, 550.0, 600.0, 650.0])
    lambdas = engine.compute_adaptive_lambda(spreads)
    
    # 预期半衰期缩短
    assert lambdas.iloc[-1] < 10.0
    # 验证单调性: 在利差加速扩张期，每一天的记忆都比前一天更短
    assert lambdas.iloc[-1] < lambdas.iloc[-2]
    assert lambdas.iloc[-2] < lambdas.iloc[-3]

def test_physical_memory_floor():
    """验证半衰期存在物理底线 (0.5年)"""
    engine = ExogenousMemoryOperator(base_half_life=10.0, kappa=50.0) # 极高敏感度
    
    # 极端信贷崩盘
    spreads = pd.Series([100.0] * 20 + [2000.0] * 5)
    lambdas = engine.compute_adaptive_lambda(spreads)
    
    assert lambdas.iloc[-1] == 0.5

def test_weighted_rank_近因效应():
    """验证自适应记忆下，近期极端值对排名的主导作用"""
    engine = ExogenousMemoryOperator(base_half_life=10.0, kappa=5.0)
    
    # 构造历史: 100 天低值，最后 1 天极大值
    values = pd.Series([10.0] * 100 + [100.0])
    
    # 情景 1: 长记忆 (10年) -> 100.0 的排名应该接近 1.0
    lambdas_long = pd.Series([10.0] * 101)
    rank_long = engine.get_weighted_rank(values, lambdas_long, window=101).iloc[-1]
    
    # 情景 2: 短记忆 (0.5年) -> 100.0 依然是最大，但因为权重极度向近期倾斜，
    # 如果此时我们将最后一天改成 5.0（比历史低），它的排名应该迅速跌落
    values_drop = pd.Series([10.0] * 100 + [5.0])
    lambdas_short = pd.Series([0.5] * 101)
    rank_short = engine.get_weighted_rank(values_drop, lambdas_short, window=101).iloc[-1]
    
    # 在短记忆下，即使 100 天都是 10.0，最后一天的 5.0 会因为权重巨大而导致排名极低
    assert rank_short < 0.1
