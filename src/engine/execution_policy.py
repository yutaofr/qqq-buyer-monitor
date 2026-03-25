"""v8.0 execution policy — beta recommendation only, no amount output."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.runtime_selector import RuntimeSelection
from src.models.risk import RiskDecision, RiskState


@dataclass(frozen=True)
class BetaRecommendation:
    """Recommend target portfolio beta and whether an adjustment is warranted."""

    target_beta: float
    recommended_qqq_pct: float
    recommended_qld_pct: float
    recommended_cash_pct: float
    should_adjust: bool
    adjustment_reason: str
    current_risk_state: RiskState
    previous_risk_state: RiskState | None


def build_beta_recommendation(
    selection: RuntimeSelection,
    risk_decision: RiskDecision,
    previous_risk_state: RiskState | None = None,
) -> BetaRecommendation:
    """Build the v8.0 recommendation surface from runtime selection + risk state."""

    target = selection.selected_candidate
    target_exposure = target.qqq_pct + 2.0 * target.qld_pct
    risk_state_changed = (
        previous_risk_state is not None
        and previous_risk_state != risk_decision.risk_state
    )

    if risk_state_changed:
        should_adjust = True
        reason = (
            f"risk_state_changed:{previous_risk_state.value}"
            f"->{risk_decision.risk_state.value}"
        )
    else:
        should_adjust = True
        reason = "align_to_target"

    return BetaRecommendation(
        target_beta=target_exposure,
        recommended_qqq_pct=target.qqq_pct,
        recommended_qld_pct=target.qld_pct,
        recommended_cash_pct=target.cash_pct,
        should_adjust=should_adjust,
        adjustment_reason=reason,
        current_risk_state=risk_decision.risk_state,
        previous_risk_state=previous_risk_state,
    )
