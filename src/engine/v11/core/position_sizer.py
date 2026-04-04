"""v11 Core: shared sizing payload for downstream execution controls."""

from __future__ import annotations

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


__all__ = ["PositionSizingResult"]
