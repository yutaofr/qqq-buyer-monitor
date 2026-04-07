import logging
from typing import Any

logger = logging.getLogger(__name__)

class ResonanceDetector:
    """
    V14.5 QLD Triple-Resonance Detector Engine.
    Orchestrates tactical signals based on:
    1. Risk Clearance (Mud Tractor + Sidecar + VIX Term Structure)
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
        vix_ratio: float
    ) -> dict[str, Any]:
        """
        Evaluate the current market state for resonance actions.
        """
        mid_prob = posteriors.get("MID_CYCLE", 0.0)
        late_prob = posteriors.get("LATE_CYCLE", 0.0)

        mid_dynamics = dynamics.get("MID_CYCLE", {})
        mid_delta = mid_dynamics.get("delta_1d", 0.0)
        mid_accel = mid_dynamics.get("acceleration_1d", 0.0)

        late_dynamics = dynamics.get("LATE_CYCLE", {})
        late_delta = late_dynamics.get("delta_1d", 0.0)

        # 1. SELL Conditions (Panic/Risk/Entropy/Late Cycle)
        # Risk Spike
        risk_spike = tractor_prob > 0.15 or sidecar_prob > 0.10
        # Entropy Loss
        entropy_spike = effective_entropy > 0.75
        # Late Cycle Overwhelm
        late_overwhelm = late_prob > 0.40 and late_delta > 0

        if risk_spike or entropy_spike or late_overwhelm:
            return {
                "action": "SELL_QLD",
                "confidence": max(tractor_prob, sidecar_prob, late_prob),
                "reason": f"RiskSpike={risk_spike}, EntropySpike={entropy_spike}, LateOverwhelm={late_overwhelm}"
            }

        # 2. BUY Conditions (Resonance)
        # Risk Clearance
        risk_clear = (tractor_prob + sidecar_prob < 0.05) and (vix_ratio < 1.0)
        # Entropy Collapse
        entropy_collapse = (effective_entropy < 0.65) and (high_entropy_streak == 0)
        # Mid-Cycle Dominance
        mid_dominance = (mid_prob > 0.40) and (mid_prob > late_prob) and (mid_delta > 0 or mid_accel > 0)

        if risk_clear and entropy_collapse and mid_dominance:
            # Confidence is scaled by how deep we are in Mid-Cycle and how low the entropy is
            # Base confidence starts at 0.7 if thresholds are met.
            confidence = 0.7 + (mid_prob - 0.4) + (0.65 - effective_entropy)
            return {
                "action": "BUY_QLD",
                "confidence": min(float(confidence), 1.0),
                "reason": "Triple-Resonance: RiskClear + EntropyCollapse + MidDominance"
            }

        # 3. Default to HOLD
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reason": "Noise: No resonance detected"
        }
