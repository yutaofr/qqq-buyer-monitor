from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.engine.v11.stress.config import StressPosteriorConfig
from src.engine.v11.stress.diagnostics.stress_attribution import StressAttributor
from src.engine.v11.stress.models.stress_calibrator import StressCalibrator
from src.engine.v11.stress.models.stress_combiner import StressCombiner
from src.engine.v11.stress.signals.macro_anomaly import MacroAnomalyScorer
from src.engine.v11.stress.signals.market_stress import MarketStressScorer
from src.engine.v11.stress.signals.persistence import PersistenceScorer
from src.engine.v11.stress.signals.price_damage import PriceDamageScorer


@dataclass(frozen=True)
class StressPosteriorResult:
    mode: str
    components: dict[str, float]
    pi_stress_raw: float
    pi_stress_calibrated: float
    attribution: dict[str, Any]
    component_diagnostics: dict[str, Any] = field(default_factory=dict)


class StressPosteriorEngine:
    """Layered pi_stress posterior with rollback-compatible legacy mode."""

    def __init__(
        self,
        config: StressPosteriorConfig | None = None,
        *,
        mode: str | None = None,
        calibrator: StressCalibrator | None = None,
    ):
        base = config or StressPosteriorConfig()
        if mode is not None:
            base = StressPosteriorConfig(
                mode=mode,
                calibrator_method=base.calibrator_method,
                price=base.price,
                market=base.market,
                macro=base.macro,
                persistence=base.persistence,
                combiner=base.combiner,
            )
        self.config = base
        self.price_scorer = PriceDamageScorer(base.price)
        self.market_scorer = MarketStressScorer(base.market)
        self.macro_scorer = MacroAnomalyScorer(base.macro)
        self.persistence_scorer = PersistenceScorer(base.persistence)
        self.combiner = StressCombiner(base.combiner)
        self.calibrator = calibrator or StressCalibrator(method="identity")
        self.attributor = StressAttributor()

    def score(
        self,
        *,
        topology_state,
        latest_vector: np.ndarray,
        mahalanobis_guard,
        feature_history: pd.DataFrame | None = None,
    ) -> StressPosteriorResult:
        if self.config.mode == "legacy_topology":
            legacy = self.legacy_topology_probability(topology_state)
            components = {
                "S_price": legacy,
                "S_market": 0.0,
                "S_macro_anom": 0.0,
                "S_persist": 0.0,
            }
            return StressPosteriorResult(
                mode="legacy_topology",
                components=components,
                pi_stress_raw=legacy,
                pi_stress_calibrated=legacy,
                attribution={
                    "components": components,
                    "raw_score": legacy,
                    "calibrated_score": legacy,
                    "terms": {"legacy_topology": legacy},
                    "top_contributors": [{"term": "legacy_topology", "contribution": legacy}],
                },
                component_diagnostics={},
            )

        price = self.price_scorer.score(topology_state)
        market = self.market_scorer.score(
            topology_state=topology_state,
            feature_history=feature_history,
        )
        macro = self.macro_scorer.score(
            current_vector=np.asarray(latest_vector, dtype=float),
            mahalanobis_guard=mahalanobis_guard,
            stress_probability=max(price.value, market.value) * 0.5,
        )
        persist = self.persistence_scorer.score(
            price_score=price.value,
            market_score=market.value,
            macro_score=macro.value,
        )
        components = {
            "S_price": float(price.value),
            "S_market": float(market.value),
            "S_macro_anom": float(macro.value),
            "S_persist": float(persist.value),
        }
        combined = self.combiner.combine(**components)
        calibrated = self.calibrator.transform_one(combined.raw_score)
        attribution = self.attributor.explain(
            components=components,
            combined=combined,
            calibrated_score=calibrated,
        )
        return StressPosteriorResult(
            mode=self.config.mode,
            components=components,
            pi_stress_raw=float(combined.raw_score),
            pi_stress_calibrated=float(calibrated),
            attribution=attribution,
            component_diagnostics={
                price.kind: dict(price.subcomponents),
                market.kind: dict(market.subcomponents),
                macro.kind: dict(macro.subcomponents),
                persist.kind: dict(persist.subcomponents),
            },
        )

    @staticmethod
    def legacy_topology_probability(topology_state) -> float:
        probabilities = getattr(topology_state, "probabilities", {}) or {}
        bust_prob = float(probabilities.get("BUST", 0.0) or 0.0)
        recovery_prob = float(probabilities.get("RECOVERY", 0.0) or 0.0)
        transition = float(getattr(topology_state, "transition_intensity", 0.0) or 0.0)
        damage = float(getattr(topology_state, "damage_memory", 0.0) or 0.0)
        bust_pressure = float(getattr(topology_state, "bust_pressure", 0.0) or 0.0)
        repair = float(getattr(topology_state, "repair_persistence", 0.0) or 0.0)
        stress = max(
            bust_prob,
            0.55 * bust_pressure,
            transition * min(1.0, damage),
            recovery_prob * transition * min(1.0, damage + repair),
        )
        return float(np.clip(stress, 0.0, 1.0))
