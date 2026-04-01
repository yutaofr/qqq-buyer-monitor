"""Stateful regime stabilizer for v11 probabilistic output."""
from __future__ import annotations

from src.regime_topology import ACTIVE_REGIME_ORDER, canonicalize_regime_name, merge_regime_weights


class RegimeStabilizer:
    """Resist noisy one-day regime flips under high entropy."""

    def __init__(self, *, initial_regime: str | None = None, evidence: float = 0.0):
        self.current_regime = canonicalize_regime_name(initial_regime)
        self.evidence = float(evidence)

    def update(self, *, posteriors: dict[str, float], entropy: float) -> dict[str, object]:
        normalized = merge_regime_weights(
            posteriors,
            regimes=ACTIVE_REGIME_ORDER,
            include_zeros=False,
            normalize=True,
        )
        raw_regime = max(normalized, key=normalized.get) if normalized else (self.current_regime or "MID_CYCLE")

        if self.current_regime is None:
            self.current_regime = raw_regime
            self.evidence = 0.0
            return {
                "raw_regime": raw_regime,
                "stable_regime": self.current_regime,
                "switched": False,
                "barrier": 0.0,
                "evidence": self.evidence,
            }

        current_prob = normalized.get(self.current_regime, 0.0)
        challenger_prob = normalized.get(raw_regime, 0.0)
        barrier = self._entropy_barrier(entropy, len(normalized))
        switched = False

        if raw_regime != self.current_regime:
            self.evidence += max(0.0, challenger_prob - current_prob)
            if self.evidence >= barrier:
                self.current_regime = raw_regime
                self.evidence = 0.0
                switched = True
        else:
            self.evidence = 0.0

        return {
            "raw_regime": raw_regime,
            "stable_regime": self.current_regime,
            "switched": switched,
            "barrier": barrier,
            "evidence": self.evidence,
        }

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
