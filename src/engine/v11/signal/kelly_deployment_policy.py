"""
True Kelly Deployment Policy implementation (v1.0)
Translates Kelly fraction into deployment state with inertia.
"""

from typing import Any

from src.engine.v11.core.kelly_criterion import (
    compute_kelly_fraction,
    kelly_fraction_to_deployment_state,
)
from src.models.deployment import deployment_multiplier_for_state


class KellyDeploymentPolicy:
    """True Kelly deployment policy with Bayesian evidence tracking."""

    def __init__(
        self,
        *,
        initial_state: str = "DEPLOY_BASE",
        evidence: float = 0.0,
        kelly_scale: float = 0.5,
        erp_weight: float = 0.4,
        regime_sharpes: dict[str, float] | None = None,
    ):
        self.current_state = initial_state
        self.evidence = float(evidence)
        self.kelly_scale = kelly_scale
        self.erp_weight = erp_weight
        self.regime_sharpes = regime_sharpes or {
            "MID_CYCLE": 2.0,
            "LATE_CYCLE": 0.2,
            "BUST": -0.8,
            "RECOVERY": 1.2,
        }
        self._prev_kelly_fraction = 0.0

    def decide(
        self,
        *,
        posteriors: dict[str, float],
        entropy: float,
        readiness_score: float,
        value_score: float,
        mid_delta: float = 0.0,
    ) -> dict[str, Any]:

        erp_percentile = float(value_score)

        kelly_fraction = compute_kelly_fraction(
            posteriors=posteriors,
            regime_sharpes=self.regime_sharpes,
            entropy=entropy,
            erp_percentile=erp_percentile,
            kelly_scale=self.kelly_scale,
            erp_weight=self.erp_weight,
        )

        raw_state = kelly_fraction_to_deployment_state(kelly_fraction)
        barrier = self._entropy_barrier(entropy, n_states=4)

        switched = False

        if raw_state != self.current_state:
            self.evidence += abs(kelly_fraction - self._prev_kelly_fraction)
            if self.evidence >= barrier:
                self.current_state = raw_state
                self.evidence = 0.0
                switched = True
        else:
            self.evidence = 0.0
            switched = False

        self._prev_kelly_fraction = kelly_fraction

        return {
            "deployment_state": self.current_state,
            "raw_state": raw_state,
            "deployment_multiplier": deployment_multiplier_for_state(self.current_state),
            "readiness_score": float(readiness_score),
            "value_score": float(value_score),
            "action_required": switched,
            "reason": "PACE_SWITCH" if switched else "PACE_HOLD",
            "scores": {"kelly_fraction": kelly_fraction},
            "barrier": barrier,
            "evidence": self.evidence,
            "kelly_fraction": kelly_fraction,
        }

    @staticmethod
    def _entropy_barrier(entropy: float, n_states: int) -> float:
        h = min(0.999, max(0.0, float(entropy)))
        states = max(1, int(n_states))
        return (h / max(1e-6, 1.0 - h)) / states
