"""TDD: Runtime Selector — deterministic selection, ceiling compliance, audit trail."""
from datetime import date

import pytest

from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.deployment_controller import DeploymentDecision
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import RiskDecision
from src.engine.runtime_selector import RuntimeSelection, choose_target_candidate
from src.models import CurrentPortfolioState
from src.models.candidate import CertifiedCandidate
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

FIXTURE = "tests/fixtures/candidate_registry_v7.json"


def _portfolio(qqq: float = 0.70, qld: float = 0.10, cash: float = 0.20) -> CurrentPortfolioState:
    return CurrentPortfolioState(
        qqq_pct=qqq,
        qld_pct=qld,
        current_cash_pct=cash,
        gross_exposure_pct=qqq + 2 * qld,
    )


def _risk(state: RiskState, ceiling: float = 0.90, cash_floor: float = 0.10) -> RiskDecision:
    return RiskDecision(state, ceiling, cash_floor, ())


def _deploy(state: DeploymentState = DeploymentState.DEPLOY_BASE) -> DeploymentDecision:
    return DeploymentDecision(state, 1.0, False, ())


# ── Task 11 ────────────────────────────────────────────────────────────────────

def test_runtime_selector_prefers_low_adjustment_cost():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)

    # Portfolio already at neutral-low-drift weights (qqq=0.80, qld=0.05, cash=0.15)
    portfolio = _portfolio(qqq=0.80, qld=0.05, cash=0.15)
    selection = choose_target_candidate(portfolio, _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    assert selection.selected_candidate.candidate_id == "neutral-low-drift"


def test_runtime_selector_is_deterministic():
    """Same inputs must always produce same selection (NFR-1)."""
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)
    portfolio = _portfolio()

    s1 = choose_target_candidate(portfolio, _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    s2 = choose_target_candidate(portfolio, _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    assert s1.selected_candidate.candidate_id == s2.selected_candidate.candidate_id


def test_runtime_selector_has_rejected_candidates_audit():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)
    selection = choose_target_candidate(_portfolio(), _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    # The non-selected candidate should appear in rejected list
    assert len(selection.rejected_candidates) >= 1
    rejected_ids = [r["candidate_id"] for r in selection.rejected_candidates]
    assert selection.selected_candidate.candidate_id not in rejected_ids


def test_runtime_selector_result_is_immutable():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)
    selection = choose_target_candidate(_portfolio(), _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    with pytest.raises((TypeError, AttributeError)):
        selection.selected_candidate = None  # type: ignore


def test_runtime_selector_filters_by_exposure_ceiling():
    """Candidate with exposure > ceiling must not be selected via fallback."""
    # Create a tight ceiling that only defense-style (low exposure) would fit
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)

    # Set ceiling so that exposure > 0.80 is rejected
    # neutral-base-001: 0.70 + 2*0.10 = 0.90 → rejected
    # neutral-low-drift: 0.80 + 2*0.05 = 0.90 → rejected (exactly at ceiling edge)
    tight_risk = RiskDecision(RiskState.RISK_NEUTRAL, 0.85, 0.15, ())
    with pytest.raises(ValueError, match="No compliant candidates"):
        choose_target_candidate(_portfolio(), tight_risk, _deploy(), candidates)


def test_runtime_selector_raises_on_empty_candidates():
    with pytest.raises(ValueError, match="No candidates"):
        choose_target_candidate(_portfolio(), _risk(RiskState.RISK_NEUTRAL), _deploy(), [])


def test_runtime_selector_returns_selection_score():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)
    selection = choose_target_candidate(_portfolio(), _risk(RiskState.RISK_NEUTRAL), _deploy(), candidates)
    assert isinstance(selection.selection_score, float)
    assert selection.selection_score >= 0.0
