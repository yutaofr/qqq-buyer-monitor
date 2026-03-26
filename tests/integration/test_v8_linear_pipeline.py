"""Integration: v8 linear pipeline from tier-0 to beta recommendation."""
from __future__ import annotations

from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.tier0_macro import assess_structural_regime
from src.models.candidate import CertifiedCandidate
from src.models.risk import RiskState


def _candidate(candidate_id: str, exposure: float, allowed_risk_state: RiskState) -> CertifiedCandidate:
    qld = max(0.0, exposure - 0.5)
    qqq = exposure - 2.0 * qld
    cash = 1.0 - qqq - qld
    return CertifiedCandidate(
        candidate_id=candidate_id,
        registry_version="v8-test-r1",
        allowed_risk_state=allowed_risk_state,
        qqq_pct=qqq,
        qld_pct=qld,
        cash_pct=cash,
        target_effective_exposure=exposure,
        certification_status="CERTIFIED",
        research_metrics={
            "cagr": 0.10,
            "max_drawdown": 0.12,
            "mean_interval_beta_deviation": 0.01,
        },
    )


def _snapshot(*, credit_spread: float, real_yield: float, forward_pe: float, capitulation_score: int) -> object:
    erp = (1.0 / forward_pe) * 100.0 - real_yield
    return erp, build_feature_snapshot(
        market_date=date(2026, 3, 25),
        raw_values={
            "credit_spread": credit_spread,
            "credit_acceleration": 0.0,
            "net_liquidity": 1000.0,
            "liquidity_roc": 1.0,
            "real_yield": real_yield,
            "funding_stress": False,
            "close": 400.0,
            "tactical_stress_score": 10,
            "capitulation_score": capitulation_score,
        },
        raw_quality={},
    )


def test_rich_tightening_without_capitulation_slows_deployment_and_caps_beta():
    from src.engine.allocation_search import find_best_allocation_v8
    from src.engine.deployment_controller import decide_deployment_state
    from src.engine.execution_policy import build_beta_recommendation
    from src.engine.risk_controller import decide_risk_state
    from src.engine.runtime_selector import RuntimeSelection

    erp, snapshot = _snapshot(credit_spread=470.0, real_yield=2.0, forward_pe=25.0, capitulation_score=20)
    tier0_regime = assess_structural_regime(credit_spread=470.0, erp=erp)

    risk = decide_risk_state(snapshot, tier0_regime=tier0_regime)
    deploy = decide_deployment_state(
        snapshot,
        risk,
        tier0_regime=tier0_regime,
        available_new_cash=1000.0,
    )
    selected = find_best_allocation_v8(
        max_beta_ceiling=risk.target_exposure_ceiling,
        candidates=[
            _candidate("reduced-050", 0.50, RiskState.RISK_REDUCED),
            _candidate("defense-030", 0.30, RiskState.RISK_DEFENSE),
        ],
    )
    beta = build_beta_recommendation(
        selection=RuntimeSelection(selected, (), 0.0),
        risk_decision=risk,
    )

    assert tier0_regime == "RICH_TIGHTENING"
    assert risk.risk_state == RiskState.RISK_REDUCED
    assert deploy.deployment_state == "DEPLOY_SLOW"
    assert beta.target_beta <= 0.50


def test_rich_tightening_with_capitulation_can_break_to_base():
    from src.engine.deployment_controller import decide_deployment_state
    from src.engine.risk_controller import decide_risk_state

    erp, snapshot = _snapshot(credit_spread=470.0, real_yield=2.0, forward_pe=25.0, capitulation_score=70)
    tier0_regime = assess_structural_regime(credit_spread=470.0, erp=erp)
    risk = decide_risk_state(snapshot, tier0_regime=tier0_regime)
    deploy = decide_deployment_state(
        snapshot,
        risk,
        tier0_regime=tier0_regime,
        available_new_cash=1000.0,
    )

    assert tier0_regime == "RICH_TIGHTENING"
    assert deploy.deployment_state == "DEPLOY_BASE"


def test_crisis_forces_exit_pause_and_cash_fallback():
    from src.engine.allocation_search import find_best_allocation_v8
    from src.engine.deployment_controller import decide_deployment_state
    from src.engine.risk_controller import decide_risk_state

    erp, snapshot = _snapshot(credit_spread=680.0, real_yield=2.0, forward_pe=25.0, capitulation_score=90)
    tier0_regime = assess_structural_regime(credit_spread=680.0, erp=erp)
    risk = decide_risk_state(snapshot, tier0_regime=tier0_regime)
    deploy = decide_deployment_state(
        snapshot,
        risk,
        tier0_regime=tier0_regime,
        available_new_cash=1000.0,
    )
    selected = find_best_allocation_v8(
        max_beta_ceiling=risk.target_exposure_ceiling,
        candidates=[_candidate("defense-030", 0.30, RiskState.RISK_DEFENSE)],
    )

    assert tier0_regime == "CRISIS"
    assert risk.risk_state == RiskState.RISK_EXIT
    assert risk.target_exposure_ceiling == 0.50
    assert deploy.deployment_state == "DEPLOY_PAUSE"
    assert selected is None
