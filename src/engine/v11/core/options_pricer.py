"""v11 Core: Black-Scholes Options Pricer for Tail Hedge Simulation.
Calculates the premium of deep OTM Puts under varying VIX environments.
"""
from __future__ import annotations

import numpy as np
import scipy.stats as si


class BlackScholesPricer:
    """
    用于模拟 Bucket B 尾部期权池的定价引擎。
    """
    def __init__(self, risk_free_rate: float = 0.045):
        self.r = risk_free_rate

    def price_put(self, S: float, K: float, T: float, sigma: float) -> float:
        """
        计算欧式看跌期权价格。
        S: 标的现价 (Underlying Price)
        K: 行权价 (Strike Price)
        T: 剩余到期时间 (Years to Maturity)
        sigma: 隐含波动率 (Implied Volatility, 比如 VIX/100)
        """
        if T <= 0 or sigma <= 0:
            return max(0.0, K - S)

        d1 = (np.log(S / K) + (self.r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        put_price = (K * np.exp(-self.r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))
        return float(put_price)

    def simulate_otm_put_roll(
        self,
        current_price: float,
        current_vix: float,
        otm_pct: float = 0.20,
        dte_days: int = 180
    ) -> dict:
        """
        模拟在当前市场环境下，开仓购买远期深度虚值 Put 的合约参数。
        """
        strike = current_price * (1.0 - otm_pct)
        T = dte_days / 252.0
        sigma = current_vix / 100.0

        premium = self.price_put(current_price, strike, T, sigma)
        return {
            "strike": strike,
            "T": T,
            "premium": premium
        }
