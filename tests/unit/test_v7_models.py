"""TDD: v7.0 state enums and candidate model."""
from datetime import date

from src.models.audit import DecisionAudit
from src.models.candidate import CandidateRegistry, CertifiedCandidate
from src.models.deployment import DeploymentState
from src.models.risk import RiskState


def test_v7_state_enums_and_candidate_model():
    cand = CertifiedCandidate(
        candidate_id="base-001",
        registry_version="test-r1",
        allowed_risk_state=RiskState.RISK_NEUTRAL,
        qqq_pct=0.7,
        qld_pct=0.1,
        cash_pct=0.2,
        target_effective_exposure=0.9,
        certification_status="CERTIFIED",
        research_metrics={"max_drawdown": 0.22},
    )
    assert RiskState.RISK_NEUTRAL.value == "RISK_NEUTRAL"
    assert DeploymentState.DEPLOY_BASE.value == "DEPLOY_BASE"
    assert cand.target_effective_exposure == 0.9
    assert cand.allowed_risk_state == RiskState.RISK_NEUTRAL


def test_risk_state_all_values():
    values = {s.value for s in RiskState}
    assert values == {"RISK_ON", "RISK_NEUTRAL", "RISK_REDUCED", "RISK_DEFENSE", "RISK_EXIT"}


def test_deployment_state_all_values():
    values = {s.value for s in DeploymentState}
    assert values == {"DEPLOY_BASE", "DEPLOY_SLOW", "DEPLOY_FAST", "DEPLOY_PAUSE", "DEPLOY_RECOVER"}


def test_risk_and_deployment_states_are_independent_types():
    """RiskState and DeploymentState must NOT be interchangeable."""
    assert not issubclass(RiskState, DeploymentState)
    assert not issubclass(DeploymentState, RiskState)


def test_certified_candidate_is_immutable():
    cand = CertifiedCandidate(
        candidate_id="test",
        registry_version="v1",
        allowed_risk_state=RiskState.RISK_ON,
        qqq_pct=0.9,
        qld_pct=0.0,
        cash_pct=0.1,
        target_effective_exposure=0.9,
        certification_status="CERTIFIED",
        research_metrics={},
    )
    import pytest
    with pytest.raises((TypeError, AttributeError)):
        cand.qqq_pct = 0.5  # type: ignore


def test_candidate_registry_structure():
    reg = CandidateRegistry(
        registry_version="2026-03-24-v7.0-r1",
        generated_at="2026-03-24T12:00:00Z",
        drawdown_budget=0.30,
        candidates=(),
    )
    assert reg.registry_version == "2026-03-24-v7.0-r1"
    assert reg.drawdown_budget == 0.30


def test_decision_audit_structure():
    audit = DecisionAudit(
        market_date=date(2026, 3, 24),
        risk_state=RiskState.RISK_NEUTRAL,
        deployment_state=DeploymentState.DEPLOY_BASE,
        selected_candidate_id="base-001",
        evidence_trace=({"rule": "clean_macro"},),
        data_quality={"credit_spread": {"source": "live"}},
        rejected_candidates=(),
    )
    assert audit.risk_state == RiskState.RISK_NEUTRAL
    assert audit.selected_candidate_id == "base-001"


def test_models_re_exported_from_package():
    """v7 types must be importable from the top-level models package."""
    from src.models import DeploymentState as DS
    from src.models import RiskState as RS
    assert RS.RISK_ON.value == "RISK_ON"
    assert DS.DEPLOY_BASE.value == "DEPLOY_BASE"
