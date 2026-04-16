"""Tests for the allocator — continuous leverage control chain (P0-1 rewrite).

SRD v1.2 Section 4: Integrates AEMA → Leverage Map → Deadband → Hold Period.

The allocator is a stateful step function:
    step(p_cp_raw, lambda_macro) → (qld_weight, allocation_log)

qld_weight ∈ [0, 1]: QLD allocation from three-way split.
"""

import numpy as np
import pytest

from src.liquidity.config import load_config
from src.liquidity.control.allocator import Allocator


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
    """Sustained calm → system enters QLD via continuous leverage."""

    def test_sustained_calm_enters_qld(self, allocator):
        """20 steps of near-zero stress → QLD weight > 0."""
        for _ in range(20):
            weight, _ = allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert weight > 0.5, (
            f"Expected QLD entry after 20 calm steps, got weight={weight}"
        )

    def test_entry_sets_in_qld_true(self, allocator):
        """After sustained calm, leverage >= 1 → in_qld True."""
        for _ in range(30):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        state = allocator.get_state()
        assert state["in_qld"] is True


class TestAllocatorStressExit:
    """Stress spike triggers exit, hold period respected."""

    def test_stress_exits_after_min_hold(self, config, allocator):
        """Enter QLD → hold 63+ days → stress spike → exit."""
        # Phase 1: Enter QLD (calm for 30 steps)
        for _ in range(30):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_state()["in_qld"] is True

        # Phase 2: Hold for 70 more calm steps (total > 63)
        for _ in range(70):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)

        # Phase 3: Large stress spike — should exit
        for _ in range(10):
            weight, log = allocator.step(p_cp_raw=0.95, lambda_macro=0.016)

        assert weight == 0.0, (
            f"Expected exit from QLD after stress spike. "
            f"weight={weight}, state={allocator.get_state()}"
        )

    def test_stress_blocked_before_min_hold(self, allocator):
        """Enter QLD → moderate stress before 63 days → hold period blocks exit."""
        # Enter QLD
        for _ in range(30):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_state()["in_qld"] is True

        # 10 more calm steps (total ~40, < 63)
        for _ in range(10):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)

        # Moderate stress (below circuit breaker 0.70)
        for _ in range(5):
            weight, _ = allocator.step(p_cp_raw=0.50, lambda_macro=0.010)

        # Hold period should prevent exit even though stress is rising
        state = allocator.get_state()
        if state["days_held"] < 63:
            assert state["in_qld"] is True, (
                "Hold period should block exit before 63 days"
            )

    def test_regime_severity_exits_when_p_cp_is_low(self, config):
        """Water-level stress must de-risk even after p_cp spike has faded."""
        config["regime_severity"]["enabled"] = True
        config = {
            **config,
            "regime_severity": {
                **config["regime_severity"],
                "alpha_up": 0.50,
                "alpha_down": 0.08,
                "combine": "max",
            },
        }
        allocator = Allocator(config)

        for _ in range(100):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002, regime_severity_raw=0.0)
        assert allocator.get_state()["in_qld"] is True

        for _ in range(10):
            weight, log = allocator.step(
                p_cp_raw=0.005,
                lambda_macro=0.002,
                regime_severity_raw=0.95,
            )

        assert log["s_level_t"] > log["s_cp_t"]
        assert log["s_t"] == log["s_level_t"]
        assert weight == 0.0


class TestAllocatorCircuitBreaker:
    """Extreme stress overrides hold period."""

    def test_circuit_breaker_exits_before_min_hold(self, config, allocator):
        """s_t > circuit_breaker=0.70 → immediate exit even before 63 days."""
        # Enter QLD
        for _ in range(30):
            allocator.step(p_cp_raw=0.005, lambda_macro=0.002)
        assert allocator.get_state()["in_qld"] is True

        # p_cp=0.90 repeatedly → AEMA bypasses, s_t will exceed CB
        for _ in range(15):
            weight, _ = allocator.step(p_cp_raw=0.90, lambda_macro=0.016)

        assert weight == 0.0, (
            f"Circuit breaker should force exit. weight={weight}"
        )


class TestAllocatorContinuousAllocation:
    """Verify continuous L → three-way allocation."""

    def test_log_has_three_way_weights(self, allocator):
        _, log = allocator.step(p_cp_raw=0.01, lambda_macro=0.002)
        for key in ["qld", "qqq", "cash"]:
            assert key in log

    def test_log_weights_sum_to_one(self, allocator):
        """QLD + QQQ + Cash ≈ 1.0."""
        for _ in range(50):
            _, log = allocator.step(p_cp_raw=0.01, lambda_macro=0.002)
            total = log["qld"] + log["qqq"] + log["cash"]
            np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_moderate_stress_gives_partial_allocation(self, allocator):
        """s_t ≈ 0.5 → L ≈ 0.57 → QQQ + Cash, no QLD."""
        # Drive stress toward moderate
        for _ in range(50):
            _, log = allocator.step(p_cp_raw=0.50, lambda_macro=0.008)
        # Should have no QLD (L < 1) and some Cash
        assert log["qld"] == 0.0
        assert log["cash"] > 0


class TestAllocatorLog:
    """step() must return a structured log dict."""

    def test_log_has_required_keys(self, allocator):
        _, log = allocator.step(p_cp_raw=0.01, lambda_macro=0.002)
        required_keys = {"s_t", "signal", "weight", "days_held", "circuit_breaker",
                         "l_target", "l_actual", "l_final", "qld", "qqq", "cash",
                         "s_cp_t", "s_level_t", "regime_severity_raw",
                         "regime_severity_norm", "regime_severity_floor",
                         "regime_severity_ceil"}
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
        for _ in range(30):
            a1.step(p_cp_raw=0.005, lambda_macro=0.002)
        # a2: stress (stay out)
        for _ in range(30):
            a2.step(p_cp_raw=0.90, lambda_macro=0.016)

        assert a1.get_weight() != a2.get_weight(), (
            "Two allocators on different inputs must have different weights."
        )
