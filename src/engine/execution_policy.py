"""v7.0 Execution Policy — band-triggered rebalance, separate deployment action."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.deployment_controller import DeploymentDecision
from src.engine.risk_controller import RiskDecision
from src.engine.runtime_selector import RuntimeSelection
from src.models import CurrentPortfolioState
from src.models.risk import RiskState


@dataclass(frozen=True)
class RebalanceAction:
    """Decision on whether to rebalance existing positions."""
    should_rebalance: bool
    reason: str
    target_qqq_pct: float
    target_qld_pct: float
    target_cash_pct: float


@dataclass(frozen=True)
class DeploymentAction:
    """Decision on how to deploy new incoming cash."""
    deploy_cash_amount: float
    deploy_mode: str   # "BASE" | "FAST" | "SLOW" | "PAUSE"
    reason: str


@dataclass(frozen=True)
class ExecutionActions:
    """Combined output: rebalance decision + new cash deployment decision."""
    rebalance_action: RebalanceAction
    deployment_action: DeploymentAction
    previous_risk_state: RiskState | None
    current_risk_state: RiskState


def build_execution_actions(
    portfolio: CurrentPortfolioState,
    selection: RuntimeSelection,
    risk_decision: RiskDecision,
    deployment_decision: DeploymentDecision,
    available_new_cash: float = 0.0,
    exposure_band: float = 0.03,
    cash_band: float = 0.03,
    previous_risk_state: RiskState | None = None,
) -> ExecutionActions:
    """
    Decide whether to rebalance and how to deploy new cash (SRD §11.2, AC-7).

    Rebalance triggers (OR logic):
      - risk_state changed since last run
      - current exposure deviates from target beyond exposure_band
      - current cash deviates from target beyond cash_band

    Never rebalances on small noise alone (SRD §11.3).
    Rebalance and deployment are independent actions (SRD §11.3).
    """
    target = selection.selected_candidate
    current_exposure = portfolio.qqq_pct + 2.0 * portfolio.qld_pct
    target_exposure = target.qqq_pct + 2.0 * target.qld_pct

    exposure_gap = abs(current_exposure - target_exposure)
    cash_gap = abs(portfolio.current_cash_pct - target.cash_pct)
    risk_state_changed = (
        previous_risk_state is not None
        and previous_risk_state != risk_decision.risk_state
    )

    # ── Rebalance decision ────────────────────────────────────────────────────
    if risk_state_changed:
        should_rebalance = True
        reason = f"risk_state_changed:{previous_risk_state.value if previous_risk_state else 'none'}->{risk_decision.risk_state.value}"
    elif exposure_gap > exposure_band:
        should_rebalance = True
        reason = f"exposure_drift:{exposure_gap:.3f}>{exposure_band}"
    elif cash_gap > cash_band:
        should_rebalance = True
        reason = f"cash_drift:{cash_gap:.3f}>{cash_band}"
    else:
        should_rebalance = False
        reason = f"within_bands:exposure_gap={exposure_gap:.3f},cash_gap={cash_gap:.3f}"

    rebalance_action = RebalanceAction(
        should_rebalance=should_rebalance,
        reason=reason,
        target_qqq_pct=target.qqq_pct,
        target_qld_pct=target.qld_pct,
        target_cash_pct=target.cash_pct,
    )

    # ── Deployment action (independent of rebalance) ──────────────────────────
    if deployment_decision.pause_new_cash:
        deploy_action = DeploymentAction(
            deploy_cash_amount=0.0,
            deploy_mode="PAUSE",
            reason="deployment_paused_by_controller",
        )
    else:
        multiplier = deployment_decision.dca_multiplier
        mode = deployment_decision.deployment_state.value.replace("DEPLOY_", "")
        deploy_amount = max(0.0, available_new_cash) * multiplier
        deploy_action = DeploymentAction(
            deploy_cash_amount=deploy_amount,
            deploy_mode=mode,
            reason=f"available_new_cash={max(0.0, available_new_cash):.2f};dca_multiplier={multiplier}",
        )

    return ExecutionActions(
        rebalance_action=rebalance_action,
        deployment_action=deploy_action,
        previous_risk_state=previous_risk_state,
        current_risk_state=risk_decision.risk_state,
    )
