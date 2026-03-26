"""TDD: v8 execution policy — beta recommendation only, no amount output."""
from __future__ import annotations

import importlib

import pytest

from src.engine.runtime_selector import RuntimeSelection
from src.models.candidate import CertifiedCandidate
from src.models.risk import RiskState


def _risk(state: RiskState = RiskState.RISK_NEUTRAL, *, tier0_applied: bool = False):
    from src.engine.risk_controller import RiskDecision

    return RiskDecision(state, 0.90, 0.10, tier0_applied=tier0_applied, reasons=())


def _selection_with_target(qqq: float, qld: float, cash: float) -> RuntimeSelection:
    candidate = CertifiedCandidate(
        candidate_id="test-cand",
        registry_version="test-r1",
        allowed_risk_state=RiskState.RISK_NEUTRAL,
        qqq_pct=qqq,
        qld_pct=qld,
        cash_pct=cash,
        target_effective_exposure=qqq + 2 * qld,
        certification_status="CERTIFIED",
        research_metrics={"turnover": 0.05},
    )
    return RuntimeSelection(selected_candidate=candidate, rejected_candidates=(), selection_score=0.0)


def _build_beta_recommendation(**kwargs):
    module = importlib.import_module("src.engine.execution_policy")
    builder = module.build_beta_recommendation
    return builder(**kwargs)


def test_build_execution_actions_interface_has_been_deleted():
    module = importlib.import_module("src.engine.execution_policy")
    assert not hasattr(module, "build_execution_actions")


def test_beta_recommendation_has_no_amount_fields():
    recommendation = _build_beta_recommendation(
        selection=_selection_with_target(0.60, 0.15, 0.25),
        risk_decision=_risk(),
    )
    assert not hasattr(recommendation, "deploy_cash_amount")
    assert not hasattr(recommendation, "rebalance_amount")


def test_beta_recommendation_computes_portfolio_beta():
    recommendation = _build_beta_recommendation(
        selection=_selection_with_target(0.60, 0.15, 0.25),
        risk_decision=_risk(),
    )
    assert recommendation.target_beta == pytest.approx(0.90)
    assert recommendation.recommended_qqq_pct == pytest.approx(0.60)
    assert recommendation.recommended_qld_pct == pytest.approx(0.15)
    assert recommendation.recommended_cash_pct == pytest.approx(0.25)


def test_should_adjust_defaults_to_true_for_alignment():
    recommendation = _build_beta_recommendation(
        selection=_selection_with_target(0.80, 0.05, 0.15),
        risk_decision=_risk(),
    )
    assert recommendation.should_adjust is True
    assert "align_to_target" in recommendation.adjustment_reason


def test_should_adjust_on_risk_state_change():
    recommendation = _build_beta_recommendation(
        selection=_selection_with_target(0.70, 0.10, 0.20),
        risk_decision=_risk(RiskState.RISK_DEFENSE),
        previous_risk_state=RiskState.RISK_NEUTRAL,
    )
    assert recommendation.should_adjust is True
    assert "risk_state_changed" in recommendation.adjustment_reason


def test_beta_recommendation_is_immutable():
    recommendation = _build_beta_recommendation(
        selection=_selection_with_target(0.70, 0.10, 0.20),
        risk_decision=_risk(),
    )
    with pytest.raises((TypeError, AttributeError)):
        recommendation.target_beta = 0.0  # type: ignore[misc]


def test_advisory_friction_blocks_rebalance_within_no_trade_band():
    module = importlib.import_module("src.engine.execution_policy")
    config = module.AdvisoryFrictionConfig(no_trade_band=0.15)
    state = module.AdvisoryState(
        assumed_beta=0.90,
        last_rebalance_date=None,
        last_advised_beta=0.90,
        upshift_streak_days=0,
        downshift_streak_days=0,
    )

    raw = _build_beta_recommendation(
        selection=_selection_with_target(0.80, 0.10, 0.10),
        risk_decision=_risk(),
    )

    decision = module.build_advisory_rebalance_decision(
        raw_recommendation=raw,
        advisory_state=state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=False,
    )

    assert decision.should_adjust is False
    assert decision.advised_target_beta == pytest.approx(0.90)
    assert "within_no_trade_band" in decision.friction_blockers


def test_advisory_friction_respects_min_hold_days_for_non_emergency_upshift():
    module = importlib.import_module("src.engine.execution_policy")
    config = module.AdvisoryFrictionConfig(
        min_hold_days=15,
        upshift_confirmation_days=7,
    )
    state = module.AdvisoryState(
        assumed_beta=0.80,
        last_rebalance_date="2026-03-20",
        last_advised_beta=0.80,
        upshift_streak_days=7,
        downshift_streak_days=0,
    )

    raw = _build_beta_recommendation(
        selection=_selection_with_target(0.80, 0.10, 0.00),
        risk_decision=_risk(),
    )

    decision = module.build_advisory_rebalance_decision(
        raw_recommendation=raw,
        advisory_state=state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=False,
    )

    assert decision.should_adjust is False
    assert decision.advised_target_beta == pytest.approx(0.80)
    assert "min_hold_days" in decision.friction_blockers


def test_advisory_friction_requires_longer_confirmation_for_upshift_than_downshift():
    module = importlib.import_module("src.engine.execution_policy")
    config = module.AdvisoryFrictionConfig(
        upshift_confirmation_days=7,
        downshift_confirmation_days=3,
    )

    upshift_state = module.AdvisoryState(
        assumed_beta=0.80,
        last_rebalance_date=None,
        last_advised_beta=0.80,
        upshift_streak_days=3,
        downshift_streak_days=0,
    )
    upshift_raw = _build_beta_recommendation(
        selection=_selection_with_target(0.80, 0.10, 0.00),
        risk_decision=_risk(),
    )
    upshift_decision = module.build_advisory_rebalance_decision(
        raw_recommendation=upshift_raw,
        advisory_state=upshift_state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=False,
    )

    downshift_state = module.AdvisoryState(
        assumed_beta=1.00,
        last_rebalance_date=None,
        last_advised_beta=1.00,
        upshift_streak_days=0,
        downshift_streak_days=3,
    )
    downshift_raw = _build_beta_recommendation(
        selection=_selection_with_target(0.80, 0.00, 0.20),
        risk_decision=_risk(RiskState.RISK_REDUCED),
    )
    downshift_decision = module.build_advisory_rebalance_decision(
        raw_recommendation=downshift_raw,
        advisory_state=downshift_state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=False,
    )

    assert upshift_decision.should_adjust is False
    assert "upshift_confirmation" in upshift_decision.friction_blockers
    assert downshift_decision.should_adjust is True


def test_advisory_friction_caps_non_emergency_step_size():
    module = importlib.import_module("src.engine.execution_policy")
    config = module.AdvisoryFrictionConfig(
        downshift_confirmation_days=3,
        max_beta_step_down=0.20,
    )
    state = module.AdvisoryState(
        assumed_beta=1.00,
        last_rebalance_date=None,
        last_advised_beta=1.00,
        upshift_streak_days=0,
        downshift_streak_days=3,
    )
    raw = _build_beta_recommendation(
        selection=_selection_with_target(0.50, 0.00, 0.50),
        risk_decision=_risk(RiskState.RISK_EXIT, tier0_applied=True),
    )

    decision = module.build_advisory_rebalance_decision(
        raw_recommendation=raw,
        advisory_state=state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=False,
    )

    assert decision.should_adjust is True
    assert decision.advised_target_beta == pytest.approx(0.80)


def test_advisory_friction_emergency_override_bypasses_hold_and_step_limits():
    module = importlib.import_module("src.engine.execution_policy")
    config = module.AdvisoryFrictionConfig(
        min_hold_days=15,
        downshift_confirmation_days=3,
        max_beta_step_down=0.20,
    )
    state = module.AdvisoryState(
        assumed_beta=1.00,
        last_rebalance_date="2026-03-25",
        last_advised_beta=1.00,
        upshift_streak_days=0,
        downshift_streak_days=0,
    )
    raw = _build_beta_recommendation(
        selection=_selection_with_target(0.50, 0.00, 0.50),
        risk_decision=_risk(RiskState.RISK_EXIT, tier0_applied=True),
    )

    decision = module.build_advisory_rebalance_decision(
        raw_recommendation=raw,
        advisory_state=state,
        as_of_date="2026-03-26",
        config=config,
        emergency_override=True,
    )

    assert decision.should_adjust is True
    assert decision.advised_target_beta == pytest.approx(0.50)
    assert decision.friction_blockers == ()


def test_advisory_state_can_be_restored_from_history():
    module = importlib.import_module("src.engine.execution_policy")
    history = [
        {
            "date": "2026-03-25",
            "raw_target_beta": 1.00,
            "target_beta": 0.90,
            "assumed_beta_after": 0.90,
            "should_adjust": True,
            "rebalance_action": {"should_adjust": True, "reason": "advisory_upshift"},
        },
        {
            "date": "2026-03-24",
            "raw_target_beta": 0.90,
            "target_beta": 0.90,
            "assumed_beta_after": 0.90,
            "should_adjust": False,
            "rebalance_action": {"should_adjust": False, "reason": "within_no_trade_band"},
        },
    ]

    state = module.build_advisory_state_from_history(
        history=history,
        current_raw_target_beta=1.00,
        fallback_beta=0.80,
    )

    assert state.assumed_beta == pytest.approx(0.90)
    assert state.last_rebalance_date == "2026-03-25"
    assert state.upshift_streak_days >= 1


def test_target_allocation_from_beta_builds_continuous_advisory_mix():
    module = importlib.import_module("src.engine.execution_policy")

    reduced = module.target_allocation_from_beta(0.80)
    assert reduced.target_qqq_pct == pytest.approx(0.80)
    assert reduced.target_qld_pct == pytest.approx(0.00)
    assert reduced.target_cash_pct == pytest.approx(0.20)

    levered = module.target_allocation_from_beta(1.10)
    assert levered.target_qqq_pct == pytest.approx(0.90)
    assert levered.target_qld_pct == pytest.approx(0.10)
    assert levered.target_cash_pct == pytest.approx(0.00)
