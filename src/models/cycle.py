"""Cycle state models for v10.0."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CycleRegime(StrEnum):
    """Represents the current cycle stage for QQQ/QLD usage."""

    CAPITULATION = "CAPITULATION"
    RECOVERY = "RECOVERY"
    MID_CYCLE = "MID_CYCLE"
    LATE_CYCLE = "LATE_CYCLE"
    BUST = "BUST"
    UNQUALIFIED = "UNQUALIFIED"


@dataclass(frozen=True)
class CycleDecision:
    """Output of the v10.0 cycle-factor classifier."""

    cycle_regime: CycleRegime
    target_exposure_ceiling: float
    qld_share_ceiling: float
    reasons: tuple = ()
