from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.signal.behavioral_guard import BehavioralGuard


def _allocation(beta: float, qqq: float, qld: float, cash: float) -> PositionSizingResult:
    return PositionSizingResult(
        target_beta=beta,
        raw_target_beta=beta,
        entropy=0.1,
        uncertainty_penalty=0.05,
        reference_capital=100_000.0,
        current_nav=100_000.0,
        risk_budget_dollars=beta * 100_000.0,
        qqq_dollars=qqq,
        qld_notional_dollars=qld,
        cash_dollars=cash,
        qld_share=0.0 if (qqq + qld) == 0 else qld / (qqq + qld),
    )


def test_behavioral_guard_holds_cooldown_on_next_cycle():
    guard = BehavioralGuard(initial_bucket="QQQ", settlement_days=1)

    first = guard.apply(_allocation(0.30, 0.0, 0.0, 100_000.0))
    assert first.target_bucket == "CASH"
    assert first.action_required is True

    second = guard.apply(_allocation(1.10, 0.0, 100_000.0, 0.0))
    assert second.lock_active is True
    assert second.target_bucket == "CASH"
    assert "SETTLEMENT_LOCKED" in second.reason


def test_behavioral_guard_forced_cash_updates_internal_state():
    guard = BehavioralGuard(initial_bucket="QLD", settlement_days=1)

    forced = guard.apply(
        _allocation(1.10, 0.0, 100_000.0, 0.0),
        forced_bucket="CASH",
        forced_reason="CRITICAL: DATA CORRUPTION. FORCED CASH.",
    )
    assert forced.target_bucket == "CASH"
    assert forced.action_required is True
    assert guard.current_bucket == "CASH"

    recovered = guard.apply(_allocation(0.35, 0.0, 0.0, 100_000.0))
    assert recovered.target_bucket == "CASH"


def test_behavioral_guard_uses_deadband_to_avoid_whipsaw():
    guard = BehavioralGuard(initial_bucket="QQQ", settlement_days=0)

    stay_put = guard.apply(_allocation(0.82, 82_000.0, 0.0, 18_000.0))
    assert stay_put.target_bucket == "QQQ"
    assert stay_put.action_required is False
