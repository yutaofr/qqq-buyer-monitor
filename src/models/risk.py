"""Risk state models for v11 Bayesian Monitor."""

from __future__ import annotations

from enum import StrEnum


class RiskState(StrEnum):
    """Broad risk regimes for auditing."""

    RISK_NORMAL = "RISK_NORMAL"
    RISK_REDUCED = "RISK_REDUCED"
    RISK_OFF = "RISK_OFF"
