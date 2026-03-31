from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.signal.behavioral_guard import BehavioralGuard


def _sizing(beta: float, entropy: float) -> PositionSizingResult:
    qld_notional = max(0.0, beta - 1.0) * 100_000.0
    qqq_dollars = 100_000.0 if beta > 1.0 else beta * 100_000.0
    cash_dollars = 0.0 if beta > 1.0 else (1.0 - beta) * 100_000.0
    invested = qqq_dollars + qld_notional
    qld_share = qld_notional / invested if invested > 0 else 0.0
    return PositionSizingResult(
        target_beta=beta,
        raw_target_beta=beta,
        entropy=entropy,
        uncertainty_penalty=0.0,
        reference_capital=100_000.0,
        current_nav=100_000.0,
        risk_budget_dollars=beta * 100_000.0,
        qqq_dollars=qqq_dollars,
        qld_notional_dollars=qld_notional,
        cash_dollars=cash_dollars,
        qld_share=qld_share,
    )


def test_behavioral_guard_requires_accumulated_evidence_near_boundary():
    guard = BehavioralGuard(initial_bucket="QQQ", evidence=0.0)

    for _ in range(8):
        decision = guard.apply(_sizing(1.01, 0.2))
        assert decision.target_bucket == "QQQ"
        assert decision.action_required is False
        assert decision.reason.startswith("EVIDENCE_HOLD")

    decision = guard.apply(_sizing(1.01, 0.2))

    assert decision.target_bucket == "QLD"
    assert decision.action_required is True
    assert decision.reason.startswith("RISK_REENGAGE")


def test_behavioral_guard_switches_immediately_on_large_low_entropy_move():
    guard = BehavioralGuard(initial_bucket="QQQ", evidence=0.0)

    decision = guard.apply(_sizing(1.25, 0.05))

    assert decision.target_bucket == "QLD"
    assert decision.action_required is True
    assert guard.cooldown_days_remaining == 1


def test_behavioral_guard_entropy_barrier_is_structural_not_tuned_constant():
    lower_barrier = BehavioralGuard._entropy_barrier(0.5, bucket_count=2)
    higher_barrier = BehavioralGuard._entropy_barrier(0.5, bucket_count=3)

    assert lower_barrier == 0.5
    assert higher_barrier == 1.0 / 3.0
