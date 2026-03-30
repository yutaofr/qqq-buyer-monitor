"""v11 Allocator: Dynamic Deleverager for Bucket A.
Implements the 'Active Bleeding' mechanism to raise free cash before the crisis peaks.
"""
from __future__ import annotations
import numpy as np

class BayesianDeleverager:
    """
    根据危机概率提前释放流动性，防止在极高波动率下与券商 MMR 硬刚。
    """
    def __init__(self, min_exposure: float = 0.20, gamma: float = 2.0):
        self.min_exposure = min_exposure
        self.gamma = gamma 

    def compute_safe_exposure(self, p_bust: float) -> float:
        """
        基于 P(BUST) 计算允许的最大现货敞口比例。
        """
        # 非线性惩罚项
        reduction = p_bust ** self.gamma
        target_exposure = 1.0 - reduction
        return max(self.min_exposure, target_exposure)

    def execute_deleveraging(self, current_a_value: float, p_bust: float) -> float:
        """
        返回应当立即抛售以换取 Free Cash 的现货金额。
        """
        target_ratio = self.compute_safe_exposure(p_bust)
        target_value = current_a_value * target_ratio
        
        cash_freed = current_a_value - target_value
        return max(0.0, cash_freed)
