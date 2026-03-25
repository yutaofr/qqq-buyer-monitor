"""TDD: Risk Controller — all state transitions + Class A degradation."""
from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state, RiskDecision
from src.models import CurrentPortfolioState
from src.models.risk import RiskState


def _snap(values: dict, quality: dict | None = None, full: bool = True) -> object:
    if full:
        # Baseline for Class A that ensures they are present and "clean"
        baseline = {
            "credit_spread": 300.0,
            "credit_acceleration": 0.0,
            "net_liquidity": 1000.0,
            "liquidity_roc": 0.0,
            "real_yield": 1.5,
            "funding_stress": False,
            "close": 400.0,
        }
        baseline.update(values)
        values = baseline

    return build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values=values,
        raw_quality=quality or {},
    )


# ── Task 5 ─────────────────────────────────────────────────────────────────────

def test_risk_controller_triple_stress_exits():
    """credit_accel > 15, liq_roc < -2, funding_stress=True → RISK_EXIT."""
    snap = _snap({
        "credit_acceleration": 18.0,
        "liquidity_roc": -3.0,
        "funding_stress": True,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_EXIT
    assert decision.target_cash_floor >= 0.70
    assert any("triple_stress" in str(r) for r in decision.reasons)


def test_risk_controller_dual_stress_defense():
    snap = _snap({
        "credit_spread": 550.0,   # danger
        "funding_stress": True,   # stress
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_DEFENSE


def test_risk_controller_single_stress_reduced():
    snap = _snap({
        "credit_spread": 420.0,   # warn zone
        "liquidity_roc": 0.5,     # fine
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_REDUCED


def test_risk_controller_clean_macro_neutral():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_NEUTRAL
    assert decision.target_exposure_ceiling == 0.90


def test_risk_decision_is_immutable():
    import pytest
    snap = _snap({"credit_spread": 300.0})
    decision = decide_risk_state(snap, CurrentPortfolioState())
    with pytest.raises((TypeError, AttributeError)):
        decision.risk_state = RiskState.RISK_EXIT  # type: ignore


def test_risk_controller_output_has_reasons():
    snap = _snap({
        "credit_acceleration": 20.0,
        "liquidity_roc": -4.0,
        "funding_stress": True,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState())
    assert len(decision.reasons) > 0


def test_risk_controller_exits_on_portfolio_drawdown_budget_breach():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    portfolio = CurrentPortfolioState(rolling_drawdown=0.31)
    decision = decide_risk_state(snap, portfolio, drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_EXIT
    assert any("drawdown_budget_breached" in str(r) for r in decision.reasons)


# ── Task 6 ─────────────────────────────────────────────────────────────────────

def test_risk_controller_degrades_conservatively_when_class_a_missing():
    """Multiple Class A features missing → at least RISK_REDUCED."""
    snap = _snap({
        "credit_spread": None,
        "liquidity_roc": None,
        "funding_stress": None,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state in {RiskState.RISK_REDUCED, RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}


def test_risk_controller_missing_data_capped_at_risk_reduced():
    """When Class A data is missing, we never go more bullish than RISK_REDUCED."""
    snap = _snap({
        "credit_spread": None,
        "net_liquidity": None,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state != RiskState.RISK_NEUTRAL
    assert decision.risk_state != RiskState.RISK_ON


def test_risk_controller_missing_data_reason_recorded():
    snap = _snap({
        "credit_spread": None,
        "liquidity_roc": None,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState())
    assert any("class_a_missing" in str(r) for r in decision.reasons)


def test_risk_controller_single_missing_class_a_still_evaluates():
    """A single None Class A feature (< 2 missing) should not immediately degrade."""
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": None,  # 1 missing — not enough to trigger degradation
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, CurrentPortfolioState())
    # Should still evaluate normally (clean → RISK_NEUTRAL)
    assert decision.risk_state in {RiskState.RISK_NEUTRAL, RiskState.RISK_REDUCED}


def test_risk_controller_only_consumes_class_a_data():
    """Class C data being present should not affect the risk decision."""
    snap_with_c = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
        "sector_rotation": 999.0,  # Class C — must be ignored
    })
    snap_without_c = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    d1 = decide_risk_state(snap_with_c, CurrentPortfolioState())
    d2 = decide_risk_state(snap_without_c, CurrentPortfolioState())
    assert d1.risk_state == d2.risk_state


def test_risk_controller_absent_class_a_features_degrade():
    """Absent Class A features (missing from snap) must be counted as missing."""
    # Entirely empty raw_values should result in all Class A being missing
    snap = _snap({}, full=False) 
    decision = decide_risk_state(snap, CurrentPortfolioState(), drawdown_budget=0.30)
    assert decision.risk_state in {RiskState.RISK_REDUCED, RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}
    assert any("class_a_missing" in str(r) for r in decision.reasons)
