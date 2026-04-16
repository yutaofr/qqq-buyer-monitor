"""Tests for minimum QLD holding period constraint (Story 4.3).

SRD v1.2 Section 4.5:
    Once in QLD, the system must hold for at least 63 trading days
    (~3 months) to amortise the leverage drag from daily resets.

    Exception: circuit_breaker overrides the hold period.
    The hold period guard does NOT own the circuit breaker check —
    that is the deadband's responsibility. The guard only enforces
    the minimum hold when signal = EXIT_QLD with days_held < 63.
"""

from src.liquidity.control.deadband import DeadbandSignal
from src.liquidity.control.hold_period import HoldPeriodGuard

MIN_HOLD = 63


class TestHoldPeriodGuardEnforcement:
    """EXIT_QLD signals are blocked unless min hold period is met."""

    def test_exit_blocked_before_min_hold(self):
        """days_held=10 < 63 → EXIT_QLD signal converted to HOLD."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        enforced = guard.enforce(
            signal=DeadbandSignal.EXIT_QLD,
            days_held=10,
            circuit_breaker_triggered=False,
        )
        assert enforced == DeadbandSignal.HOLD

    def test_exit_allowed_after_min_hold(self):
        """days_held=63 >= 63 → EXIT_QLD passes through."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        enforced = guard.enforce(
            signal=DeadbandSignal.EXIT_QLD,
            days_held=63,
            circuit_breaker_triggered=False,
        )
        assert enforced == DeadbandSignal.EXIT_QLD

    def test_exit_allowed_well_after_min_hold(self):
        """days_held=200 >> 63 → EXIT_QLD passes through."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        enforced = guard.enforce(
            signal=DeadbandSignal.EXIT_QLD,
            days_held=200,
            circuit_breaker_triggered=False,
        )
        assert enforced == DeadbandSignal.EXIT_QLD

    def test_circuit_breaker_overrides_hold_period(self):
        """days_held=5 but circuit_breaker=True → EXIT_QLD passes immediately."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        enforced = guard.enforce(
            signal=DeadbandSignal.EXIT_QLD,
            days_held=5,
            circuit_breaker_triggered=True,
        )
        assert enforced == DeadbandSignal.EXIT_QLD

    def test_hold_signal_unaffected(self):
        """HOLD signal is never modified by the guard."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        for days in [0, 10, 62, 63, 200]:
            enforced = guard.enforce(
                signal=DeadbandSignal.HOLD,
                days_held=days,
                circuit_breaker_triggered=False,
            )
            assert enforced == DeadbandSignal.HOLD

    def test_enter_signal_unaffected(self):
        """ENTER_QLD signal is never modified by the guard."""
        guard = HoldPeriodGuard(min_hold_days=MIN_HOLD)
        enforced = guard.enforce(
            signal=DeadbandSignal.ENTER_QLD,
            days_held=0,
            circuit_breaker_triggered=False,
        )
        assert enforced == DeadbandSignal.ENTER_QLD


class TestHoldPeriodGuardBoundary:
    """Boundary condition: exactly at min_hold_days."""

    def test_day_62_blocked(self):
        guard = HoldPeriodGuard(min_hold_days=63)
        enforced = guard.enforce(DeadbandSignal.EXIT_QLD, days_held=62,
                                 circuit_breaker_triggered=False)
        assert enforced == DeadbandSignal.HOLD

    def test_day_63_allowed(self):
        guard = HoldPeriodGuard(min_hold_days=63)
        enforced = guard.enforce(DeadbandSignal.EXIT_QLD, days_held=63,
                                 circuit_breaker_triggered=False)
        assert enforced == DeadbandSignal.EXIT_QLD

    def test_custom_min_hold(self):
        """Verify parameter is actually used (not hardcoded to 63)."""
        guard = HoldPeriodGuard(min_hold_days=10)
        # Should allow exit at day 10 with custom guard
        enforced = guard.enforce(DeadbandSignal.EXIT_QLD, days_held=10,
                                 circuit_breaker_triggered=False)
        assert enforced == DeadbandSignal.EXIT_QLD
        # Should block at day 9
        enforced2 = guard.enforce(DeadbandSignal.EXIT_QLD, days_held=9,
                                  circuit_breaker_triggered=False)
        assert enforced2 == DeadbandSignal.HOLD
