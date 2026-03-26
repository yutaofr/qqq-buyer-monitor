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




def test_rich_tightening_defaults_to_base_without_left_tail_confirmation():
    snap = _snap(
        {
            "credit_spread": 470.0,
            "capitulation_score": 20,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.05,
            "five_day_return": 0.01,
            "twenty_day_return": -0.02,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.30, 0.70),
        tier0_regime="RICH_TIGHTENING",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_BASE


def test_rich_tightening_allows_fast_when_left_tail_momentum_confirms():
    snap = _snap(
        {
            "credit_spread": 470.0,
            "capitulation_score": 70,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.18,
            "five_day_return": -0.03,
            "twenty_day_return": -0.10,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.30, 0.70),
        tier0_regime="RICH_TIGHTENING",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST


def test_transition_stress_defaults_to_slow_without_left_tail_confirmation():
    snap = _snap(
        {
            "credit_spread": 560.0,
            "capitulation_score": 70,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.18,
            "five_day_return": -0.01,
            "twenty_day_return": -0.04,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_DEFENSE, 0.50, 0.50),
        tier0_regime="TRANSITION_STRESS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_SLOW


def test_transition_stress_allows_fast_when_left_tail_momentum_confirms():
    snap = _snap(
        {
            "credit_spread": 560.0,
            "capitulation_score": 70,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.20,
            "five_day_return": -0.04,
            "twenty_day_return": -0.10,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_DEFENSE, 0.50, 0.50),
        tier0_regime="TRANSITION_STRESS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST


def test_crisis_cannot_break_pause_even_with_extreme_capitulation():
    snap = _snap(
        {
            "credit_spread": 680.0,
            "capitulation_score": 90,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.30,
            "five_day_return": -0.04,
            "twenty_day_return": -0.12,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.0, 1.0),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert decision.pause_new_cash is True


def test_crisis_liquidity_reversal_override_unlocks_fast_deployment():
    snap = _snap(
        {
            "credit_spread": 680.0,
            "credit_acceleration": -1.0,
            "liquidity_roc": 1.0,
            "capitulation_score": 20,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.18,
            "five_day_return": -0.03,
            "twenty_day_return": -0.10,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.50, 0.50),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST
    assert decision.pause_new_cash is False
    assert any(reason["rule"] == "blood_chip_crisis_override" for reason in decision.reasons)


def test_crisis_panic_exhaustion_override_unlocks_fast_deployment():
    snap = _snap(
        {
            "credit_spread": 680.0,
            "capitulation_score": 30,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.22,
            "five_day_return": -0.04,
            "twenty_day_return": -0.11,
            "price_vix_divergence": True,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.50, 0.50),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST
    assert any(reason["rule"] == "blood_chip_crisis_override" for reason in decision.reasons)


def test_crisis_smart_money_support_override_unlocks_fast_deployment():
    snap = _snap(
        {
            "credit_spread": 680.0,
            "capitulation_score": 20,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.19,
            "five_day_return": -0.03,
            "twenty_day_return": -0.09,
            "price_mfi_divergence": True,
            "near_volume_poc": True,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.50, 0.50),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST
    assert any(reason["rule"] == "blood_chip_crisis_override" for reason in decision.reasons)


def test_crisis_override_is_blocked_when_tactical_stress_says_pause():
    snap = _snap(
        {
            "credit_spread": 680.0,
            "credit_acceleration": -1.0,
            "liquidity_roc": 1.0,
            "capitulation_score": 30,
            "tactical_stress_score": 80,
            "rolling_drawdown": 0.18,
            "five_day_return": -0.03,
            "twenty_day_return": -0.10,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_EXIT, 0.50, 0.50),
        tier0_regime="CRISIS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert decision.pause_new_cash is True
    assert any(reason["rule"] == "tactical_stress_pause" for reason in decision.reasons)


def test_neutral_keeps_fast_path_available():
    snap = _snap(
        {
            "credit_spread": 320.0,
            "capitulation_score": 40,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.12,
            "five_day_return": -0.02,
            "twenty_day_return": -0.09,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST


def test_euphoric_keeps_fast_path_available():
    snap = _snap(
        {
            "credit_spread": 220.0,
            "capitulation_score": 40,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.12,
            "five_day_return": -0.02,
            "twenty_day_return": -0.09,
        }
    )
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


def test_reduced_state_pauses_on_deep_drawdown_even_without_crisis_spreads():
    snap = _snap(
        {
            "credit_spread": 470.0,
            "capitulation_score": 80,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.30,
            "five_day_return": -0.04,
            "twenty_day_return": -0.12,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_REDUCED, 0.50, 0.50),
        tier0_regime="RICH_TIGHTENING",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert decision.pause_new_cash is True


def test_defense_state_pauses_on_deep_drawdown_even_when_left_tail_is_extreme():
    snap = _snap(
        {
            "credit_spread": 560.0,
            "capitulation_score": 80,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.28,
            "five_day_return": -0.05,
            "twenty_day_return": -0.14,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_DEFENSE, 0.50, 0.50),
        tier0_regime="TRANSITION_STRESS",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_PAUSE
    assert decision.pause_new_cash is True


def test_shallow_pullback_uses_five_day_weakness_to_unlock_fast():
    snap = _snap(
        {
            "credit_spread": 320.0,
            "capitulation_score": 20,
            "tactical_stress_score": 10,
            "rolling_drawdown": 0.09,
            "five_day_return": -0.02,
            "twenty_day_return": -0.04,
        }
    )
    decision = decide_deployment_state(
        snap,
        _risk(RiskState.RISK_NEUTRAL),
        tier0_regime="NEUTRAL",
        available_new_cash=1000.0,
    )
    assert decision.deployment_state == DeploymentState.DEPLOY_FAST



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
