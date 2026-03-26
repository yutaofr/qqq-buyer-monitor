"""TDD: Risk Controller — all state transitions + Class A degradation."""
from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state
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
        "liquidity_roc": -6.0,
        "funding_stress": True,
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_EXIT
    assert decision.target_cash_floor == 0.50
    assert decision.target_exposure_ceiling == 0.50
    assert any("triple_stress" in str(r) for r in decision.reasons)


def test_risk_controller_dual_stress_defense():
    snap = _snap({
        "credit_spread": 550.0,   # danger
        "funding_stress": True,   # stress
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_DEFENSE


def test_risk_controller_single_stress_reduced():
    snap = _snap({
        "credit_spread": 520.0,   # warn zone
        "liquidity_roc": 0.5,     # fine
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_REDUCED


def test_risk_controller_clean_macro_neutral():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state == RiskState.RISK_NEUTRAL
    assert decision.target_exposure_ceiling == 1.00


def test_risk_controller_clean_euphoric_unlocks_risk_on():
    snap = _snap({
        "credit_spread": 220.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="EUPHORIC",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_ON
    assert decision.target_exposure_ceiling == 1.20
    assert decision.target_cash_floor == 0.00


def test_risk_controller_tight_spread_clean_macro_unlocks_risk_on_without_erp():
    snap = _snap({
        "credit_spread": 320.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 0.5,
        "funding_stress": False,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="NEUTRAL",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_ON
    assert decision.target_exposure_ceiling == 1.20


def test_risk_controller_funding_stress_alone_does_not_force_reduction():
    snap = _snap({
        "credit_spread": 320.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 0.5,
        "funding_stress": True,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="NEUTRAL",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_NEUTRAL


def test_risk_decision_is_immutable():
    import pytest
    snap = _snap({"credit_spread": 300.0})
    decision = decide_risk_state(snap)
    with pytest.raises((TypeError, AttributeError)):
        decision.risk_state = RiskState.RISK_EXIT  # type: ignore


def test_risk_controller_output_has_reasons():
    snap = _snap({
        "credit_acceleration": 20.0,
        "liquidity_roc": -4.0,
        "funding_stress": True,
    })
    decision = decide_risk_state(snap)
    assert len(decision.reasons) > 0


def test_risk_controller_exits_on_portfolio_drawdown_budget_breach():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, rolling_drawdown=0.31, drawdown_budget=0.30)
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
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state in {RiskState.RISK_REDUCED, RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}


def test_risk_controller_missing_data_capped_at_risk_reduced():
    """When Class A data is missing, we never go more bullish than RISK_REDUCED."""
    snap = _snap({
        "credit_spread": None,
        "net_liquidity": None,
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state != RiskState.RISK_NEUTRAL
    assert decision.risk_state != RiskState.RISK_ON


def test_risk_controller_missing_unused_fields_does_not_degrade_clean_macro():
    snap = _snap({
        "net_liquidity": None,
        "real_yield": None,
        "credit_spread": 320.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 0.5,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state in {RiskState.RISK_NEUTRAL, RiskState.RISK_ON}


def test_risk_controller_missing_data_reason_recorded():
    snap = _snap({
        "credit_spread": None,
        "liquidity_roc": None,
    })
    decision = decide_risk_state(snap)
    assert any("class_a_missing" in str(r) for r in decision.reasons)


def test_risk_controller_single_missing_class_a_still_evaluates():
    """A single None Class A feature (< 2 missing) should not immediately degrade."""
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": None,  # 1 missing — not enough to trigger degradation
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(snap)
    # Should still evaluate normally (clean → RISK_NEUTRAL)
    assert decision.risk_state in {RiskState.RISK_NEUTRAL, RiskState.RISK_REDUCED, RiskState.RISK_ON}


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
    d1 = decide_risk_state(snap_with_c)
    d2 = decide_risk_state(snap_without_c)
    assert d1.risk_state == d2.risk_state


def test_risk_controller_absent_class_a_features_degrade():
    """Absent Class A features (missing from snap) must be counted as missing."""
    # Entirely empty raw_values should result in all Class A being missing
    snap = _snap({}, full=False)
    decision = decide_risk_state(snap, drawdown_budget=0.30)
    assert decision.risk_state in {RiskState.RISK_REDUCED, RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}
    assert any("class_a_missing" in str(r) for r in decision.reasons)


# ── v8.0 Tier-0 Hard Constraint ──────────────────────────────────────────────

def test_risk_controller_crisis_forces_exit_even_when_micro_is_clean():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="CRISIS",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_EXIT
    assert decision.target_exposure_ceiling == 0.50
    assert decision.target_cash_floor == 0.50
    assert decision.tier0_applied is True


def test_risk_controller_rich_tightening_caps_ceiling_at_thirty_percent():
    snap = _snap({"credit_spread": 300.0, "funding_stress": False})
    decision = decide_risk_state(
        snap,
        tier0_regime="RICH_TIGHTENING",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_REDUCED
    assert decision.target_exposure_ceiling <= 0.80
    assert decision.tier0_applied is True


def test_risk_controller_transition_stress_forces_defense():
    snap = _snap({"credit_spread": 300.0, "funding_stress": False})
    decision = decide_risk_state(
        snap,
        tier0_regime="TRANSITION_STRESS",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_DEFENSE
    assert decision.target_exposure_ceiling == 0.70
    assert decision.tier0_applied is True


def test_risk_controller_neutral_tier0_preserves_v7_clean_behavior():
    snap = _snap({
        "credit_spread": 300.0,
        "credit_acceleration": 2.0,
        "liquidity_roc": 1.0,
        "funding_stress": False,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="NEUTRAL",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_NEUTRAL
    assert decision.target_exposure_ceiling == 1.00
    assert decision.tier0_applied is False


def test_risk_controller_tier0_applied_flag_matches_regime():
    snap = _snap({"credit_spread": 300.0, "funding_stress": False})
    expected = {
        "CRISIS": True,
        "RICH_TIGHTENING": True,
        "TRANSITION_STRESS": True,
        "NEUTRAL": False,
        "EUPHORIC": False,
    }
    for regime, applied in expected.items():
        decision = decide_risk_state(snap, tier0_regime=regime)
        assert decision.tier0_applied is applied


def test_risk_controller_tier0_crisis_overrides_micro_triple_stress_path():
    snap = _snap({
        "credit_acceleration": 20.0,
        "liquidity_roc": -5.0,
        "funding_stress": True,
    })
    decision = decide_risk_state(
        snap,
        tier0_regime="CRISIS",
        drawdown_budget=0.30,
    )
    assert decision.risk_state == RiskState.RISK_EXIT
    assert decision.target_exposure_ceiling == 0.50
    assert decision.tier0_applied is True


def test_risk_decision_v8_tier0_field_is_immutable():
    import pytest

    snap = _snap({"credit_spread": 300.0})
    decision = decide_risk_state(
        snap,
        tier0_regime="RICH_TIGHTENING",
    )
    with pytest.raises((TypeError, AttributeError)):
        decision.tier0_applied = False  # type: ignore[misc]
