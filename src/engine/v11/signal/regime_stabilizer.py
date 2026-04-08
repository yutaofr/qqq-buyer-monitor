"""Stateful regime stabilizer for v11 probabilistic output."""

from __future__ import annotations

from src.regime_topology import ACTIVE_REGIME_ORDER, canonicalize_regime_name, merge_regime_weights


class RegimeStabilizer:
    """Resist noisy one-day regime flips under high entropy."""

    def __init__(self, *, initial_regime: str | None = None, evidence: float = 0.0):
        self.current_regime = canonicalize_regime_name(initial_regime)
        self.evidence = float(evidence)

    def update(
        self,
        *,
        posteriors: dict[str, float],
        entropy: float,
        release_hint: dict[str, float | str] | None = None,
    ) -> dict[str, object]:
        normalized = merge_regime_weights(
            posteriors,
            regimes=ACTIVE_REGIME_ORDER,
            include_zeros=False,
            normalize=True,
        )
        raw_regime = (
            max(normalized, key=normalized.get)
            if normalized
            else (self.current_regime or "MID_CYCLE")
        )

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
        barrier = self._entropy_barrier(entropy, len(normalized))
        challenger_regime = raw_regime
        challenger_prob = normalized.get(challenger_regime, 0.0)
        switched = False
        release_override = self._resolve_release_candidate(
            normalized=normalized,
            current_regime=self.current_regime,
            entropy=entropy,
            release_hint=release_hint,
        )
        if release_override is not None:
            challenger_regime = release_override["candidate_regime"]
            challenger_prob = float(normalized.get(challenger_regime, 0.0))
            barrier *= float(release_override["barrier_scale"])

        if challenger_regime != self.current_regime:
            self.evidence += max(0.0, challenger_prob - current_prob) + (
                float(release_override["bonus"]) if release_override is not None else 0.0
            )
            if self.evidence >= barrier:
                self.current_regime = challenger_regime
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

    @staticmethod
    def _resolve_release_candidate(
        *,
        normalized: dict[str, float],
        current_regime: str | None,
        entropy: float,
        release_hint: dict[str, float | str] | None,
    ) -> dict[str, float | str] | None:
        if current_regime not in {"BUST", "LATE_CYCLE"} or not release_hint:
            return None
        if str(release_hint.get("topology_regime")) != "RECOVERY":
            return None

        recovery_prob = float(normalized.get("RECOVERY", 0.0))
        current_prob = float(normalized.get(current_regime, 0.0))
        if recovery_prob < 0.20 or recovery_prob < 0.55 * max(1e-6, current_prob):
            return None

        recovery_impulse = float(release_hint.get("recovery_impulse", 0.0) or 0.0)
        damage_memory = float(release_hint.get("damage_memory", 0.0) or 0.0)
        bust_pressure = float(release_hint.get("bust_pressure", 0.0) or 0.0)
        bearish_divergence = float(release_hint.get("bearish_divergence", 0.0) or 0.0)
        transition_intensity = float(release_hint.get("transition_intensity", 0.0) or 0.0)

        release_score = (
            0.24 * recovery_impulse
            + 0.26 * damage_memory
            + 0.18 * transition_intensity
            + 0.32 * recovery_prob
            - 0.22 * bust_pressure
            - 0.12 * bearish_divergence
        )
        if release_score < 0.32:
            return None

        bonus = max(0.0, release_score - 0.30)
        entropy_scale = max(0.30, 0.60 - (0.30 * min(1.0, max(0.0, entropy))))
        return {
            "candidate_regime": "RECOVERY",
            "barrier_scale": entropy_scale,
            "bonus": bonus,
        }
