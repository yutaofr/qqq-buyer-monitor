"""Integration: registry-backed runtime pipeline on the v8 surface."""
from __future__ import annotations

from datetime import date

from src.engine.allocation_search import find_best_allocation_v8
from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.deployment_controller import decide_deployment_state
from src.engine.execution_policy import build_beta_recommendation
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state
from src.engine.runtime_selector import RuntimeSelection
from src.engine.tier0_macro import assess_structural_regime
from src.models import (
    CurrentPortfolioState,
    Signal,
    SignalDetail,
    SignalResult,
    TargetAllocationState,
    Tier1Result,
    Tier2Result,
)
from src.models.risk import RiskState

FIXTURE_REGISTRY = "tests/fixtures/candidate_registry_v7.json"


def _detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _base_result() -> SignalResult:
    t1 = Tier1Result(
        score=50,
        drawdown_52w=_detail("dd"),
        ma200_deviation=_detail("ma"),
        vix=_detail("vix"),
        fear_greed=_detail("fg"),
        breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "none", None, None)
    return SignalResult(
        date=date(2026, 3, 24),
        price=450.0,
        signal=Signal.NO_SIGNAL,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="integration test",
    )


def _run_runtime_pipeline(
    values: dict,
    *,
    portfolio: CurrentPortfolioState | None = None,
    available_new_cash: float = 1000.0,
    forward_pe: float = 25.0,
    real_yield: float = 2.0,
):
    portfolio = portfolio or CurrentPortfolioState()
    result = _base_result()

    baseline = {
        "credit_spread": 300.0,
        "credit_acceleration": 0.0,
        "net_liquidity": 1000.0,
        "liquidity_roc": 0.0,
        "real_yield": real_yield,
        "funding_stress": False,
        "close": 450.0,
        "capitulation_score": 10,
        "tactical_stress_score": 10,
    }
    baseline.update(values)
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values=baseline,
        raw_quality={},
    )
    erp = (1.0 / forward_pe) * 100.0 - real_yield
    tier0_regime = assess_structural_regime(baseline.get("credit_spread"), erp)
    risk = decide_risk_state(snapshot, portfolio, tier0_regime=tier0_regime)
    deploy = decide_deployment_state(
        snapshot,
        risk,
        tier0_regime=tier0_regime,
        available_new_cash=available_new_cash,
    )

    registry = load_registry(FIXTURE_REGISTRY)
    candidates = select_runtime_candidates(registry, risk.risk_state)
    selected = find_best_allocation_v8(
        max_beta_ceiling=risk.target_exposure_ceiling,
        max_drawdown_budget=registry.drawdown_budget,
        candidates=candidates,
    )

    result.risk_state = risk.risk_state
    result.deployment_state = deploy.deployment_state
    result.registry_version = registry.registry_version
    result.tier0_regime = tier0_regime
    result.tier0_applied = risk.tier0_applied

    if selected is not None:
        recommendation = build_beta_recommendation(
            portfolio=portfolio,
            selection=RuntimeSelection(selected, (), 0.0),
            risk_decision=risk,
        )
        result.selected_candidate_id = selected.candidate_id
        result.target_beta = recommendation.target_beta
        result.should_adjust = recommendation.should_adjust
        result.target_allocation = TargetAllocationState(
            target_cash_pct=recommendation.recommended_cash_pct,
            target_qqq_pct=recommendation.recommended_qqq_pct,
            target_qld_pct=recommendation.recommended_qld_pct,
            target_beta=recommendation.target_beta,
        )
        result.rebalance_action = {"should_adjust": recommendation.should_adjust}
    else:
        result.logic_trace.append({"rule": "no_compliant_candidates"})

    return result


def test_runtime_pipeline_returns_risk_state():
    result = _run_runtime_pipeline({"credit_spread": 300.0, "funding_stress": False})
    assert result.risk_state is not None


def test_runtime_pipeline_returns_deployment_state():
    result = _run_runtime_pipeline({"credit_spread": 300.0, "funding_stress": False})
    assert result.deployment_state is not None


def test_runtime_pipeline_returns_selected_candidate_id_under_neutral():
    result = _run_runtime_pipeline({"credit_spread": 300.0, "funding_stress": False, "capitulation_score": 5})
    assert result.selected_candidate_id is not None


def test_runtime_pipeline_clean_macro_selects_neutral_candidate():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 250.0,
            "credit_acceleration": 2.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
        },
        forward_pe=20.0,
        real_yield=1.0,
    )
    assert result.risk_state == RiskState.RISK_NEUTRAL
    assert result.tier0_regime == "NEUTRAL"


def test_runtime_pipeline_rich_tightening_selects_beta_capped_candidate():
    result = _run_runtime_pipeline({
        "credit_spread": 320.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
        "capitulation_score": 20,
    })
    assert result.risk_state == RiskState.RISK_REDUCED
    assert result.selected_candidate_id == "reduced-tight-001"
    assert result.target_beta == 0.30


def test_runtime_pipeline_triple_stress_exits():
    result = _run_runtime_pipeline({
        "credit_acceleration": 20.0,
        "liquidity_roc": -5.0,
        "funding_stress": True,
        "credit_spread": 520.0,
    })
    assert result.risk_state == RiskState.RISK_EXIT


def test_runtime_pipeline_provides_registry_audit_surface():
    result = _run_runtime_pipeline({"credit_spread": 300.0, "funding_stress": False})
    assert result.registry_version is not None


def test_runtime_pipeline_degrades_explicitly_when_registry_missing():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_registry("/tmp/nonexistent_registry_for_integration_test.json")


def test_runtime_pipeline_no_compliant_candidates_records_trace():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 520.0,
            "credit_acceleration": 20.0,
            "liquidity_roc": -5.0,
            "funding_stress": True,
        }
    )
    assert any("no_compliant_candidates" in str(item) for item in result.logic_trace)
    assert result.selected_candidate_id is None
