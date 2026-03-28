"""Integration: registry-backed runtime pipeline on the v8 surface."""
from __future__ import annotations

from datetime import date

import pytest

from src.engine.allocation_search import select_candidate_with_floor_fallback_v8
from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.cycle_factor import decide_cycle_state
from src.engine.deployment_controller import decide_deployment_state
from src.engine.execution_policy import (
    build_advisory_rebalance_decision,
    build_advisory_state_from_history,
    build_beta_recommendation,
    target_allocation_from_beta,
)
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state
from src.engine.runtime_selector import RuntimeSelection
from src.engine.tier0_macro import assess_structural_regime
from src.models import (
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
    history: list[dict] | None = None,
    available_new_cash: float = 1000.0,
    forward_pe: float = 25.0,
    real_yield: float = 2.0,
):
    result = _base_result()

    baseline = {
        "credit_spread": 300.0,
        "credit_acceleration": 0.0,
        "net_liquidity": 1000.0,
        "liquidity_roc": 0.0,
        "real_yield": real_yield,
        "funding_stress": False,
        "close": 450.0,
        "breadth": 0.50,
        "price_vs_ma200": 0.02,
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
    snapshot.values["erp"] = erp
    cycle = decide_cycle_state(snapshot)
    tier0_regime = assess_structural_regime(baseline.get("credit_spread"), erp)
    risk = decide_risk_state(snapshot, tier0_regime=tier0_regime, cycle_decision=cycle)
    deploy = decide_deployment_state(
        snapshot,
        risk,
        tier0_regime=tier0_regime,
        available_new_cash=available_new_cash,
    )

    registry = load_registry(FIXTURE_REGISTRY)
    candidates = select_runtime_candidates(registry, risk.risk_state)
    selected, used_floor_fallback = select_candidate_with_floor_fallback_v8(
        scoped_candidates=candidates,
        registry_candidates=list(registry.candidates),
        max_beta_ceiling=risk.target_exposure_ceiling,
        qld_share_ceiling=risk.qld_share_ceiling,
        max_drawdown_budget=registry.drawdown_budget,
    )

    result.risk_state = risk.risk_state
    result.deployment_state = deploy.deployment_state
    result.cycle_regime = cycle.cycle_regime.value
    result.registry_version = registry.registry_version
    result.tier0_regime = tier0_regime
    result.tier0_applied = risk.tier0_applied
    primary_reason = deploy.reasons[0] if deploy.reasons else {}
    blood_chip_reason = next(
        (
            reason
            for reason in deploy.reasons
            if reason.get("rule") == "blood_chip_crisis_override"
        ),
        primary_reason,
    )
    result.deployment_action = {
        "deploy_mode": deploy.deployment_state.value.replace("DEPLOY_", ""),
        "reason": primary_reason.get("rule", "controller_decision"),
        "blood_chip_override_active": blood_chip_reason.get("rule") == "blood_chip_crisis_override",
        "path": blood_chip_reason.get("path"),
    }

    if selected is not None:
        recommendation = build_beta_recommendation(
            selection=RuntimeSelection(selected, (), 0.0),
            risk_decision=risk,
        )
        advisory_state = build_advisory_state_from_history(
            history=history or [],
            current_raw_target_beta=recommendation.target_beta,
            fallback_beta=recommendation.target_beta,
        )
        advisory_decision = build_advisory_rebalance_decision(
            raw_recommendation=recommendation,
            advisory_state=advisory_state,
            as_of_date=result.date,
            emergency_override=tier0_regime == "CRISIS",
        )
        result.selected_candidate_id = selected.candidate_id
        result.raw_target_beta = recommendation.target_beta
        result.target_beta = advisory_decision.advised_target_beta
        result.assumed_beta_before = advisory_decision.assumed_beta_before
        result.assumed_beta_after = advisory_decision.assumed_beta_after
        result.friction_blockers = list(advisory_decision.friction_blockers)
        result.estimated_turnover = advisory_decision.estimated_turnover
        result.estimated_cost_drag = advisory_decision.estimated_cost_drag
        result.should_adjust = advisory_decision.should_adjust
        result.target_allocation = target_allocation_from_beta(
            advisory_decision.advised_target_beta,
            qld_share_ceiling=risk.qld_share_ceiling,
        )
        result.rebalance_action = {
            "should_adjust": advisory_decision.should_adjust,
            "reason": advisory_decision.adjustment_reason,
        }
        if used_floor_fallback:
            result.logic_trace.append({"rule": "global_beta_floor_fallback", "candidate_id": selected.candidate_id})
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
            "breadth": 0.50,
            "price_vs_ma200": 0.03,
        },
        forward_pe=20.0,
        real_yield=1.0,
    )
    assert result.risk_state == RiskState.RISK_NEUTRAL
    assert result.cycle_regime == "MID_CYCLE"
    assert result.tier0_regime == "NEUTRAL"


def test_runtime_pipeline_mid_cycle_prefers_pure_qqq_candidate():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 300.0,
            "credit_acceleration": 2.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
            "breadth": 0.50,
            "price_vs_ma200": 0.03,
        },
        forward_pe=20.0,
        real_yield=1.0,
    )

    assert result.risk_state == RiskState.RISK_NEUTRAL
    assert result.cycle_regime == "MID_CYCLE"
    assert result.selected_candidate_id == "neutral-core-001"
    assert result.target_beta == pytest.approx(0.90)
    assert result.target_allocation.target_qqq_pct == pytest.approx(0.90)
    assert result.target_allocation.target_qld_pct == pytest.approx(0.00)
    assert result.target_allocation.target_cash_pct == pytest.approx(0.10)


def test_runtime_pipeline_recovery_allows_limited_qld_candidate():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 420.0,
            "credit_acceleration": -8.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
            "breadth": 0.45,
            "price_vs_ma200": -0.01,
            "capitulation_score": 15,
        },
        forward_pe=20.0,
        real_yield=1.0,
    )
    assert result.risk_state == RiskState.RISK_NEUTRAL
    assert result.cycle_regime == "RECOVERY"
    assert result.selected_candidate_id == "recovery-limited-001"
    assert result.target_allocation.target_qld_pct == pytest.approx(0.10)
    assert result.target_allocation.target_qqq_pct == pytest.approx(0.80)
    assert result.target_allocation.target_cash_pct == pytest.approx(0.10)


def test_runtime_pipeline_late_cycle_selects_pure_qqq_beta_capped_candidate():
    result = _run_runtime_pipeline({
        "credit_spread": 470.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
        "breadth": 0.30,
        "price_vs_ma200": -0.03,
        "capitulation_score": 20,
    })
    assert result.risk_state == RiskState.RISK_REDUCED
    assert result.cycle_regime == "LATE_CYCLE"
    assert result.selected_candidate_id == "reduced-tight-001"
    assert result.target_beta == pytest.approx(0.80)
    assert result.raw_target_beta == pytest.approx(0.80)
    assert result.target_allocation.target_qqq_pct == pytest.approx(0.80)
    assert result.target_allocation.target_qld_pct == pytest.approx(0.00)
    assert result.target_allocation.target_cash_pct == pytest.approx(0.20)


def test_runtime_pipeline_triple_stress_exits():
    result = _run_runtime_pipeline({
        "credit_acceleration": 20.0,
        "liquidity_roc": -5.0,
        "funding_stress": True,
        "credit_spread": 680.0,
    })
    assert result.risk_state == RiskState.RISK_EXIT


def test_runtime_pipeline_capitulation_unlocks_risk_on_limited_qld():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 620.0,
            "credit_acceleration": -5.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
            "breadth": 0.25,
            "price_vs_ma200": -0.10,
            "capitulation_score": 40,
            "rolling_drawdown": 0.20,
        },
        forward_pe=15.0,
        real_yield=1.0,
    )
    assert result.risk_state == RiskState.RISK_ON
    assert result.cycle_regime == "CAPITULATION"
    assert result.selected_candidate_id == "capitulation-max-001"
    assert result.target_allocation.target_qld_pct == pytest.approx(0.25)


def test_runtime_pipeline_provides_registry_audit_surface():
    result = _run_runtime_pipeline({"credit_spread": 300.0, "funding_stress": False})
    assert result.registry_version is not None


def test_runtime_pipeline_degrades_explicitly_when_registry_missing():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_registry("/tmp/nonexistent_registry_for_integration_test.json")


def test_runtime_pipeline_exit_state_keeps_beta_floor_candidate():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 680.0,
            "credit_acceleration": 20.0,
            "liquidity_roc": -5.0,
            "funding_stress": True,
        }
    )
    assert result.risk_state == RiskState.RISK_EXIT
    assert result.selected_candidate_id == "exit-floor-001"
    assert result.target_beta == 0.50
    assert result.target_allocation.target_qld_pct == pytest.approx(0.0)


def test_runtime_pipeline_crisis_blood_chip_override_keeps_beta_floor_but_deploys_fast():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 680.0,
            "credit_acceleration": -1.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
            "capitulation_score": 20,
            "rolling_drawdown": 0.18,
            "five_day_return": -0.03,
            "twenty_day_return": -0.10,
        }
    )
    assert result.risk_state == RiskState.RISK_EXIT
    assert result.selected_candidate_id == "exit-floor-001"
    assert result.deployment_state.value == "DEPLOY_FAST"
    assert result.target_beta == pytest.approx(0.5)
    assert result.deployment_action["reason"] == "blood_chip_crisis_override"
    assert result.deployment_action["blood_chip_override_active"] is True
    assert result.deployment_action["path"] == "liquidity_reversal"


def test_runtime_pipeline_exposes_raw_and_advised_beta_separately():
    result = _run_runtime_pipeline(
        {
            "credit_spread": 250.0,
            "credit_acceleration": 2.0,
            "liquidity_roc": 1.0,
            "funding_stress": False,
        },
        history=[
            {
                "date": "2026-03-20",
                "raw_target_beta": 0.80,
                "target_beta": 0.80,
                "assumed_beta_after": 0.80,
                "should_adjust": True,
                "rebalance_action": {"should_adjust": True, "reason": "advisory_upshift"},
            }
        ],
        forward_pe=20.0,
        real_yield=1.0,
    )
    assert result.raw_target_beta == pytest.approx(0.9)
    assert result.target_beta == pytest.approx(0.8)
    assert result.should_adjust is False
    assert "upshift_confirmation" in result.friction_blockers or "min_hold_days" in result.friction_blockers
