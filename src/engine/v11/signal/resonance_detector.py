import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResonanceDetector:
    """
    V14.5 QLD Triple-Resonance Detector Engine.
    Orchestrates tactical signals based on:
    1. Risk Clearance (Mud Tractor + Sidecar Probability)
    2. Entropy Collapse (Information Precision)
    3. Regime Dominance (Bayesian Mid-Cycle Momentum)
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        posteriors: dict[str, float],
        dynamics: dict[str, Any],
        effective_entropy: float,
        high_entropy_streak: int,
        tractor_prob: float,
        sidecar_prob: float,
        previous_effective_entropy: float | None = None,
        risk_context: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate the current market state for resonance actions.
        """
        mid_prob = posteriors.get("MID_CYCLE", 0.0)
        late_prob = posteriors.get("LATE_CYCLE", 0.0)
        bust_prob = posteriors.get("BUST", 0.0)

        mid_dynamics = dynamics.get("MID_CYCLE", {})
        mid_delta = mid_dynamics.get("delta_1d", 0.0)
        mid_accel = mid_dynamics.get("acceleration_1d", 0.0)

        late_dynamics = dynamics.get("LATE_CYCLE", {})
        late_delta = late_dynamics.get("delta_1d", 0.0)

        bust_dynamics = dynamics.get("BUST", {})
        bust_delta = bust_dynamics.get("delta_1d", 0.0)

        risk_context = risk_context or {}
        prev_tractor = float(risk_context.get("tractor_prev", tractor_prob))
        prev_sidecar = float(risk_context.get("sidecar_prev", sidecar_prob))
        combined_risk = float(tractor_prob) + float(sidecar_prob)
        previous_combined_risk = prev_tractor + prev_sidecar
        risk_delta = combined_risk - previous_combined_risk
        entropy_delta = (
            float(effective_entropy) - float(previous_effective_entropy)
            if previous_effective_entropy is not None
            else 0.0
        )

        risk_spike = tractor_prob >= 0.15 or sidecar_prob >= 0.10
        risk_rebound = (
            previous_combined_risk <= 0.10
            and combined_risk >= 0.16
            and risk_delta >= 0.08
        )
        late_overwhelm = (
            late_prob >= 0.45
            and late_delta > 0.03
            and (late_prob - mid_prob) >= 0.12
        )
        entropy_fog = (
            effective_entropy >= 0.78
            or (previous_effective_entropy is not None and effective_entropy >= 0.72 and entropy_delta >= 0.08)
            or (high_entropy_streak >= 5 and effective_entropy >= 0.75)
        )

        if risk_spike or risk_rebound:
            return self._signal(
                action="SELL_QLD",
                confidence=max(tractor_prob, sidecar_prob, combined_risk),
                reason_code="LEFT_TAIL_RISK_SPIKE",
                reason="Left-tail risk spike detected.",
                prompt="左尾风險重新抬頭，立即降級 QLD，退守 QQQ。",
            )
        if entropy_fog:
            return self._signal(
                action="SELL_QLD",
                confidence=max(effective_entropy, 0.8),
                reason_code="ENTROPY_FOG",
                reason="System entropy is rebuilding into defensive fog.",
                prompt="紫色迷霧重生，系統視野失真，應主動卸下 QLD 槓桿。",
            )
        if late_overwhelm:
            return self._signal(
                action="SELL_QLD",
                confidence=max(late_prob, 0.75),
                reason_code="LATE_CYCLE_OVERWHELM",
                reason="Late-cycle probability is swallowing mid-cycle leadership.",
                prompt="黃線開始蠶食藍線，週期進入降槓桿區，應把 QLD 切回 QQQ。",
            )

        risk_clear = combined_risk <= 0.18 and tractor_prob <= 0.10 and sidecar_prob <= 0.10
        risk_relief = (
            risk_delta <= -0.02
            or (
                previous_combined_risk >= 0.30
                and combined_risk <= 0.18
                and risk_delta <= -0.12
            )
        )
        entropy_waterfall = (
            previous_effective_entropy is not None
            and previous_effective_entropy >= 0.55
            and effective_entropy <= 0.35
            and entropy_delta <= -0.12
            and high_entropy_streak == 0
        )
        mid_cycle_surge = (
            mid_prob >= 0.45
            and mid_prob > late_prob
            and mid_delta >= 0.08
            and (mid_accel > 0.0 or bust_delta <= -0.05)
        )
        bust_retreat = bust_prob <= 0.18 or bust_delta <= -0.05

        if risk_clear and risk_relief and entropy_waterfall and mid_cycle_surge and bust_retreat:
            confidence = min(
                1.0,
                0.78
                + max(0.0, mid_prob - 0.45)
                + max(0.0, 0.18 - combined_risk)
                + max(0.0, -entropy_delta * 0.25),
            )
            return self._signal(
                action="BUY_QLD",
                confidence=confidence,
                reason_code="TRIPLE_RESONANCE_BUY",
                reason="Risk cliff + entropy waterfall + MID_CYCLE resurgence.",
                prompt="三重共振成立，可切入 QLD：橙青退潮、紫線坍塌、藍色 MID_CYCLE 強勢回歸。",
            )

        return self._signal(
            action="HOLD",
            confidence=0.0,
            reason_code="NO_RESONANCE",
            reason="Noise: No resonance detected",
            prompt="暫無三重共振，維持現有節奏。",
        )

    @staticmethod
    def _signal(
        *,
        action: str,
        confidence: float,
        reason_code: str,
        reason: str,
        prompt: str,
    ) -> dict[str, Any]:
        return {
            "action": action,
            "confidence": min(max(float(confidence), 0.0), 1.0),
            "reason_code": reason_code,
            "reason": reason,
            "prompt": prompt,
        }
