"""Tests for NAV computation module (Story 5.1 / T5.1.1).

SRD v1.2 Section 8.6: Two-step NAV update.
  Step 1: Signal at close of t-1 determines weight for day t.
  Step 2: NAV_t = NAV_{t-1} × (1 + portfolio_return_t)

Execution gap is attribution only — NOT deducted from NAV (no double-count).
"""

import numpy as np
import pytest

from src.liquidity.backtest.nav import NavAccumulator, compute_portfolio_return


class TestComputePortfolioReturn:
    """Unit tests for single-step portfolio return calculation."""

    def test_full_qqq_no_qld(self):
        """weight=0.0 → 100% QQQ → portfolio_ret = qqq_ret."""
        ret = compute_portfolio_return(
            weight_qld=0.0, qqq_ret=0.01, qld_ret=0.02
        )
        np.testing.assert_allclose(ret, 0.01, atol=1e-12)

    def test_full_qld(self):
        """weight=1.0 → 100% QLD → portfolio_ret = qld_ret."""
        ret = compute_portfolio_return(
            weight_qld=1.0, qqq_ret=0.01, qld_ret=0.02
        )
        np.testing.assert_allclose(ret, 0.02, atol=1e-12)

    def test_zero_return(self):
        """Both returns zero → portfolio return zero."""
        ret = compute_portfolio_return(
            weight_qld=1.0, qqq_ret=0.0, qld_ret=0.0
        )
        np.testing.assert_allclose(ret, 0.0, atol=1e-12)

    def test_negative_return_qqq(self):
        """Down day handled correctly."""
        ret = compute_portfolio_return(
            weight_qld=0.0, qqq_ret=-0.03, qld_ret=-0.06
        )
        np.testing.assert_allclose(ret, -0.03, atol=1e-12)


class TestNavAccumulatorInit:
    """Initial state checks."""

    def test_initial_nav_one(self):
        acc = NavAccumulator(initial_nav=1.0)
        assert acc.current_nav == pytest.approx(1.0)

    def test_initial_nav_custom(self):
        acc = NavAccumulator(initial_nav=100.0)
        assert acc.current_nav == pytest.approx(100.0)

    def test_initial_history_empty(self):
        acc = NavAccumulator()
        assert len(acc.history) == 0


class TestNavAccumulatorStep:
    """Single-step NAV update via step()."""

    def test_nav_grows_on_positive_return(self):
        acc = NavAccumulator()
        acc.step(weight_qld=0.0, qqq_ret=0.01, qld_ret=0.02)
        assert acc.current_nav == pytest.approx(1.01)

    def test_nav_shrinks_on_negative_return(self):
        acc = NavAccumulator()
        acc.step(weight_qld=0.0, qqq_ret=-0.05, qld_ret=-0.10)
        assert acc.current_nav == pytest.approx(0.95)

    def test_nav_never_negative(self):
        """Even with -100% return, NAV floor is 0."""
        acc = NavAccumulator()
        acc.step(weight_qld=0.0, qqq_ret=-1.0, qld_ret=-2.0)
        assert acc.current_nav >= 0.0

    def test_history_appends(self):
        acc = NavAccumulator()
        acc.step(weight_qld=0.0, qqq_ret=0.01, qld_ret=0.02)
        acc.step(weight_qld=1.0, qqq_ret=0.01, qld_ret=0.02)
        assert len(acc.history) == 2

    def test_history_correct_values(self):
        acc = NavAccumulator(slippage_bps=3.0)
        acc.step(weight_qld=0.0, qqq_ret=0.01, qld_ret=0.02)  # NAV = 1.01, no slip
        # Step 2: weight changes 0→1 → 3bps slippage deducted
        acc.step(weight_qld=1.0, qqq_ret=0.01, qld_ret=0.02)  # + slip 3e-4
        nav1 = 1.01
        nav2 = nav1 * (1.0 + 0.02 - 3e-4)   # return - slippage
        np.testing.assert_allclose(acc.history, [nav1, nav2], atol=1e-10)

    def test_compounding_correct(self):
        """10 days of 1% daily return → NAV = 1.01^10."""
        acc = NavAccumulator()
        for _ in range(10):
            acc.step(weight_qld=0.0, qqq_ret=0.01, qld_ret=0.02)
        np.testing.assert_allclose(acc.current_nav, 1.01 ** 10, atol=1e-10)


class TestNavSlippage:
    """Slippage is deducted on position changes."""

    def test_no_slippage_when_holding(self):
        """Same weight as previous step → no slippage deduction."""
        acc = NavAccumulator()
        acc.step(weight_qld=1.0, qqq_ret=0.01, qld_ret=0.02)  # enter QLD
        nav_before = acc.current_nav
        acc.step(weight_qld=1.0, qqq_ret=0.01, qld_ret=0.02, prev_weight=1.0)
        # No slippage when holding
        assert acc.current_nav == pytest.approx(nav_before * 1.02)

    def test_slippage_on_transition(self):
        """Weight change → slippage deducted from NAV."""
        acc = NavAccumulator(slippage_bps=3.0)
        nav_before = acc.current_nav
        acc.step(
            weight_qld=1.0, qqq_ret=0.00, qld_ret=0.00,
            prev_weight=0.0  # transition from QQQ to QLD
        )
        expected_nav = nav_before * (1.0 - 3e-4)  # 3 bps slippage
        np.testing.assert_allclose(acc.current_nav, expected_nav, atol=1e-10)
