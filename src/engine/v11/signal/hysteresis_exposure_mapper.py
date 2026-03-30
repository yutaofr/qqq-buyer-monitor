"""v11 Signal: Hysteresis Exposure Mapper.
The Dictatorial State Machine. 
Converts continuous probability into discrete, settlement-locked commands.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

class HysteresisExposureMapper:
    """
    v11 终极独裁者：带死区（Deadband）与物理结算锁的状态机。
    """
    def __init__(self, initial_state: str = "QLD", settlement_t_plus: int = 1):
        self.current_state = initial_state
        self.settlement_t_plus = settlement_t_plus
        self.cooldown_days_remaining = 0

    def tick_cooldown(self):
        """每日调用，减少冷却天数"""
        if self.cooldown_days_remaining > 0:
            self.cooldown_days_remaining -= 1

    def get_signal(self, p_bust: float, is_kill_switch_active: bool) -> dict:
        """
        输入核心推断，输出绝对执行指令。
        """
        previous_state = self.current_state
        signal_reason = "CRUISE"

        # 1. 物理层拦截 (Settlement Lock)
        if self.cooldown_days_remaining > 0:
            return self._format_output(
                previous_state, 
                f"SETTLEMENT_LOCKED ({self.cooldown_days_remaining} days left)"
            )

        # 2. 越权接管 (Resurrection)
        if is_kill_switch_active:
            if self.current_state != "QLD":
                self.current_state = "QLD"
                # 猎杀后强制锁仓 30 天，无视洗盘
                self.cooldown_days_remaining = 30 
                signal_reason = "RESURRECTION: Z-SCORE > 3.0. OVERRIDING PROBABILITY."
            return self._format_output(previous_state, signal_reason)

        # 3. 状态机流转 (Deadband Logic)
        if self.current_state == "QLD":
            # 降维防线
            if p_bust > 0.40:
                self.current_state = "QQQ"
                self.cooldown_days_remaining = self.settlement_t_plus
                signal_reason = f"DELEVERAGE: P(BUST) {p_bust:.2f} > 0.40"
                
        elif self.current_state == "QQQ":
            # 终极避险
            if p_bust > 0.75:
                self.current_state = "CASH"
                self.cooldown_days_remaining = self.settlement_t_plus
                signal_reason = f"BLACKOUT: P(BUST) {p_bust:.2f} > 0.75"
            # 警报解除 (需低于 0.20，形成死区)
            elif p_bust < 0.20:
                self.current_state = "QLD"
                self.cooldown_days_remaining = self.settlement_t_plus
                signal_reason = f"RE-LEVERAGE: P(BUST) {p_bust:.2f} < 0.20"
                
        elif self.current_state == "CASH":
            # 现金池复苏极其严苛，主要靠 Kill-Switch 复活
            if p_bust < 0.10:  
                self.current_state = "QQQ"
                self.cooldown_days_remaining = self.settlement_t_plus
                signal_reason = f"CAUTIOUS RE-ENTRY: P(BUST) {p_bust:.2f} < 0.10"

        return self._format_output(previous_state, signal_reason)

    def _format_output(self, previous_state: str, reason: str) -> dict:
        action_required = (self.current_state != previous_state)
        return {
            "target_exposure": self.current_state,
            "action_required": action_required,
            "reason": reason
        }
