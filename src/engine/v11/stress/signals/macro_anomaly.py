from __future__ import annotations

import math

import numpy as np

from src.engine.v11.stress.config import MacroAnomalyConfig
from src.engine.v11.stress.types import StressComponentScore


def _clip01(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


class MacroAnomalyScorer:
    """Normalize robust Mahalanobis/OOD geometry into S_macro_anom."""

    def __init__(self, config: MacroAnomalyConfig | None = None):
        self.config = config or MacroAnomalyConfig()

    def score(
        self,
        *,
        current_vector: np.ndarray,
        mahalanobis_guard,
        stress_probability: float = 0.0,
    ) -> StressComponentScore:
        diagnostics = mahalanobis_guard.distance_diagnostics(
            current_vector,
            stress_probability=stress_probability,
        )
        distance = float(diagnostics.get("adjusted_mahalanobis_distance", 0.0) or 0.0)
        bounded_distance = min(max(0.0, distance), self.config.cap_distance)
        z = (bounded_distance - self.config.threshold) / max(1e-6, self.config.width)
        score = _clip01(1.0 / (1.0 + np.exp(-np.clip(z, -40.0, 40.0))))
        return StressComponentScore(
            kind="S_macro_anom",
            value=score,
            subcomponents={
                "adjusted_mahalanobis_distance": distance,
                "threshold": float(self.config.threshold),
                "condition_number": float(diagnostics.get("condition_number", 0.0) or 0.0),
                "is_posterior": False,
                "geometry": diagnostics,
            },
        )
