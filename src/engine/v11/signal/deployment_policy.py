"""Independent v11 deployment policy for incremental cash pacing."""
from __future__ import annotations

from src.models.deployment import DeploymentState, deployment_multiplier_for_state
from src.regime_topology import ACTIVE_REGIME_ORDER, merge_regime_weights


class ProbabilisticDeploymentPolicy:
    """Translate probabilistic opportunity into an independent deployment surface."""

    def __init__(self, *, initial_state: str = "DEPLOY_BASE", evidence: float = 0.0):
        self.current_state = initial_state
        self.evidence = float(evidence)

    def decide(
        self,
        *,
        posteriors: dict[str, float],
        entropy: float,
        readiness_score: float,
        value_score: float,
    ) -> dict[str, object]:
        scores = self._score_states(
            posteriors=posteriors,
            entropy=entropy,
            readiness_score=readiness_score,
            value_score=value_score,
        )
        raw_state = max(scores, key=scores.get)
        barrier = self._entropy_barrier(entropy, len(scores))
        switched = False

        if raw_state != self.current_state:
            # v12.2 AC-5 Smart Priming:
            # If we have no accumulated evidence (cold start or post-reset),
            # we align immediately to avoid pacing lag.
            if self.evidence <= 0.0:
                self.current_state = raw_state
                self.evidence = 0.0
                switched = True
            else:
                self.evidence += max(0.0, scores[raw_state] - scores.get(self.current_state, 0.0))
                if self.evidence >= barrier:
                    self.current_state = raw_state
                    self.evidence = 0.0
                    switched = True
        else:
            self.evidence = 0.0

        return {
            "deployment_state": self.current_state,
            "raw_state": raw_state,
            "deployment_multiplier": deployment_multiplier_for_state(self.current_state),
            "readiness_score": float(readiness_score),
            "value_score": float(value_score),
            "action_required": switched,
            "reason": "PACE_SWITCH" if switched else "PACE_HOLD",
            "scores": scores,
            "barrier": barrier,
            "evidence": self.evidence,
        }

    @staticmethod
    def _score_states(
        *,
        posteriors: dict[str, float],
        entropy: float,
        readiness_score: float,
        value_score: float,
    ) -> dict[str, float]:
        p = merge_regime_weights(
            posteriors,
            regimes=ACTIVE_REGIME_ORDER,
            include_zeros=True,
            normalize=True,
        )
        bust = p.get("BUST", 0.0)
        late = p.get("LATE_CYCLE", 0.0)
        mid = p.get("MID_CYCLE", 0.0)
        recovery = p.get("RECOVERY", 0.0)

        h = min(1.0, max(0.0, float(entropy)))
        readiness = min(1.0, max(0.0, float(readiness_score)))
        value = min(1.0, max(0.0, float(value_score)))
        conviction = 1.0 - h
        reversal = recovery

        raw_scores = {
            DeploymentState.DEPLOY_PAUSE.value: bust * (1.0 - readiness + h) + late * h,
            DeploymentState.DEPLOY_SLOW.value: late * (1.0 + h) + bust * (1.0 - readiness),
            DeploymentState.DEPLOY_BASE.value: mid * (1.0 + value) + conviction * max(0.0, 1.0 - bust - late),
            DeploymentState.DEPLOY_FAST.value: reversal * (readiness + value + conviction),
        }
        return ProbabilisticDeploymentPolicy._normalize(raw_scores)

    @staticmethod
    def _entropy_barrier(entropy: float, n_states: int) -> float:
        h = min(0.999, max(0.0, float(entropy)))
        states = max(1, int(n_states))
        return (h / max(1e-6, 1.0 - h)) / states

    @staticmethod
    def _normalize(weights: dict[str, float]) -> dict[str, float]:
        total = float(sum(max(0.0, float(value)) for value in weights.values()))
        if total <= 0.0:
            n = max(1, len(weights))
            return {str(key): 1.0 / n for key in weights}
        return {str(key): max(0.0, float(value)) / total for key, value in weights.items()}
