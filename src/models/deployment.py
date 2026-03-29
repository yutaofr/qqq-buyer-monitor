"""v7.0 Deployment State enumeration."""
from enum import StrEnum


class DeploymentState(StrEnum):
    """Represents the pace at which new cash should be deployed into the market."""
    DEPLOY_BASE = "DEPLOY_BASE"
    DEPLOY_SLOW = "DEPLOY_SLOW"
    DEPLOY_FAST = "DEPLOY_FAST"
    DEPLOY_PAUSE = "DEPLOY_PAUSE"
    DEPLOY_RECOVER = "DEPLOY_RECOVER"


DEPLOYMENT_MULTIPLIER_BY_STATE: dict[str, float] = {
    DeploymentState.DEPLOY_PAUSE.value: 0.0,
    DeploymentState.DEPLOY_SLOW.value: 0.5,
    DeploymentState.DEPLOY_BASE.value: 1.0,
    DeploymentState.DEPLOY_RECOVER.value: 1.0,
    DeploymentState.DEPLOY_FAST.value: 2.0,
}


def deployment_multiplier_for_state(state: DeploymentState | str | None) -> float | None:
    """Translate a deployment state into its normalized pacing multiplier."""
    if state is None:
        return None

    state_value = state.value if isinstance(state, DeploymentState) else str(state)
    if state_value not in DEPLOYMENT_MULTIPLIER_BY_STATE:
        raise ValueError(f"Unknown deployment state: {state_value}")
    return DEPLOYMENT_MULTIPLIER_BY_STATE[state_value]
