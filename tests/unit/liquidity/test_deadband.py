"""Tests for asymmetric execution deadband (Story 4.2).

SRD v1.2 Section 4.3:
    Stress signal s_t is compared against dynamic thresholds.
    The deadband prevents churn from small oscillations.

    Entry threshold (exit from stress, re-enter QLD):
        s_t < entry_threshold  i.e. stress well below exit level

    Exit threshold (too stressed, leave QLD):
        s_t > exit_threshold

    Parameters:
        delta_down=0.05    (narrow: easy to re-enter on sustained calm)
        delta_up=0.30      (wide:   require large stress spike to exit)
        recovery_coeff=0.15 (conservative: re-entry needs s < exit - 0.15*delta_up)
"""

from src.liquidity.control.deadband import DeadbandSignal, DeadbandState, update_deadband


class TestDeadbandSignalEnum:
    def test_all_signals_exist(self):
        assert hasattr(DeadbandSignal, "HOLD")
        assert hasattr(DeadbandSignal, "ENTER_QLD")
        assert hasattr(DeadbandSignal, "EXIT_QLD")


class TestUpdateDeadbandCalmEntry:
    """When not in QLD and stress is low → ENTER_QLD."""

    def test_low_stress_triggers_entry(self):
        """s_t well below entry threshold → ENTER_QLD."""
        state = DeadbandState(in_qld=False, exit_threshold=None, days_held=0)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        # Very low stress: should enter
        new_state, signal = update_deadband(state, s_t=0.02, params=params)
        assert signal == DeadbandSignal.ENTER_QLD
        assert new_state.in_qld is True

    def test_high_stress_stays_out(self):
        """s_t high when not in QLD → stay out (HOLD, not enter)."""
        state = DeadbandState(in_qld=False, exit_threshold=None, days_held=0)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        new_state, signal = update_deadband(state, s_t=0.50, params=params)
        assert signal == DeadbandSignal.HOLD
        assert new_state.in_qld is False


class TestUpdateDeadbandStressExit:
    """When in QLD and stress exceeds exit threshold → EXIT_QLD."""

    def test_stress_spike_exits_qld(self):
        """Very high stress → EXIT_QLD immediately."""
        # In QLD with exit_threshold implicitly derived from entry
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=100)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        # s_t = 0.75 >> exit_threshold=0.35 → exit
        new_state, signal = update_deadband(state, s_t=0.75, params=params)
        assert signal == DeadbandSignal.EXIT_QLD
        assert new_state.in_qld is False
        assert new_state.days_held == 0

    def test_calm_in_qld_stays(self):
        """Low stress while in QLD → HOLD."""
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=10)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        new_state, signal = update_deadband(state, s_t=0.05, params=params)
        assert signal == DeadbandSignal.HOLD
        assert new_state.in_qld is True


class TestCircuitBreaker:
    """Circuit breaker overrides hold period — forces immediate exit."""

    def test_circuit_breaker_exits_regardless_of_hold_period(self):
        """Even with days_held=10 (< 63), circuit breaker forces exit."""
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=10)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        # s_t > circuit_breaker=0.70 → must exit
        new_state, signal = update_deadband(state, s_t=0.85, params=params)
        assert signal == DeadbandSignal.EXIT_QLD


class TestDeadbandHoldCounter:
    """days_held increments each step while in QLD, resets on exit."""

    def test_counter_increments_while_in_qld(self):
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=5)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        new_state, _ = update_deadband(state, s_t=0.01, params=params)
        assert new_state.days_held == 6

    def test_counter_resets_on_exit(self):
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=100)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        new_state, signal = update_deadband(state, s_t=0.80, params=params)
        assert signal == DeadbandSignal.EXIT_QLD
        assert new_state.days_held == 0

    def test_counter_zero_when_not_in_qld(self):
        state = DeadbandState(in_qld=False, exit_threshold=None, days_held=0)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        new_state, _ = update_deadband(state, s_t=0.80, params=params)
        assert new_state.days_held == 0


class TestDeadbandAsymmetry:
    """Wide exit (delta_up=0.30) vs narrow entry (delta_down=0.05)."""

    def test_moderate_stress_cannot_exit_qld(self):
        """s_t = 0.20 — moderate but below exit threshold → HOLD in QLD."""
        state = DeadbandState(in_qld=True, exit_threshold=0.35, days_held=100)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        _, signal = update_deadband(state, s_t=0.20, params=params)
        assert signal == DeadbandSignal.HOLD

    def test_entry_requires_lower_stress_than_exit(self):
        """Entry threshold < exit threshold (asymmetry enforced)."""
        # After exiting at high stress, re-entry requires stress to be much lower
        # Entry: s_t < entry_threshold (which is exit_threshold - recovery_coeff * delta_up)
        # 0.35 - 0.15 * 0.30 = 0.35 - 0.045 = 0.305
        # i.e., need s_t < 0.305 to re-enter
        state_out = DeadbandState(in_qld=False, exit_threshold=0.35, days_held=0)
        params = dict(delta_down=0.05, delta_up=0.30, recovery_coeff=0.15,
                      circuit_breaker=0.70)
        # Moderate stress 0.30: below original exit but check entry threshold
        _, signal = update_deadband(state_out, s_t=0.30, params=params)
        # 0.30 > entry_threshold: must not re-enter yet
        # (entry needs s < 0.35 - 0.15*0.30 = 0.305, so 0.30 < 0.305 → should enter)
        # Adjust: use s_t = 0.31 which is above the 0.305 threshold
        _, signal_31 = update_deadband(state_out, s_t=0.31, params=params)
        assert signal_31 == DeadbandSignal.HOLD  # 0.31 > 0.305, should not enter
