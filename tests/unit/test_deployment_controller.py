"""TDD: Deployment Controller — all states and risk ceiling enforcement."""
from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.deployment_controller import decide_deployment_state, DeploymentDecision
from src.engine.risk_controller import RiskDecision
from src.models.risk import RiskState
from src.models.deployment import DeploymentState


def _snap(values: dict) -> object:
    return build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values=values,
        raw_quality={},
    )


def _risk(state: RiskState, ceiling: float = 0.90, cash: float = 0.10) -> RiskDecision:
    return RiskDecision(state, ceiling, cash, ())


# ── Task 7 ─────────────────────────────────────────────────────────────────────

def test_deployment_fast_under_neutral_with_capitulation():
    snap = _snap({"capitulation_score": 40, "tactical_stress_score": 20})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_NEUTRAL), available_new_cash=1000.0)
    assert deploy.deployment_state == DeploymentState.DEPLOY_FAST
    assert deploy.dca_multiplier == 2.0
    assert deploy.pause_new_cash is False


def test_deployment_fast_under_risk_on_with_capitulation():
    snap = _snap({"capitulation_score": 50, "tactical_stress_score": 10})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_ON), available_new_cash=500.0)
    assert deploy.deployment_state == DeploymentState.DEPLOY_FAST


def test_deployment_base_under_clean_neutral():
    snap = _snap({"capitulation_score": 10, "tactical_stress_score": 20})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_NEUTRAL))
    assert deploy.deployment_state == DeploymentState.DEPLOY_BASE
    assert deploy.dca_multiplier == 1.0


def test_deployment_slow_under_risk_reduced():
    snap = _snap({"capitulation_score": 10, "tactical_stress_score": 20})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_REDUCED, 0.75, 0.25))
    assert deploy.deployment_state == DeploymentState.DEPLOY_SLOW


def test_deployment_has_reasons():
    snap = _snap({"capitulation_score": 40, "tactical_stress_score": 20})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_NEUTRAL))
    assert len(deploy.reasons) > 0


def test_deployment_decision_is_immutable():
    import pytest
    snap = _snap({})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_NEUTRAL))
    with pytest.raises((TypeError, AttributeError)):
        deploy.deployment_state = DeploymentState.DEPLOY_FAST  # type: ignore


# ── Task 8 ─────────────────────────────────────────────────────────────────────

def test_deployment_cannot_fast_under_defense():
    snap = _snap({"capitulation_score": 50, "tactical_stress_score": 50})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_DEFENSE, 0.50, 0.50))
    assert deploy.deployment_state != DeploymentState.DEPLOY_FAST
    assert deploy.deployment_state == DeploymentState.DEPLOY_PAUSE


def test_deployment_cannot_fast_under_exit():
    snap = _snap({"capitulation_score": 80, "tactical_stress_score": 10})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_EXIT, 0.25, 0.75))
    assert deploy.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert deploy.pause_new_cash is True


def test_deployment_ceiling_enforced_on_risk_reduced():
    """Under RISK_REDUCED, ceiling is DEPLOY_SLOW — FAST must not appear."""
    snap = _snap({"capitulation_score": 60, "tactical_stress_score": 5})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_REDUCED, 0.75, 0.25))
    assert deploy.deployment_state in {DeploymentState.DEPLOY_SLOW, DeploymentState.DEPLOY_BASE, DeploymentState.DEPLOY_PAUSE}
    assert deploy.deployment_state != DeploymentState.DEPLOY_FAST


def test_deployment_ceiling_reason_recorded():
    snap = _snap({"capitulation_score": 50, "tactical_stress_score": 50})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_DEFENSE, 0.50, 0.50))
    assert any("risk_ceiling" in str(r) for r in deploy.reasons)


def test_deployment_high_stress_triggers_pause():
    snap = _snap({"tactical_stress_score": 80, "capitulation_score": 10})
    deploy = decide_deployment_state(snap, _risk(RiskState.RISK_NEUTRAL))
    assert deploy.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert deploy.pause_new_cash is True
