from __future__ import annotations

import math

import numpy as np

from src.engine.v11.stress.config import StressCombinerConfig
from src.engine.v11.stress.types import CombinedStressScore


def _clip01(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + np.exp(-float(np.clip(value, -40.0, 40.0)))))


class StressCombiner:
    """Interpretable logistic combiner with explicit conditional interactions."""

    def __init__(self, config: StressCombinerConfig | None = None):
        self.config = config or StressCombinerConfig()

    def combine(
        self,
        *,
        S_price: float,
        S_market: float,
        S_macro_anom: float,
        S_persist: float,
    ) -> CombinedStressScore:
        raw_inputs = {
            "S_price": _clip01(S_price),
            "S_market": _clip01(S_market),
            "S_macro_anom": _clip01(S_macro_anom),
            "S_persist": _clip01(S_persist),
        }
        transformed = {name: self._transform(value) for name, value in raw_inputs.items()}
        coeff = self.config.coefficients
        terms = {
            "intercept": float(coeff.get("intercept", 0.0)),
            "S_price": float(coeff.get("S_price", 0.0)) * transformed["S_price"],
            "S_market": float(coeff.get("S_market", 0.0)) * transformed["S_market"],
            "S_macro_anom": float(coeff.get("S_macro_anom", 0.0))
            * transformed["S_macro_anom"],
            "S_persist": float(coeff.get("S_persist", 0.0)) * transformed["S_persist"],
            "interaction_price_market": max(0.0, float(coeff.get("interaction_price_market", 0.0)))
            * raw_inputs["S_price"]
            * raw_inputs["S_market"],
            "interaction_price_macro": max(0.0, float(coeff.get("interaction_price_macro", 0.0)))
            * raw_inputs["S_price"]
            * raw_inputs["S_macro_anom"],
            "interaction_market_macro": max(
                0.0, float(coeff.get("interaction_market_macro", 0.0))
            )
            * raw_inputs["S_market"]
            * raw_inputs["S_macro_anom"],
        }
        linear_score = float(sum(terms.values()))
        return CombinedStressScore(
            raw_score=_sigmoid(linear_score),
            linear_score=linear_score,
            terms=terms,
            transformed_inputs=transformed,
        )

    def _transform(self, value: float) -> float:
        value = _clip01(value)
        if self.config.transform == "square":
            return value * value
        if self.config.transform == "sqrt":
            return float(np.sqrt(value))
        if self.config.transform == "hinge":
            return _clip01((value - 0.25) / 0.75)
        return value
