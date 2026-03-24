"""v7.0 Risk State enumeration."""
from enum import Enum


class RiskState(str, Enum):
    """Represents the current macro risk regime for portfolio exposure decisions."""
    RISK_ON = "RISK_ON"
    RISK_NEUTRAL = "RISK_NEUTRAL"
    RISK_REDUCED = "RISK_REDUCED"
    RISK_DEFENSE = "RISK_DEFENSE"
    RISK_EXIT = "RISK_EXIT"
