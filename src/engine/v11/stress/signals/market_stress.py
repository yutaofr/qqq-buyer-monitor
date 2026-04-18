from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.engine.v11.stress.config import MarketStressConfig
from src.engine.v11.stress.types import StressComponentScore


def _clip01(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + np.exp(-float(np.clip(value, -40.0, 40.0)))))


class MarketStressScorer:
    """Build S_market from market-internal confirmation where available."""

    def __init__(self, config: MarketStressConfig | None = None):
        self.config = config or MarketStressConfig()

    def score(self, *, topology=None, topology_state=None, feature_history: pd.DataFrame | None = None) -> StressComponentScore:
        topology_obj = topology_state if topology_state is not None else topology
        frame = feature_history if feature_history is not None else pd.DataFrame()
        latest = frame.iloc[-1] if not frame.empty else pd.Series(dtype=float)

        vol = self._max_abs_feature(latest, self.config.vol_feature_names)
        spread = self._max_abs_feature(latest, self.config.spread_feature_names)
        breadth = self._max_abs_feature(latest, self.config.breadth_feature_names)
        corr = self._max_abs_feature(latest, self.config.correlation_feature_names)
        beta_instability = self._max_abs_feature(latest, self.config.beta_instability_names)
        breadth_compression = self._breadth_compression(latest)
        term_structure = self._term_structure_stress(latest)

        transition = _clip01(float(getattr(topology_obj, "transition_intensity", 0.0) or 0.0))
        entropy = _clip01(float(getattr(topology_obj, "benchmark_entropy", 0.0) or 0.0))
        topology_confirmation = 0.55 * transition + 0.45 * entropy

        feature_confirmation = max(
            self._z_to_score(vol),
            self._z_to_score(0.90 * spread),
            self._z_to_score(0.75 * breadth),
            self._z_to_score(1.50 * corr),
            self._z_to_score(0.70 * beta_instability),
            breadth_compression,
            term_structure,
        )
        score = 0.72 * feature_confirmation + 0.28 * topology_confirmation
        return StressComponentScore(
            kind="S_market",
            value=_clip01(score),
            subcomponents={
                "volatility_confirmation": self._z_to_score(vol),
                "spread_confirmation": self._z_to_score(spread),
                "breadth_confirmation": self._z_to_score(breadth),
                "correlation_stress": self._z_to_score(1.50 * corr),
                "breadth_compression": breadth_compression,
                "term_structure_stress": term_structure,
                "beta_instability": self._z_to_score(0.70 * beta_instability),
                "topology_confirmation": topology_confirmation,
                "fallback_used": bool(frame.empty),
            },
        )

    @staticmethod
    def _max_abs_feature(latest: pd.Series, names: tuple[str, ...]) -> float:
        values = []
        for name in names:
            if name in latest:
                value = pd.to_numeric(pd.Series([latest[name]]), errors="coerce").iloc[0]
                if pd.notna(value) and np.isfinite(float(value)):
                    values.append(abs(float(value)))
        return max(values) if values else 0.0

    def _z_to_score(self, value: float) -> float:
        return _clip01(_sigmoid((float(value) - self.config.z_center) / self.config.z_scale))

    def _breadth_compression(self, latest: pd.Series) -> float:
        breadth_values = []
        for name in self.config.breadth_internal_names:
            if name in latest:
                value = pd.to_numeric(pd.Series([latest[name]]), errors="coerce").iloc[0]
                if pd.notna(value) and np.isfinite(float(value)):
                    breadth_values.append(float(value))
        if not breadth_values:
            return 0.0
        quality = 1.0
        for name in self.config.breadth_quality_names:
            if name in latest:
                value = pd.to_numeric(pd.Series([latest[name]]), errors="coerce").iloc[0]
                if pd.notna(value) and np.isfinite(float(value)):
                    quality = max(0.0, min(1.0, float(value)))
                    break
        compression = max(0.0, 0.50 - min(breadth_values)) / 0.35
        return _clip01(compression * quality)

    def _term_structure_stress(self, latest: pd.Series) -> float:
        for name in self.config.term_structure_names:
            if name not in latest:
                continue
            value = pd.to_numeric(pd.Series([latest[name]]), errors="coerce").iloc[0]
            if pd.isna(value) or not np.isfinite(float(value)):
                continue
            val = float(value)
            if name == "term_structure_stress":
                return _clip01(val)
            return _clip01((val - 1.0) / 0.30)
        return 0.0
