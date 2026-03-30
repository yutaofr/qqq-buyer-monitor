"""v11 Allocator: Convexity Manager for Bucket B.
Implements the Non-linear Tail Hedge (The Liquidity Nuke)
using rolling OTM Puts, eliminating static Cash Drag.
"""
from __future__ import annotations

import pandas as pd

from src.engine.v11.core.options_pricer import BlackScholesPricer


class ConvexityManager:
    """
    v11 尾部期权资金池引擎。
    废除持币待购，改用“确定的微小 Theta 损耗”换取“极寒时刻的核爆级变现”。
    """
    def __init__(self, premium_budget_pct: float = 0.005, otm_depth: float = 0.20, dte: int = 180):
        self.pricer = BlackScholesPricer()
        self.premium_budget_pct = premium_budget_pct # 每期预算占 AUM 的比例 (如 0.5%)
        self.otm_depth = otm_depth                   # 虚值深度 (如 20%)
        self.dte = dte                               # 购买时的到期天数

        # Portfolio of active option contracts
        # List of dicts: {"strike", "T_open", "premium_paid", "contracts_held"}
        self.active_puts = []

    def roll_insurance(self, current_aum: float, current_price: float, current_vix: float, current_date: pd.Timestamp):
        """
        在平稳期，按固定预算买入新的 OTM Puts 批次（展期）。
        """
        budget_dollars = current_aum * self.premium_budget_pct

        # 获取合约定价
        contract = self.pricer.simulate_otm_put_roll(
            current_price=current_price,
            current_vix=current_vix,
            otm_pct=self.otm_depth,
            dte_days=self.dte
        )

        if contract["premium"] <= 0.01:
            # 价格过低，可能有数值异常，设一个极小底线
            contract["premium"] = 0.01

        contracts_to_buy = budget_dollars / (contract["premium"] * 100) # 假设乘数为 100

        self.active_puts.append({
            "open_date": current_date,
            "strike": contract["strike"],
            "T_remaining_days": self.dte,
            "premium_paid": contract["premium"],
            "contracts_held": contracts_to_buy
        })

        return budget_dollars # 记录沉没成本 (扣除现金)

    def decay_portfolio(self):
        """
        每日流逝，衰减所有有效合约的剩余天数。清理过期合约。
        """
        active_next = []
        for p in self.active_puts:
            p["T_remaining_days"] -= 1
            if p["T_remaining_days"] > 0:
                active_next.append(p)
        self.active_puts = active_next

    def detonate_nuke(self, current_price: float, current_vix: float) -> float:
        """
        Kill-Switch 触发时，一键市价平仓所有期权，转化为“自由现金”。
        """
        total_cash_generated = 0.0

        for p in self.active_puts:
            current_premium = self.pricer.price_put(
                S=current_price,
                K=p["strike"],
                T=p["T_remaining_days"] / 252.0,
                sigma=current_vix / 100.0
            )
            cash_from_position = current_premium * 100 * p["contracts_held"]
            total_cash_generated += cash_from_position

        # 核弹变现后，清空武器库
        self.active_puts = []
        return total_cash_generated
