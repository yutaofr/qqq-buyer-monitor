"""TDD: v8 deployment controller — tier-0 soft ceiling and idle semantics."""
from __future__ import annotations

from datetime import date

import pytest

from src.engine.deployment_controller import decide_deployment_state
from src.engine.feature_pipeline import build_feature_snapshot
from src.models.deployment import DeploymentState
from src.models.risk import RiskDecision, RiskState


def _snap(values: dict) -> object:
    return build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values=values,
        raw_quality={},
    )


def _risk(state: RiskState, ceiling: float = 0.90, cash: float = 0.10) -> RiskDecision:
    return RiskDecision(state, ceiling, cash, (), False)


def test_deployment_returns_idle_when_no_new_cash():
    snap = _snap({"capitulation_score": 10, "tactical_stress_score": 20})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=0.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_IDLE
    assert decision.dca_multiplier == 0.0
    assert decision.pause_new_cash is False


def test_deployment_returns_idle_when_new_cash_is_negative():
    snap = _snap({"capitulation_score": 10, "tactical_stress_score": 20})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=-100.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_IDLE


def test_rich_tightening_defaults_to_slow_without_high_quality_capitulation():
    snap = _snap({"capitulation_score": 20, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.30, 0.70),
        tier0_regime="RICH_TIGHTENING",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_SLOW


def test_rich_tightening_allows_base_when_capitulation_breaks_soft_ceiling():
    snap = _snap({"capitulation_score": 70, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.30, 0.70),
        tier0_regime="RICH_TIGHTENING",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_BASE


def test_transition_stress_defaults_to_slow_without_override():
    snap = _snap({"capitulation_score": 10, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.50, 0.50),
        tier0_regime="TRANSITION_STRESS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_SLOW


def test_transition_stress_allows_base_when_capitulation_breaks_soft_ceiling():
    snap = _snap({"capitulation_score": 70, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.50, 0.50),
        tier0_regime="TRANSITION_STRESS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_BASE


def test_crisis_cannot_break_pause_even_with_extreme_capitulation():
    snap = _snap({"capitulation_score": 90, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.0, 1.0),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert decision.pause_new_cash is True


def test_neutral_keeps_fast_path_available():
    snap = _snap({"capitulation_score": 40, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST


def test_euphoric_keeps_fast_path_available():
    snap = _snap({"capitulation_score": 40, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_ON),
        tier0_regime="EUPHORIC",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST


def test_tier0_override_threshold_is_independent_from_fast_threshold():
    module = __import__("src.engine.deployment_controller", fromlist=["_CAPITULATION_FAST_THRESHOLD"])
    assert module._TIER0_CAPITULATION_OVERRIDE_THRESHOLD != module._CAPITULATION_FAST_THRESHOLD


def test_deploy_idle_enum_exists():
    assert DeploymentState.DEPLOY_IDLE.value == "DEPLOY_IDLE"


def test_deployment_decision_is_immutable():
    snap = _snap({"capitulation_score": 40, "tactical_stress_score": 10})
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=1000.0,
    )
    with pytest.raises((TypeError, AttributeError)):
        decision.deployment_state = DeploymentState.DEPLOY_FAST  # type: ignore[misc]
