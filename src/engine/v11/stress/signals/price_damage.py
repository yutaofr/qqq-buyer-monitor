from __future__ import annotations

import math

import numpy as np

from src.engine.v11.stress.config import PriceDamageConfig
from src.engine.v11.stress.types import StressComponentScore


def _clip01(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


def _ramp(value: float, center: float, width: float = 0.30) -> float:
    return _clip01((float(value) - float(center)) / max(1e-6, float(width)) + 0.5)


class PriceDamageScorer:
    """Build S_price from abstract price-topology damage state."""

    def __init__(self, config: PriceDamageConfig | None = None):
        self.config = config or PriceDamageConfig()

    def score(self, topology_state) -> StressComponentScore:
        probabilities = getattr(topology_state, "probabilities", {}) or {}
        bust_prob = _clip01(float(probabilities.get("BUST", 0.0) or 0.0))
        damage = _clip01(float(getattr(topology_state, "damage_memory", 0.0) or 0.0))
        bust_pressure = _clip01(float(getattr(topology_state, "bust_pressure", 0.0) or 0.0))
        transition = _clip01(float(getattr(topology_state, "transition_intensity", 0.0) or 0.0))
        bearish_div = _clip01(float(getattr(topology_state, "bearish_divergence", 0.0) or 0.0))

        structural_damage = _ramp(damage, self.config.damage_center)
        pressure_break = max(bust_prob, _ramp(bust_pressure, self.config.bust_center))
        transition_break = _ramp(transition * max(damage, bust_pressure), self.config.transition_center)
        divergence = _ramp(bearish_div, 0.35)

        score = (
            self.config.damage_weight * structural_damage
            + self.config.bust_weight * pressure_break
            + self.config.transition_weight * transition_break
            + self.config.bearish_divergence_weight * divergence
        )
        return StressComponentScore(
            kind="S_price",
            value=_clip01(score),
            subcomponents={
                "structural_damage": structural_damage,
                "pressure_break": pressure_break,
                "transition_break": transition_break,
                "bearish_divergence": divergence,
                "bust_probability": bust_prob,
            },
        )
