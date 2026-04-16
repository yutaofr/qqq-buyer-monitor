"""Tests for dynamic slippage model (P0-3).

SRD 6.2: Slippage = s0 + s1 × σ̂ / σ_normal
"""

import numpy as np

from src.liquidity.backtest.slippage import compute_sigma_hat, compute_slippage


class TestComputeSlippage:

    def test_calm_vol_gives_5bps(self):
        """σ̂ = σ_normal = 18% → slippage = 3 + 2*(18/18) = 5 bps."""
        s = compute_slippage(sigma_hat=0.18, s0_bps=3.0, s1_bps=2.0, sigma_normal=0.18)
        np.testing.assert_allclose(s, 5.0, atol=1e-10)

    def test_stress_vol_gives_8bps(self):
        """σ̂ = 45% → slippage = 3 + 2*(45/18) = 8.0 bps."""
        s = compute_slippage(sigma_hat=0.45, s0_bps=3.0, s1_bps=2.0, sigma_normal=0.18)
        np.testing.assert_allclose(s, 8.0, atol=1e-10)

    def test_zero_vol_gives_s0(self):
        """σ̂ = 0 → slippage = s0 = 3 bps."""
        s = compute_slippage(sigma_hat=0.0, s0_bps=3.0, s1_bps=2.0, sigma_normal=0.18)
        np.testing.assert_allclose(s, 3.0, atol=1e-10)

    def test_monotonic_in_vol(self):
        """Higher vol → higher slippage."""
        s_low  = compute_slippage(0.10)
        s_mid  = compute_slippage(0.20)
        s_high = compute_slippage(0.40)
        assert s_low < s_mid < s_high

    def test_annual_cost_bound(self):
        """SRD 6.4: Normal year ~20 trades → 20 * 5bps = 100bps = 1%.
        Stress year ~40 trades → 40 * 8bps = 320bps = 3.2%.
        Both are within acceptable range.
        """
        normal_annual = 20 * compute_slippage(0.18)
        stress_annual = 40 * compute_slippage(0.45)
        assert normal_annual < 200    # < 2% p.a.
        assert stress_annual < 500    # < 5% p.a.


class TestComputeSigmaHat:

    def test_zero_stress_gives_calm_vol(self):
        """s_t = 0 → σ̂ = σ_calm = 18%."""
        s = compute_sigma_hat(0.0, sigma_calm=0.18, sigma_stress=0.45)
        np.testing.assert_allclose(s, 0.18, atol=1e-12)

    def test_full_stress_gives_stress_vol(self):
        """s_t = 1 → σ̂ = σ_stress = 45%."""
        s = compute_sigma_hat(1.0, sigma_calm=0.18, sigma_stress=0.45)
        np.testing.assert_allclose(s, 0.45, atol=1e-12)

    def test_midpoint(self):
        """s_t = 0.5 → σ̂ = (0.18+0.45)/2 = 0.315."""
        s = compute_sigma_hat(0.5, sigma_calm=0.18, sigma_stress=0.45)
        np.testing.assert_allclose(s, 0.315, atol=1e-12)

    def test_monotonic_in_stress(self):
        """Higher stress → higher σ̂."""
        assert compute_sigma_hat(0.1) < compute_sigma_hat(0.5) < compute_sigma_hat(0.9)
