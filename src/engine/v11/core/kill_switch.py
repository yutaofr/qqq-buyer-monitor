"""v11 Core: Term Structure Kill-Switch with Dynamic Z-Score.
Weaponized resurrection operator using dynamic volatility breakout bounds.
"""
from __future__ import annotations

import pandas as pd


class DynamicZScoreKillSwitch:
    """
    v11 终极猎杀逆转算子：废除绝对参数，通过自适应 Z-Score 捕捉波动率结构的瞬间断裂。
    """
    def __init__(self, rolling_window: int = 60, z_threshold: float = 2.5):
        self.window = rolling_window
        self.z_threshold = z_threshold # 统计学意义上的尾部突破阈值

    def evaluate_resurrection(
        self,
        is_blackout: bool,
        ts_series: pd.Series,
        vix_1m: pd.Series,
        current_idx: int
    ) -> bool:
        """
        评估是否在流动性黑洞中强行解除冻结并开启猎杀。
        """
        if not is_blackout:
            return False # 仅在 Blackout 状态下具备“苏醒”资格

        if current_idx < self.window + 3:
            return False # 预热窗不足

        # 1. 恐慌一阶导数: VIX 必须正在下降 (确认峰值已过)
        vix_momentum = vix_1m.iloc[current_idx] - vix_1m.iloc[current_idx - 1]
        if vix_momentum >= 0:
            return False

        # 2. 提取历史窗口，计算 3 日修复动量的滚动分布
        start_idx = current_idx - self.window
        history_ts = ts_series.iloc[start_idx : current_idx + 1]

        # 计算 3 日修复动量序列
        momentum_series = history_ts.diff(periods=3).dropna()
        if len(momentum_series) < 10:
            return False

        current_momentum = momentum_series.iloc[-1]

        # 3. 计算 Z-Score
        rolling_mean = momentum_series.mean()
        rolling_std = momentum_series.std()

        if rolling_std == 0:
            return False

        current_z_score = (current_momentum - rolling_mean) / rolling_std

        # 4. 突破统计学红线即触发
        if current_z_score > self.z_threshold:
            # [LOG] 物理触发: Z-Score 结构断裂重连，强制释放 Bucket B
            return True

        return False
