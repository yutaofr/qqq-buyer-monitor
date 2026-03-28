"""TDD: SignalResult v7 field extension (Task 2)."""
from datetime import date

from src.models import Signal, SignalDetail, SignalResult, Tier1Result, Tier2Result
from src.models.deployment import DeploymentState
from src.models.risk import RiskState


def _make_signal_detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _make_tier1() -> Tier1Result:
    return Tier1Result(
        score=0,
        drawdown_52w=_make_signal_detail("dd"),
        ma200_deviation=_make_signal_detail("ma"),
        vix=_make_signal_detail("vix"),
        fear_greed=_make_signal_detail("fg"),
        breadth=_make_signal_detail("br"),
    )


def _make_tier2() -> Tier2Result:
    return Tier2Result(0, None, None, None, False, False, False, True, "none", None, None)


def test_signal_result_supports_v7_fields():
    t1 = _make_tier1()
    t2 = _make_tier2()
    result = SignalResult(
        date=date(2026, 3, 24),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="",
        risk_state=RiskState.RISK_NEUTRAL,
        deployment_state=DeploymentState.DEPLOY_BASE,
    )
    assert result.risk_state == RiskState.RISK_NEUTRAL
    assert result.deployment_state == DeploymentState.DEPLOY_BASE


def test_signal_result_v7_fields_default_to_none():
    """Legacy construction without v7 fields must still work."""
    t1 = _make_tier1()
    t2 = _make_tier2()
    result = SignalResult(
        date=date(2026, 3, 24),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="",
    )
    assert result.risk_state is None
    assert result.deployment_state is None
    assert result.selected_candidate_id is None
    assert result.registry_version is None
    assert result.rebalance_action == {}
    assert result.deployment_action == {}
    assert result.candidate_selection_audit == []
    assert result.cycle_regime is None
    assert result.cycle_reasons == []
    assert result.tier0_regime is None
    assert result.tier0_applied is False
    assert result.raw_target_beta is None
    assert result.target_beta is None
    assert result.target_exposure_ceiling is None
    assert result.target_cash_floor is None
    assert result.qld_share_ceiling is None
    assert result.assumed_beta_before is None
    assert result.assumed_beta_after is None
    assert result.friction_blockers == []
    assert result.estimated_turnover is None
    assert result.estimated_cost_drag is None
    assert result.should_adjust is None


def test_signal_result_v7_full_fields():
    t1 = _make_tier1()
    t2 = _make_tier2()
    result = SignalResult(
        date=date(2026, 3, 24),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="",
        risk_state=RiskState.RISK_DEFENSE,
        deployment_state=DeploymentState.DEPLOY_PAUSE,
        selected_candidate_id="defense-001",
        registry_version="2026-03-24-v7.0-r1",
        rebalance_action={"should_adjust": True, "reason": "risk_state_change"},
        deployment_action={"deploy_mode": "PAUSE", "reason": "risk_ceiling"},
        candidate_selection_audit=[{"candidate_id": "defense-001", "selected": True}],
    )
    assert result.risk_state == RiskState.RISK_DEFENSE
    assert result.selected_candidate_id == "defense-001"
    assert result.rebalance_action["should_adjust"] is True
    assert len(result.candidate_selection_audit) == 1


def test_signal_result_supports_v8_linear_pipeline_fields():
    t1 = _make_tier1()
    t2 = _make_tier2()
    result = SignalResult(
        date=date(2026, 3, 24),
        price=100.0,
        signal=Signal.NO_SIGNAL,
        final_score=0,
        tier1=t1,
        tier2=t2,
        explanation="",
        cycle_regime="LATE_CYCLE",
        tier0_regime="RICH_TIGHTENING",
        tier0_applied=True,
        raw_target_beta=0.50,
        target_beta=0.30,
        target_exposure_ceiling=0.80,
        target_cash_floor=0.20,
        qld_share_ceiling=0.10,
        assumed_beta_before=0.50,
        assumed_beta_after=0.30,
        friction_blockers=["max_beta_step"],
        estimated_turnover=0.20,
        estimated_cost_drag=0.003,
        should_adjust=True,
    )
    assert result.cycle_regime == "LATE_CYCLE"
    assert result.tier0_regime == "RICH_TIGHTENING"
    assert result.tier0_applied is True
    assert result.raw_target_beta == 0.50
    assert result.target_beta == 0.30
    assert result.target_exposure_ceiling == 0.80
    assert result.target_cash_floor == 0.20
    assert result.qld_share_ceiling == 0.10
    assert result.assumed_beta_before == 0.50
    assert result.assumed_beta_after == 0.30
    assert result.friction_blockers == ["max_beta_step"]
    assert result.estimated_turnover == 0.20
    assert result.estimated_cost_drag == 0.003
    assert result.should_adjust is True
