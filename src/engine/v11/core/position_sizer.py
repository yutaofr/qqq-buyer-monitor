"""v11 Core: Probabilistic position sizing."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizingResult:
    """Continuous v11 sizing output before behavior constraints are applied."""

    target_beta: float
    raw_target_beta: float
    entropy: float
    uncertainty_penalty: float
    reference_capital: float
    current_nav: float
    risk_budget_dollars: float
    qqq_dollars: float
    qld_notional_dollars: float
    cash_dollars: float
    qld_share: float


class ProbabilisticPositionSizer:
    """Translate posterior regime probabilities into a continuous target exposure."""

    def __init__(
        self,
        *,
        regime_beta_map: dict[str, float] | None = None,
        uncertainty_weight: float = 0.35,
        max_daily_beta_shift: float = 0.10,
        min_beta: float = 0.20,
        max_beta: float = 1.15,
    ):
        self.regime_beta_map = regime_beta_map or {
            "BUST": 0.25,
            "LATE_CYCLE": 0.60,
            "MID_CYCLE": 0.90,
            "RECOVERY": 1.00,
            "CAPITULATION": 1.15,
        }
        self.uncertainty_weight = uncertainty_weight
        self.max_daily_beta_shift = max_daily_beta_shift
        self.min_beta = min_beta
        self.max_beta = max_beta

    def size_positions(
        self,
        *,
        posteriors: dict[str, float],
        reference_capital: float,
        current_nav: float,
        previous_target_beta: float | None = None,
    ) -> PositionSizingResult:
        normalized = self._normalize(posteriors)
        raw_target_beta = sum(
            normalized.get(regime, 0.0) * beta for regime, beta in self.regime_beta_map.items()
        )
        entropy = self._normalized_entropy(normalized)
        uncertainty_penalty = entropy * self.uncertainty_weight
        target_beta = raw_target_beta * (1.0 - uncertainty_penalty)
        target_beta = max(self.min_beta, min(self.max_beta, target_beta))

        if previous_target_beta is not None:
            lower = previous_target_beta - self.max_daily_beta_shift
            upper = previous_target_beta + self.max_daily_beta_shift
            target_beta = max(lower, min(upper, target_beta))
            target_beta = max(self.min_beta, min(self.max_beta, target_beta))

        current_nav = max(0.0, float(current_nav))
        reference_capital = max(current_nav, float(reference_capital))
        risk_budget_dollars = reference_capital * target_beta

        if target_beta <= 1.0:
            qld_dollars = 0.0
            qqq_dollars = current_nav * target_beta
            cash_dollars = current_nav - qqq_dollars
        else:
            qld_dollars = current_nav * (target_beta - 1.0)
            qqq_dollars = current_nav - qld_dollars
            cash_dollars = 0.0

        invested = qqq_dollars + qld_dollars
        qld_share = qld_dollars / invested if invested > 0 else 0.0

        return PositionSizingResult(
            target_beta=round(target_beta, 6),
            raw_target_beta=round(raw_target_beta, 6),
            entropy=round(entropy, 6),
            uncertainty_penalty=round(uncertainty_penalty, 6),
            reference_capital=round(reference_capital, 6),
            current_nav=round(current_nav, 6),
            risk_budget_dollars=round(risk_budget_dollars, 6),
            qqq_dollars=round(qqq_dollars, 6),
            qld_notional_dollars=round(qld_dollars, 6),
            cash_dollars=round(cash_dollars, 6),
            qld_share=round(qld_share, 6),
        )

    @staticmethod
    def _normalize(posteriors: dict[str, float]) -> dict[str, float]:
        total = float(sum(max(0.0, value) for value in posteriors.values()))
        if total <= 0:
            n = max(1, len(posteriors))
            return {name: 1.0 / n for name in posteriors}
        return {name: max(0.0, value) / total for name, value in posteriors.items()}

    @staticmethod
    def _normalized_entropy(posteriors: dict[str, float]) -> float:
        probs = [value for value in posteriors.values() if value > 0]
        if not probs:
            return 1.0
        entropy = -sum(p * math.log(p) for p in probs)
        max_entropy = math.log(len(posteriors)) if len(posteriors) > 1 else 1.0
        if max_entropy <= 0:
            return 0.0
        return entropy / max_entropy
