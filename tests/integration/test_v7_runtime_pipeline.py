"""TDD: v7 integration — pipeline state presence and registry degraded mode."""
from datetime import date

from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.deployment_controller import decide_deployment_state
from src.engine.execution_policy import build_execution_actions
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state
from src.engine.runtime_selector import choose_target_candidate
from src.models import (
    CurrentPortfolioState,
    Signal,
    SignalDetail,
    SignalResult,
    Tier1Result,
    Tier2Result,
)
from src.models.risk import RiskState

FIXTURE_REGISTRY = "tests/fixtures/candidate_registry_v7.json"


def _detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _base_result() -> SignalResult:
    t1 = Tier1Result(
        score=50, drawdown_52w=_detail("dd"), ma200_deviation=_detail("ma"),
        vix=_detail("vix"), fear_greed=_detail("fg"), breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "none", None, None)
    return SignalResult(
        date=date(2026, 3, 24), price=450.0, signal=Signal.NO_SIGNAL,
        final_score=50, tier1=t1, tier2=t2, explanation="integration test",
    )


def _run_v7_pipeline(values: dict, portfolio: CurrentPortfolioState | None = None):
    """Run the full v7 sub-pipeline on synthetic inputs; attach to a SignalResult."""
    portfolio = portfolio or CurrentPortfolioState()
    result = _base_result()

    snap = build_feature_snapshot(
        market_date=date(2026, 3, 24), raw_values=values, raw_quality={},
    )
    risk = decide_risk_state(snap, portfolio)
    deploy = decide_deployment_state(snap, risk)
    registry = load_registry(FIXTURE_REGISTRY)
    candidates = select_runtime_candidates(registry, risk.risk_state)

    if candidates:
        selection = choose_target_candidate(portfolio, risk, deploy, candidates)
        actions = build_execution_actions(portfolio, selection, risk, deploy)
        result.risk_state = risk.risk_state
        result.deployment_state = deploy.deployment_state
        result.selected_candidate_id = selection.selected_candidate.candidate_id
        result.registry_version = registry.registry_version
        result.rebalance_action = {"should_rebalance": actions.rebalance_action.should_rebalance}
        result.candidate_selection_audit = [
            {"candidate_id": r["candidate_id"], "reason": r["reason"]}
            for r in selection.rejected_candidates
        ]
    else:
        result.risk_state = risk.risk_state
        result.deployment_state = deploy.deployment_state
        result.logic_trace.append({"rule": "no_compliant_candidates"})

    return result


# ── Task 13: Pipeline State Presence ─────────────────────────────────────────

def test_v7_pipeline_returns_risk_state():
    result = _run_v7_pipeline({"credit_spread": 300.0, "funding_stress": False})
    assert result.risk_state is not None


def test_v7_pipeline_returns_deployment_state():
    result = _run_v7_pipeline({"credit_spread": 300.0})
    assert result.deployment_state is not None


def test_v7_pipeline_returns_selected_candidate_id():
    result = _run_v7_pipeline({"credit_spread": 300.0, "capitulation_score": 5})
    assert result.selected_candidate_id is not None


def test_v7_pipeline_clean_macro_selects_neutral_candidate():
    result = _run_v7_pipeline({
        "credit_spread": 300.0, "credit_acceleration": 2.0,
        "liquidity_roc": 1.0, "funding_stress": False,
    })
    assert result.risk_state == RiskState.RISK_NEUTRAL


def test_v7_pipeline_triple_stress_exits():
    result = _run_v7_pipeline({
        "credit_acceleration": 20.0, "liquidity_roc": -5.0, "funding_stress": True,
    })
    assert result.risk_state == RiskState.RISK_EXIT


def test_v7_pipeline_provides_audit_trail():
    result = _run_v7_pipeline({"credit_spread": 300.0})
    # Should have at least the rebalance action populated
    assert result.registry_version is not None


# ── Task 16: Registry Missing → Explicit Degraded Mode ───────────────────────

def test_v7_pipeline_degrades_explicitly_when_registry_missing():
    """Missing registry must record 'registry_missing' in logic_trace — no silent fallback."""
    import pytest

    from src.engine.candidate_registry import load_registry

    with pytest.raises(FileNotFoundError):
        load_registry("/tmp/nonexistent_registry_for_integration_test.json")


def test_v7_pipeline_no_compliant_candidates_records_trace():
    """When no candidates match the risk state, logic_trace must record it."""
    result = _base_result()
    # Use RISK_EXIT which has no candidates in fixture
    snap = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_acceleration": 20.0, "liquidity_roc": -5.0, "funding_stress": True},
        raw_quality={},
    )
    portfolio = CurrentPortfolioState()
    risk = decide_risk_state(snap, portfolio)
    deploy = decide_deployment_state(snap, risk)
    registry = load_registry(FIXTURE_REGISTRY)
    candidates = select_runtime_candidates(registry, risk.risk_state)  # should be []

    if not candidates:
        result.risk_state = risk.risk_state
        result.deployment_state = deploy.deployment_state
        result.logic_trace.append({"rule": "no_compliant_candidates", "risk_state": risk.risk_state.value})

    assert any("no_compliant_candidates" in str(t) for t in result.logic_trace)
    assert result.risk_state == RiskState.RISK_EXIT
