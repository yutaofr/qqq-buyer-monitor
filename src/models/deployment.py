"""v7.0 Deployment State enumeration."""
from enum import Enum


class DeploymentState(str, Enum):
    """Represents the pace at which new cash should be deployed into the market."""
    DEPLOY_BASE = "DEPLOY_BASE"
    DEPLOY_SLOW = "DEPLOY_SLOW"
    DEPLOY_FAST = "DEPLOY_FAST"
    DEPLOY_PAUSE = "DEPLOY_PAUSE"
    DEPLOY_RECOVER = "DEPLOY_RECOVER"
    DEPLOY_IDLE = "DEPLOY_IDLE"
