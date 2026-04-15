"""Minimum QLD holding period enforcement.

SRD v1.2 Section 4.5: Leveraged ETFs (QLD) suffer from daily leverage
resets (volatility drag / beta slippage). The 63-day minimum hold
ensures the strategy captures enough directional momentum to overcome
this structural drag.

This module is deliberately thin: it is a single-responsibility guard
that intercepts EXIT_QLD signals and converts them to HOLD if the
holding period constraint is not yet satisfied.

The circuit breaker check (s_t > 0.70) is the deadband's responsibility.
This guard receives a pre-computed circuit_breaker_triggered flag.
"""

from src.liquidity.control.deadband import DeadbandSignal


class HoldPeriodGuard:
    """Enforces the minimum QLD holding period constraint.

    Args:
        min_hold_days: Minimum trading days before EXIT_QLD is permitted.
                       Default 63 (1 quarter, from SRD v1.2 Section 4.5).
    """

    def __init__(self, min_hold_days: int = 63) -> None:
        self._min_hold = min_hold_days

    def enforce(
        self,
        signal: DeadbandSignal,
        days_held: int,
        circuit_breaker_triggered: bool,
    ) -> DeadbandSignal:
        """Gate EXIT_QLD signals against the minimum hold period.

        Args:
            signal:                  Raw signal from update_deadband().
            days_held:               Number of trading days currently held in QLD.
            circuit_breaker_triggered: If True, hold period is waived.

        Returns:
            Original signal if HOLD or ENTER_QLD, or if EXIT_QLD and
            (days_held >= min_hold OR circuit_breaker).
            HOLD if EXIT_QLD but hold period not yet satisfied.
        """
        if signal != DeadbandSignal.EXIT_QLD:
            return signal    # HOLD and ENTER_QLD pass through unchanged

        if circuit_breaker_triggered or days_held >= self._min_hold:
            return DeadbandSignal.EXIT_QLD

        # Hold period not satisfied — suppress exit
        return DeadbandSignal.HOLD
