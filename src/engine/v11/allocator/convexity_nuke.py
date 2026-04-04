"""v11 Allocator: Convexity Nuke Engine for Bucket B.
Converts monthly insurance premiums into infinite liquidity during crises.
"""

from __future__ import annotations

import numpy as np


class ConvexityEngine:
    """
    将确定性的微小损耗（200bps/年）转化为极端环境下的核弹级现金。
    """

    def __init__(self, premium_budget_bps: int = 200, kappa: float = 12.0):
        self.allocation_ratio = premium_budget_bps / 10000.0
        self.kappa = kappa  # 波动率敏感度常数

    def simulate_nuke_payout(
        self, total_equity: float, base_vix: float, peak_vix: float, is_kill_switch_triggered: bool
    ) -> float:
        """
        在 Z-Score 解冻发令枪响的那一刻，结算并提取期权残值。
        """
        initial_premium = total_equity * self.allocation_ratio

        # 仅在 Kill-Switch 触发且波动率显著扩张时释放流动性
        if not is_kill_switch_triggered or peak_vix < 45.0:
            return 0.0  # 接受 Theta 损耗

        # 计算凸性爆炸 (Gamma & Vega 近似)
        vix_expansion = max(0.0, peak_vix - base_vix)
        payout_multiplier = np.exp(vix_expansion / self.kappa)

        return initial_premium * payout_multiplier
