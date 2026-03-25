"""Risk state models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskState(str, Enum):
    """Represents the current macro risk regime for portfolio exposure decisions."""
    RISK_ON = "RISK_ON"
    RISK_NEUTRAL = "RISK_NEUTRAL"
    RISK_REDUCED = "RISK_REDUCED"
    RISK_DEFENSE = "RISK_DEFENSE"
    RISK_EXIT = "RISK_EXIT"


@dataclass(frozen=True)
class RiskDecision:
    """Output of the Risk Controller for one market day."""

    risk_state: RiskState
    target_exposure_ceiling: float
    target_cash_floor: float
    reasons: tuple = ()
    tier0_applied: bool = False
