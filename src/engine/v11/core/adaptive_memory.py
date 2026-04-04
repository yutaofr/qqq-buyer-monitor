"""v11 Core: Exogenous Memory Operator.
Decouples cognitive half-life from VIX and anchors it to Credit Spread OAS ROC.
Implements the 'Malignant Expansion' decay function.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class ExogenousMemoryOperator:
    """
    v11 终极认知中枢：基于外生信贷压力的自适应半衰期引擎。
    """

    def __init__(self, base_half_life: float = 10.0, kappa: float = 5.0):
        self.base_half_life = base_half_life
        self.kappa = kappa  # 惩罚系数：决定信贷危机时的“遗忘暴力程度”

    def compute_adaptive_lambda(self, credit_spread_series: pd.Series) -> pd.Series:
        """
        输入: 信用利差历史序列 (ICE BofA US High Yield OAS)
        输出: 每日动态半衰期序列 (单位: 年)
        """
        # 计算 20 日基准线以过滤日常噪音 (SSoT: EMA 20)
        baseline_spread = credit_spread_series.ewm(span=20, adjust=False).mean()

        # 计算信贷恶化动量 (ROC): (S - EMA)/EMA
        # 仅关注恶化方向 (max(0, ROC))
        spread_roc = (credit_spread_series - baseline_spread) / baseline_spread
        malignant_expansion = np.maximum(0, spread_roc)

        # 指数级记忆衰减算子: lambda = base * exp(-kappa * ROC)
        dynamic_lambda = self.base_half_life * np.exp(-self.kappa * malignant_expansion)

        # 设定物理底线：半衰期不能低于 0.5 年，防止模型完全退化为白噪声
        return np.maximum(dynamic_lambda, 0.5)

    def get_weighted_rank(
        self, value_series: pd.Series, lambda_series: pd.Series, window: int = 252 * 20
    ) -> pd.Series:
        """
        利用动态半衰期计算加权分位数排名。
        """

        def _weighted_pct(x):
            if len(x) < 1:
                return np.nan
            n = len(x)
            current_hl = float(lambda_series.reindex(x.index).iloc[-1]) * 252
            weights = np.exp(np.log(0.5) / current_hl * np.arange(n)[::-1])
            current_val = x.iloc[-1]
            if pd.isna(current_val):
                return np.nan

            # 对有效数据进行加权
            valid_mask = ~np.isnan(x)
            if not np.any(valid_mask):
                return np.nan

            return np.sum(weights[valid_mask & (x < current_val)]) / np.sum(weights[valid_mask])

        return value_series.rolling(window, min_periods=1).apply(_weighted_pct, raw=False)
