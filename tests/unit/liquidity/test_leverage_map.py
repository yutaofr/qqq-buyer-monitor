"""Tests for leverage mapping and three-way allocation (P0-1).

SRD v1.2 Section 4.2-4.3:
    L_target = (1 - P̄) × σ_target / σ̂_t
    σ̂ = (1 - P̄) × σ_calm + P̄ × σ_stress

Allocation:
    L >= 1 → QLD = L-1,  QQQ = 2-L,  Cash = 0
    L <  1 → QLD = 0,    QQQ = L,    Cash = 1-L
"""

import numpy as np
import pytest

from src.liquidity.control.leverage_map import (
    compute_allocation,
    compute_leverage,
)


class TestComputeLeverage:
    """SRD 4.2 reference values."""

    def test_zero_stress_full_leverage(self):
        """P̄ = 0 → σ̂ = 0.18 → L = 1.0 × 0.36/0.18 = 2.0."""
        lev = compute_leverage(s_t=0.0)
        np.testing.assert_allclose(lev, 2.0, atol=1e-10)

    def test_full_stress_zero_leverage(self):
        """P̄ = 1 → participation = 0 → L = 0.0."""
        lev = compute_leverage(s_t=1.0)
        np.testing.assert_allclose(lev, 0.0, atol=1e-10)

    def test_half_stress_analytic(self):
        """P̄ = 0.5 → σ̂ = 0.315 → L = 0.5 × 0.36/0.315 ≈ 0.5714."""
        lev = compute_leverage(s_t=0.5)
        expected = 0.5 * 0.36 / 0.315
        np.testing.assert_allclose(lev, expected, atol=1e-6)

    def test_leverage_monotone_decreasing(self):
        """Higher stress → lower leverage (monotonically)."""
        stresses = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]
        leverages = [compute_leverage(s) for s in stresses]
        for i in range(len(leverages) - 1):
            assert leverages[i] >= leverages[i + 1], (
                f"Non-monotonic: L({stresses[i]})={leverages[i]:.4f} < "
                f"L({stresses[i+1]})={leverages[i+1]:.4f}"
            )

    def test_leverage_clamped_at_2(self):
        """L never exceeds 2.0 even with extreme params."""
        lev = compute_leverage(
            s_t=0.0, sigma_calm=0.10, sigma_stress=0.50, sigma_target=0.50
        )
        assert lev <= 2.0

    def test_leverage_clamped_at_0(self):
        """L never goes below 0.0."""
        lev = compute_leverage(s_t=1.0)
        assert lev >= 0.0

    def test_custom_params(self):
        """Verify custom sigma params are used, not hardcoded."""
        l_default = compute_leverage(s_t=0.3)
        l_custom  = compute_leverage(s_t=0.3, sigma_calm=0.10, sigma_stress=0.50)
        assert l_default != l_custom


class TestComputeAllocation:
    """SRD 4.3: three-way portfolio split."""

    def test_full_leverage_full_qld(self):
        """L=2.0 → QLD=1.0, QQQ=0.0, Cash=0.0."""
        a = compute_allocation(2.0)
        np.testing.assert_allclose(a.qld, 1.0, atol=1e-10)
        np.testing.assert_allclose(a.qqq, 0.0, atol=1e-10)
        np.testing.assert_allclose(a.cash, 0.0, atol=1e-10)

    def test_one_leverage_full_qqq(self):
        """L=1.0 → QLD=0.0, QQQ=1.0, Cash=0.0."""
        a = compute_allocation(1.0)
        np.testing.assert_allclose(a.qld, 0.0, atol=1e-10)
        np.testing.assert_allclose(a.qqq, 1.0, atol=1e-10)
        np.testing.assert_allclose(a.cash, 0.0, atol=1e-10)

    def test_zero_leverage_full_cash(self):
        """L=0.0 → QLD=0.0, QQQ=0.0, Cash=1.0."""
        a = compute_allocation(0.0)
        np.testing.assert_allclose(a.qld, 0.0, atol=1e-10)
        np.testing.assert_allclose(a.qqq, 0.0, atol=1e-10)
        np.testing.assert_allclose(a.cash, 1.0, atol=1e-10)

    def test_1_5_leverage_mixed(self):
        """L=1.5 → QLD=0.5, QQQ=0.5, Cash=0."""
        a = compute_allocation(1.5)
        np.testing.assert_allclose(a.qld, 0.5, atol=1e-10)
        np.testing.assert_allclose(a.qqq, 0.5, atol=1e-10)
        np.testing.assert_allclose(a.cash, 0.0, atol=1e-10)

    def test_0_5_leverage_qqq_cash(self):
        """L=0.5 → QLD=0, QQQ=0.5, Cash=0.5."""
        a = compute_allocation(0.5)
        np.testing.assert_allclose(a.qld, 0.0, atol=1e-10)
        np.testing.assert_allclose(a.qqq, 0.5, atol=1e-10)
        np.testing.assert_allclose(a.cash, 0.5, atol=1e-10)

    def test_weights_sum_to_one(self):
        """For all L ∈ [0, 2], QLD + QQQ + Cash = 1.0."""
        for l_val in np.linspace(0.0, 2.0, 21):
            a = compute_allocation(float(l_val))
            total = a.qld + a.qqq + a.cash
            np.testing.assert_allclose(total, 1.0, atol=1e-10,
                                       err_msg=f"L={l_val}")

    def test_no_negative_weights(self):
        """All weights >= 0 for valid L range."""
        for l_val in np.linspace(0.0, 2.0, 21):
            a = compute_allocation(float(l_val))
            assert a.qld >= 0 and a.qqq >= 0 and a.cash >= 0, (
                f"Negative weight at L={l_val}: {a}"
            )

    def test_leverage_stored_in_allocation(self):
        """Allocation dataclass stores the input leverage."""
        a = compute_allocation(1.5)
        assert a.leverage == pytest.approx(1.5)

    def test_allocation_immutable(self):
        """Allocation is frozen dataclass — no mutation allowed."""
        a = compute_allocation(1.5)
        with pytest.raises(AttributeError):
            a.qld = 0.99  # type: ignore[misc]


class TestLeverageAllocationEndToEnd:
    """Integration: stress → leverage → allocation."""

    def test_calm_market_enters_qld(self):
        """s_t≈0 → L≈2.0 → full QLD."""
        lev = compute_leverage(0.01)
        a = compute_allocation(lev)
        assert a.qld > 0.95, f"Expected near-full QLD, got QLD={a.qld:.3f}"

    def test_moderate_stress_qqq_dominant(self):
        """s_t=0.5 → L≈0.57 → QQQ + Cash, no QLD."""
        lev = compute_leverage(0.5)
        a = compute_allocation(lev)
        assert a.qld == 0.0
        assert a.qqq > 0
        assert a.cash > 0

    def test_extreme_stress_full_cash(self):
        """s_t=1.0 → L=0 → 100% Cash."""
        lev = compute_leverage(1.0)
        a = compute_allocation(lev)
        np.testing.assert_allclose(a.cash, 1.0, atol=1e-10)
