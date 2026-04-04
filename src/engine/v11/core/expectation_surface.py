from __future__ import annotations

from typing import Final

import numpy as np

from src.models.deployment import DeploymentState, deployment_multiplier_for_state
from src.regime_topology import canonicalize_regime_name

BETA_FLOOR: Final[float] = 0.5
BETA_CEILING: Final[float] = 1.2
DEFAULT_REFERENCE_CAPITAL: Final[float] = 100_000.0
DEPLOYMENT_NOTIONAL_UNIT: Final[float] = 0.01

EXPECTED_DEPLOYMENT_BY_REGIME: Final[dict[str, str]] = {
    "RECOVERY": DeploymentState.DEPLOY_FAST.value,
    "MID_CYCLE": DeploymentState.DEPLOY_BASE.value,
    "LATE_CYCLE": DeploymentState.DEPLOY_SLOW.value,
    "BUST": DeploymentState.DEPLOY_PAUSE.value,
}

DEPLOYMENT_STATE_RANK: Final[dict[str, int]] = {
    DeploymentState.DEPLOY_PAUSE.value: 0,
    DeploymentState.DEPLOY_SLOW.value: 1,
    DeploymentState.DEPLOY_BASE.value: 2,
    DeploymentState.DEPLOY_FAST.value: 3,
}


def clamp_beta(
    beta: float,
    *,
    floor: float = BETA_FLOOR,
    ceiling: float = BETA_CEILING,
) -> float:
    return float(np.clip(float(beta), float(floor), float(ceiling)))


def compute_beta_expectation(
    posteriors: dict[str, float],
    base_betas: dict[str, float],
    *,
    floor: float = BETA_FLOOR,
    ceiling: float = BETA_CEILING,
) -> float:
    expectation = sum(
        float(posteriors.get(regime, 0.0)) * float(base_betas.get(regime, 1.0))
        for regime in base_betas
    )
    return clamp_beta(expectation, floor=floor, ceiling=ceiling)


def expected_policy_for_regime(
    regime: str,
    *,
    base_betas: dict[str, float],
    floor: float = BETA_FLOOR,
    ceiling: float = BETA_CEILING,
) -> dict[str, float | str]:
    canonical = canonicalize_regime_name(regime)
    expected_beta = clamp_beta(
        float(base_betas.get(canonical, 1.0)),
        floor=floor,
        ceiling=ceiling,
    )
    expected_state = EXPECTED_DEPLOYMENT_BY_REGIME.get(
        canonical,
        DeploymentState.DEPLOY_BASE.value,
    )
    expected_multiplier = deployment_multiplier_for_state(expected_state)
    return {
        "expected_target_beta": expected_beta,
        "expected_deployment_state": expected_state,
        "expected_deployment_multiplier": float(expected_multiplier),
    }


def deployment_state_rank(state: str) -> int:
    return DEPLOYMENT_STATE_RANK.get(str(state), DEPLOYMENT_STATE_RANK[DeploymentState.DEPLOY_BASE.value])


def deployment_cash_notional(
    multiplier: float,
    *,
    reference_capital: float = DEFAULT_REFERENCE_CAPITAL,
    deployment_unit: float = DEPLOYMENT_NOTIONAL_UNIT,
) -> float:
    return float(reference_capital) * float(deployment_unit) * float(multiplier)
