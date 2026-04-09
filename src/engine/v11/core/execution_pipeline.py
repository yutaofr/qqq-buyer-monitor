from typing import Any

import numpy as np

from src.engine.v11.core.expectation_surface import BETA_FLOOR, clamp_beta


def compute_effective_entropy(*, posterior_entropy: float, quality_score: float) -> float:
    """Calculates effective entropy by penalizing low data quality with an additive shift."""
    h = float(np.clip(posterior_entropy, 0.0, 1.0))
    q = float(np.clip(quality_score, 0.0, 1.0))
    # V14.6: Switch to additive penalty to prevent 'Quality Paralysis'
    return float(np.clip(h + (1.0 - q) * 0.15, 0.0, 1.0))


def compute_pre_floor_beta(
    *, raw_beta: float, effective_entropy: float, state_count: int, entropy_controller: Any
) -> float:
    """Applies information-theoretic haircut to raw beta expectation."""
    return entropy_controller.apply_haircut(
        raw_beta,
        effective_entropy,
        state_count=state_count,
    )


def apply_beta_floor(
    *, pre_floor_beta: float, floor: float = BETA_FLOOR, overlay_state: str | None = None
) -> tuple[float, bool]:
    """Applies the non-negotiable business floor to beta."""
    _ = overlay_state
    protected_beta = clamp_beta(pre_floor_beta, floor=floor)
    is_floor_active = bool(protected_beta > float(pre_floor_beta))
    return protected_beta, is_floor_active


def compute_overlay_beta(
    *,
    protected_beta: float,
    beta_overlay_multiplier: float,
    floor: float = BETA_FLOOR,
) -> float:
    """Applies execution overlay multiplier without violating the business floor."""
    return clamp_beta(protected_beta * float(beta_overlay_multiplier), floor=floor)


def compute_deployment_readiness(
    *, effective_entropy: float, e_sharpe: float, erp_percentile: float
) -> float:
    """Calculates CDR (Capital Deployment Readiness) score."""
    return float(np.clip((1.0 - effective_entropy) * max(0.0, e_sharpe) * erp_percentile, 0.0, 1.0))


def run_execution_pipeline(
    *,
    raw_beta: float,
    posterior_entropy: float,
    quality_score: float,
    posteriors: dict[str, float],
    entropy_controller: Any,
    overlay: dict[str, Any],
    e_sharpe: float,
    erp_percentile: float,
    high_entropy_streak: int,
    bypass_v11_floor: bool = False,
) -> dict[str, Any]:
    """Orchestrates the full post-inference execution logic."""

    effective_entropy = compute_effective_entropy(
        posterior_entropy=posterior_entropy, quality_score=quality_score
    )

    pre_floor_beta = compute_pre_floor_beta(
        raw_beta=raw_beta,
        effective_entropy=effective_entropy,
        state_count=len(posteriors),
        entropy_controller=entropy_controller,
    )

    if bypass_v11_floor:
        protected_beta, is_floor_active = pre_floor_beta, False
    else:
        protected_beta, is_floor_active = apply_beta_floor(
            pre_floor_beta=pre_floor_beta, overlay_state=overlay.get("overlay_state")
        )

    overlay_beta = compute_overlay_beta(
        protected_beta=protected_beta,
        beta_overlay_multiplier=float(overlay.get("beta_overlay_multiplier", 1.0)),
    )

    deployment_readiness = compute_deployment_readiness(
        effective_entropy=effective_entropy, e_sharpe=e_sharpe, erp_percentile=erp_percentile
    )

    overlay_deployment_readiness = float(
        np.clip(
            deployment_readiness * float(overlay.get("deployment_overlay_multiplier", 1.0)),
            0.0,
            1.0,
        )
    )

    # Update high entropy streak
    new_streak = high_entropy_streak + 1 if effective_entropy > 0.85 else 0

    return {
        "effective_entropy": effective_entropy,
        "pre_floor_beta": pre_floor_beta,
        "protected_beta": protected_beta,
        "is_floor_active": is_floor_active,
        "overlay_beta": overlay_beta,
        "deployment_readiness": deployment_readiness,
        "overlay_deployment_readiness": overlay_deployment_readiness,
        "high_entropy_streak": new_streak,
    }
