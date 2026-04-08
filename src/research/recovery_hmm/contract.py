"""Shadow-only contract for the recovery HMM research track."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryHmmShadowContract:
    """Declares that recovery HMM work is isolated from live production execution."""

    shadow_only: bool = True
    production_beta_floor: float = 0.5
    may_modify_live_target_beta: bool = False
