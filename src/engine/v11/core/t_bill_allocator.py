"""v11 Core: Synthetic Liquidity Allocator for Bucket B.
Bypasses T+1 settlement and eliminates cash drag using T-Bills and NQ Futures.
"""

from __future__ import annotations


class SyntheticLiquidityAllocator:
    """
    绕过 T+1 结算黑洞：使用国债抵押直击 NQ/MNQ 期货的合成多头引擎。
    """

    def __init__(self, nq_multiplier: int = 20, margin_buffer: float = 0.30):
        # MNQ multiplier is 2, NQ is 20. We use NQ as default for institution-grade.
        self.nq_multiplier = nq_multiplier
        # 预留 30% 抵押品应对 VIX 飙升时的追加保证金 (Margin Call)
        self.margin_buffer = margin_buffer

    def calculate_futures_order(
        self,
        t_bill_value: float,
        target_notional_exposure: float,
        nq_current_price: float,
        current_vix: float,
        base_im_per_contract: float = 18000.0,  # Approximate NQ Initial Margin
    ) -> dict:
        """
        在 Kill-Switch 触发瞬间，计算能直接打出的期货子弹。
        """
        # 1. 模拟清算所绞肉机 (Clearing House Haircut Dynamic)
        # VIX 越高，国债折价率越高，保证金要求也越高
        dynamic_haircut = 0.05 if current_vix > 60 else 0.01
        dynamic_im = base_im_per_contract * (1 + (current_vix / 100.0))

        usable_collateral = t_bill_value * (1 - dynamic_haircut)

        # 2. 计算合成目标现货敞口所需的合约数
        notional_per_contract = nq_current_price * self.nq_multiplier
        if notional_per_contract <= 0:
            return {"action": "HOLD", "contracts": 0, "reason": "Invalid NQ Price"}

        raw_contracts = target_notional_exposure / notional_per_contract
        optimal_contracts = int(raw_contracts)  # 向下取整，绝不透支

        # 3. 生存红线校验 (Margin Safety Check)
        required_margin = optimal_contracts * dynamic_im
        available_margin_for_deployment = usable_collateral * (1 - self.margin_buffer)

        # 如果保证金受限，强制缩减合约数量
        while required_margin > available_margin_for_deployment and optimal_contracts > 0:
            optimal_contracts -= 1
            required_margin = optimal_contracts * dynamic_im

        if optimal_contracts <= 0:
            return {
                "action": "MARGIN_BLOCKED",
                "contracts": 0,
                "margin_locked": 0.0,
                "remaining_collateral": usable_collateral,
                "actual_notional_exposure": 0.0,
            }

        return {
            "action": "BUY_NQ_FUTURES",
            "contracts": optimal_contracts,
            "margin_locked": required_margin,
            "remaining_collateral": usable_collateral - required_margin,
            "actual_notional_exposure": optimal_contracts * notional_per_contract,
        }
