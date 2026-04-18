from __future__ import annotations

import math

import numpy as np

from src.engine.v11.stress.config import PersistenceConfig
from src.engine.v11.stress.types import StressComponentScore


def _clip01(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


class PersistenceScorer:
    """Stateful hysteresis score that rewards persistence over single shocks."""

    def __init__(
        self,
        config: PersistenceConfig | None = None,
        *,
        half_life_days: float | None = None,
    ):
        if config is None:
            config = PersistenceConfig(
                half_life_days=float(half_life_days)
                if half_life_days is not None
                else PersistenceConfig().half_life_days
            )
        self.config = config
        self._state = 0.0
        self._precursors: list[float] = []

    def reset(self) -> None:
        self._state = 0.0
        self._precursors = []

    def score(self, *, price_score: float, market_score: float, macro_score: float) -> StressComponentScore:
        precursor = _clip01(0.45 * price_score + 0.35 * market_score + 0.20 * macro_score)
        self._precursors.append(precursor)
        window = max(1, int(self.config.occupancy_window))
        if len(self._precursors) > window:
            self._precursors = self._precursors[-window:]
        occupancy = float(
            np.mean(np.asarray(self._precursors, dtype=float) >= self.config.activation_threshold)
        )
        half_life = (
            self.config.stressed_half_life_days
            if occupancy >= 0.45
            else self.config.half_life_days
        )
        alpha = 1.0 - np.exp(np.log(0.5) / max(1.0, float(half_life)))
        if precursor >= self.config.activation_threshold:
            next_state = ((1.0 - alpha) * self._state) + (alpha * precursor)
        elif precursor <= self.config.release_threshold:
            next_state = max(0.0, self._state - float(self.config.max_daily_release))
            next_state = ((1.0 - alpha) * next_state) + (alpha * precursor)
        else:
            next_state = ((1.0 - alpha) * self._state) + (alpha * precursor * 0.65)
        occupancy_boost = max(0.0, occupancy - 0.35) * 0.45
        self._state = _clip01(max(next_state, occupancy_boost))
        return StressComponentScore(
            kind="S_persist",
            value=self._state,
            subcomponents={
                "precursor": precursor,
                "alpha": float(alpha),
                "occupancy": occupancy,
                "half_life_days": float(half_life),
                "activation_threshold": float(self.config.activation_threshold),
                "release_threshold": float(self.config.release_threshold),
            },
        )
