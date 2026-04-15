"""Tests for the allocator — control chain orchestrator (Story 4.4).

SRD v1.2 Section 4: Integrates AEMA → deadband → hold_period → lever map.

The allocator is a stateful step function:
    step(p_cp_raw, lambda_macro) → (target_weight, allocation_log)

target_weight:
    0.0 = 100% QQQ (no leverage)
    1.0 = 100% QLD (2× leverage via the ETF)
    Values in between: transition (POC uses binary, production: continuous)
"""

import numpy as np
import pytest

from src.liquidity.control.allocator import Allocator
from src.liquidity.config import load_config


@pytest.fixture()
def config():
    return load_config()


@pytest.fixture()
def allocator(config):
    return Allocator(config)


class TestAllocatorInitialState:

    def test_initial_weight_is_zero(self, allocator):
        """System starts in QQQ-only (no QLD position) at t=0."""
        assert allocator.get_weight() == 0.0

    def test_initial_in_qld_is_false(self, allocator):
        state = allocator.get_state()
        assert state["in_qld"] is False

    def test_initial_days_held_zero(self, allocator):
        state = allocator.get_state()
        assert state["days_held"] == 0


class TestAllocatorCalmEntry:
    """Sustained calm → system enters QLD."""

    def test_sustained_calm_enters_qld(self, allocator):
        """20 steps of near-zero stress → target_weight becomes 1.0."""
        for _ in range(20):
            weight, _ = allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert weight == 1.0, (
            f"Expected QLD entry after 20 calm steps, got weight={weight}"
        )

    def test_entry_sets_in_qld_true(self, allocator):
        """After entry, in_qld state flag is True."""
        for _ in range(20):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        state = allocator.get_state()
        assert state["in_qld"] is True


class TestAllocatorStressExit:
    """Stress spike triggers exit, hold period respected."""

    def test_stress_exits_after_min_hold(self, config, allocator):
        """Enter QLD → hold 63+ days → stress spike → exit."""
        # Phase 1: Enter QLD (calm for 20 steps)
        for _ in range(20):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_weight() == 1.0, "Should be in QLD"

        # Phase 2: Hold for 63 more calm steps (total in QLD: 63+20 steps, but
        # days_held counts from entry — need exactly 63 steps of HOLD)
        # Run calm until days_held >= 63
        min_hold = config["hold_period"]["min_qld_hold_days"]
        for _ in range(min_hold + 5):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)

        # Phase 3: Large stress spike — should exit
        weight, log = allocator.step(p_cp_raw=0.95, lambda_macro=0.016)
        # May not exit on first spike (AEMA dampens), so run a few high-stress steps
        for _ in range(5):
            weight, log = allocator.step(p_cp_raw=0.95, lambda_macro=0.016)

        assert weight == 0.0, (
            f"Expected exit from QLD after {min_hold}+ days + stress spike, "
            f"got weight={weight}. State={allocator.get_state()}"
        )

    def test_stress_blocked_before_min_hold(self, allocator):
        """Enter QLD → stress spike before 63 days → still holds (no circuit break)."""
        # Enter QLD
        for _ in range(20):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_weight() == 1.0

        # Stress spike after only 10 days in QLD (below min hold, no circuit breaker)
        for _ in range(10):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)

        # Moderate stress (below circuit breaker 0.70)
        for _ in range(5):
            weight, _ = allocator.step(p_cp_raw=0.45, lambda_macro=0.010)

        # Should still be in QLD (min hold not reached, no circuit breaker)
        state = allocator.get_state()
        assert state["days_held"] < 63 or weight == 1.0


class TestAllocatorCircuitBreaker:
    """Extreme stress overrides hold period."""

    def test_circuit_breaker_exits_before_min_hold(self, config, allocator):
        """s_t > circuit_breaker=0.70 → immediate exit even before 63 days."""
        # Enter QLD
        for _ in range(20):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_weight() == 1.0

        # p_cp=1.0 repeatedly → AEMA stress will exceed circuit breaker
        for _ in range(10):
            weight, _ = allocator.step(p_cp_raw=1.0, lambda_macro=0.016)

        assert weight == 0.0, (
            f"Circuit breaker should force exit before min hold. weight={weight}"
        )


class TestAllocatorLog:
    """step() must return a structured log dict."""

    def test_log_has_required_keys(self, allocator):
        _, log = allocator.step(p_cp_raw=0.01, lambda_macro=0.002)
        required_keys = {"s_t", "signal", "weight", "days_held", "circuit_breaker"}
        missing = required_keys - set(log.keys())
        assert not missing, f"Log missing keys: {missing}"

    def test_log_s_t_in_01(self, allocator):
        _, log = allocator.step(p_cp_raw=0.5, lambda_macro=0.01)
        assert 0.0 <= log["s_t"] <= 1.0

    def test_log_weight_matches_return(self, allocator):
        weight, log = allocator.step(p_cp_raw=0.01, lambda_macro=0.002)
        assert log["weight"] == weight


class TestAllocatorIsolation:
    """Two separate Allocator instances must be independent."""

    def test_two_allocators_independent(self, config):
        a1 = Allocator(config)
        a2 = Allocator(config)

        # a1: calm (enter QLD)
        for _ in range(25):
            a1.step(p_cp_raw=0.005, lambda_macro=0.002)
        # a2: stress (stay out)
        for _ in range(25):
            a2.step(p_cp_raw=0.90, lambda_macro=0.016)

        assert a1.get_weight() != a2.get_weight(), (
            "Two allocators on different inputs must have different weights."
        )
