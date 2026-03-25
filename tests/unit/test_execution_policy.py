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
    builder = getattr(module, "build_beta_recommendation")
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
