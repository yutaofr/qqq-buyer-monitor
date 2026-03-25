"""TDD: Execution Policy — band triggers, separate actions, no unconditional rebalance."""
from datetime import date

import pytest

from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.deployment_controller import DeploymentDecision
from src.engine.execution_policy import build_execution_actions, RebalanceAction, DeploymentAction
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import RiskDecision
from src.engine.runtime_selector import choose_target_candidate, RuntimeSelection
from src.models import CurrentPortfolioState
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

FIXTURE = "tests/fixtures/candidate_registry_v7.json"


def _portfolio(qqq: float = 0.70, qld: float = 0.10, cash: float = 0.20) -> CurrentPortfolioState:
    return CurrentPortfolioState(
        qqq_pct=qqq, qld_pct=qld, current_cash_pct=cash,
        gross_exposure_pct=qqq + 2 * qld,
    )


def _risk(state: RiskState = RiskState.RISK_NEUTRAL) -> RiskDecision:
    return RiskDecision(state, 0.90, 0.10, ())


def _deploy_base() -> DeploymentDecision:
    return DeploymentDecision(DeploymentState.DEPLOY_BASE, 1.0, False, ())


def _deploy_pause() -> DeploymentDecision:
    return DeploymentDecision(DeploymentState.DEPLOY_PAUSE, 0.0, True, ())


def _selection_with_target(qqq: float, qld: float, cash: float) -> RuntimeSelection:
    """Build a minimal RuntimeSelection with specified target weights."""
    from src.models.candidate import CertifiedCandidate
    c = CertifiedCandidate(
        candidate_id="test-cand",
        registry_version="test-r1",
        allowed_risk_state=RiskState.RISK_NEUTRAL,
        qqq_pct=qqq, qld_pct=qld, cash_pct=cash,
        target_effective_exposure=qqq + 2 * qld,
        certification_status="CERTIFIED",
        research_metrics={"turnover": 0.05},
    )
    return RuntimeSelection(selected_candidate=c, rejected_candidates=(), selection_score=0.0)


# ── Task 12: Band-Based Rebalance Trigger ──────────────────────────────────────

def test_no_rebalance_within_bands():
    """Exposure gap 0.02 and cash gap 0.02 — both within 0.03 band → do NOT rebalance."""
    # Current: qqq=0.70, qld=0.10 → exposure=0.90. Cash=0.20
    # Target:  qqq=0.72, qld=0.09 → exposure=0.90. Cash=0.19
    # exposure_gap = 0.0, cash_gap = 0.01 → within bands
    portfolio = _portfolio(qqq=0.72, qld=0.09, cash=0.19)
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_base(),
        exposure_band=0.03, cash_band=0.03,
    )
    assert actions.rebalance_action.should_rebalance is False
    assert "within_bands" in actions.rebalance_action.reason


def test_rebalance_triggers_on_large_exposure_drift():
    """Exposure gap > 0.03 → must rebalance."""
    portfolio = _portfolio(qqq=0.60, qld=0.05, cash=0.35)  # exposure = 0.70
    selection = _selection_with_target(qqq=0.80, qld=0.05, cash=0.15)  # exposure = 0.90
    # gap = 0.20 >> 0.03
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_base(),
        exposure_band=0.03, cash_band=0.03,
    )
    assert actions.rebalance_action.should_rebalance is True
    assert "exposure_drift" in actions.rebalance_action.reason


def test_rebalance_triggers_on_large_cash_drift():
    """Cash gap > 0.03, exposure within band → must rebalance."""
    portfolio = _portfolio(qqq=0.70, qld=0.10, cash=0.20)  # cash=0.20
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.10)  # cash=0.10
    # cash_gap = 0.10 >> 0.03
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_base(),
        exposure_band=0.03, cash_band=0.03,
    )
    assert actions.rebalance_action.should_rebalance is True
    assert "cash_drift" in actions.rebalance_action.reason


def test_rebalance_triggers_on_risk_state_change():
    """Risk state change → always rebalance, even if within bands."""
    portfolio = _portfolio(qqq=0.70, qld=0.10, cash=0.20)
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)  # 0 gap
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(RiskState.RISK_DEFENSE),
        deployment_decision=_deploy_base(),
        exposure_band=0.03, cash_band=0.03,
        previous_risk_state=RiskState.RISK_NEUTRAL,  # state changed
    )
    assert actions.rebalance_action.should_rebalance is True
    assert "risk_state_changed" in actions.rebalance_action.reason


def test_no_rebalance_when_no_state_change_and_within_bands():
    """Explicitly confirm: no state change + within bands = no rebalance (SRD AC-7)."""
    portfolio = _portfolio(qqq=0.70, qld=0.10, cash=0.20)
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_base(),
        exposure_band=0.03, cash_band=0.03,
        previous_risk_state=RiskState.RISK_NEUTRAL,  # same state
    )
    assert actions.rebalance_action.should_rebalance is False


# ── Task 12: Separate Rebalance & Deployment Actions ──────────────────────────

def test_deployment_action_is_independent_of_rebalance():
    """PAUSE deployment does not require rebalance to be True."""
    portfolio = _portfolio(qqq=0.70, qld=0.10, cash=0.20)
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)  # same → no rebalance
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_pause(),
        exposure_band=0.03, cash_band=0.03,
    )
    assert actions.rebalance_action.should_rebalance is False
    assert actions.deployment_action.deploy_mode == "PAUSE"
    assert actions.deployment_action.deploy_cash_amount == 0.0


def test_deployment_action_base_mode():
    portfolio = _portfolio()
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)
    actions = build_execution_actions(
        portfolio=portfolio, selection=selection,
        risk_decision=_risk(), deployment_decision=_deploy_base(),
        available_new_cash=1000.0,
        exposure_band=0.03, cash_band=0.03,
    )
    assert actions.deployment_action.deploy_mode == "BASE"
    assert actions.deployment_action.deploy_cash_amount == 1000.0


def test_deployment_action_fast_mode_scales_actual_cash_amount():
    portfolio = _portfolio()
    selection = _selection_with_target(qqq=0.70, qld=0.10, cash=0.20)
    fast = DeploymentDecision(DeploymentState.DEPLOY_FAST, 2.0, False, ())
    actions = build_execution_actions(
        portfolio=portfolio,
        selection=selection,
        risk_decision=_risk(),
        deployment_decision=fast,
        available_new_cash=500.0,
        exposure_band=0.03,
        cash_band=0.03,
    )
    assert actions.deployment_action.deploy_mode == "FAST"
    assert actions.deployment_action.deploy_cash_amount == 1000.0


def test_execution_actions_are_immutable():
    portfolio = _portfolio()
    selection = _selection_with_target(0.70, 0.10, 0.20)
    actions = build_execution_actions(
        portfolio, selection, _risk(), _deploy_base(),
    )
    with pytest.raises((TypeError, AttributeError)):
        actions.rebalance_action = None  # type: ignore


def test_rebalance_action_contains_target_weights():
    portfolio = _portfolio()
    selection = _selection_with_target(0.65, 0.15, 0.20)
    actions = build_execution_actions(
        portfolio, selection, _risk(), _deploy_base(),
        exposure_band=0.0, cash_band=0.0,  # always rebalance
    )
    assert actions.rebalance_action.target_qqq_pct == 0.65
    assert actions.rebalance_action.target_qld_pct == 0.15
    assert actions.rebalance_action.target_cash_pct == 0.20
