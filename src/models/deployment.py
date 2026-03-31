"""Deployment state models for v11 Bayesian Monitor."""
from __future__ import annotations
from enum import StrEnum

class DeploymentState(StrEnum):
    """Incremental cash deployment pacing states."""
    DEPLOY_FAST = "DEPLOY_FAST"
    DEPLOY_BASE = "DEPLOY_BASE"
    DEPLOY_SLOW = "DEPLOY_SLOW"
    DEPLOY_PAUSE = "DEPLOY_PAUSE"

def deployment_multiplier_for_state(state: str | DeploymentState) -> float:
    """Map deployment state to a numerical pacing multiplier."""
    s = str(state)
    if "FAST" in s: return 2.0
    if "BASE" in s: return 1.0
    if "SLOW" in s: return 0.5
    if "PAUSE" in s: return 0.0
    return 1.0
