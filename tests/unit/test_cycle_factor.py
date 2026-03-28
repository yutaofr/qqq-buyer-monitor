"""TDD: v10 cycle factor classifier."""
from __future__ import annotations

from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot


def _snapshot(values: dict) -> object:
    baseline = {
        "credit_spread": 320.0,
        "credit_acceleration": 0.0,
        "liquidity_roc": 0.0,
        "funding_stress": False,
        "breadth": 0.50,
        "price_vs_ma200": 0.01,
        "rolling_drawdown": 0.06,
        "erp": 3.2,
        "close": 400.0,
    }
    baseline.update(values)
    return build_feature_snapshot(
        market_date=date(2026, 3, 29),
        raw_values=baseline,
        raw_quality={},
    )


def test_cycle_factor_detects_late_cycle_and_locks_qld():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(
        _snapshot(
            {
                "credit_spread": 470.0,
                "credit_acceleration": 4.0,
                "breadth": 0.35,
                "price_vs_ma200": -0.03,
                "erp": 2.1,
            }
        )
    )

    assert decision.cycle_regime.value == "LATE_CYCLE"
    assert decision.target_exposure_ceiling == 0.80
    assert decision.qld_share_ceiling == 0.0


def test_cycle_factor_detects_bust_and_forces_exit_floor():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(
        _snapshot(
            {
                "credit_spread": 680.0,
                "credit_acceleration": 20.0,
                "liquidity_roc": -6.0,
                "funding_stress": True,
                "breadth": 0.25,
                "price_vs_ma200": -0.12,
                "rolling_drawdown": 0.22,
                "erp": 3.0,
            }
        )
    )

    assert decision.cycle_regime.value == "BUST"
    assert decision.target_exposure_ceiling == 0.50
    assert decision.qld_share_ceiling == 0.0


def test_cycle_factor_detects_capitulation_and_unlocks_tactical_qld():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(
        _snapshot(
            {
                "credit_spread": 620.0,
                "credit_acceleration": -5.0,
                "liquidity_roc": 1.0,
                "breadth": 0.25,
                "price_vs_ma200": -0.10,
                "rolling_drawdown": 0.20,
                "erp": 5.2,
            }
        )
    )

    assert decision.cycle_regime.value == "CAPITULATION"
    assert decision.target_exposure_ceiling == 1.20
    assert decision.qld_share_ceiling == 0.25


def test_cycle_factor_detects_recovery_and_keeps_qld_limited():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(
        _snapshot(
            {
                "credit_spread": 420.0,
                "credit_acceleration": -8.0,
                "liquidity_roc": 0.8,
                "breadth": 0.45,
                "price_vs_ma200": -0.01,
                "rolling_drawdown": 0.10,
                "erp": 4.0,
            }
        )
    )

    assert decision.cycle_regime.value == "RECOVERY"
    assert decision.target_exposure_ceiling == 1.00
    assert decision.qld_share_ceiling == 0.10


def test_cycle_factor_defaults_to_mid_cycle_without_extremes():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(_snapshot({}))

    assert decision.cycle_regime.value == "MID_CYCLE"
    assert decision.target_exposure_ceiling == 0.90
    assert decision.qld_share_ceiling == 0.0


def test_cycle_factor_fails_closed_when_core_cycle_data_is_missing():
    from src.engine.cycle_factor import decide_cycle_state

    decision = decide_cycle_state(
        _snapshot(
            {
                "breadth": None,
                "price_vs_ma200": None,
                "erp": None,
            }
        )
    )

    assert decision.cycle_regime.value == "UNQUALIFIED"
    assert decision.target_exposure_ceiling == 0.80
    assert decision.qld_share_ceiling == 0.0
