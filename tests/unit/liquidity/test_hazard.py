"""Tests for hazard function precomputation (Story 1.2).

SRD v1.2 Chapter 2: Run-length modulation function g(r) and hazard vector.
All assertions use atol=1e-12 (analytic-solution precision).
"""

import numpy as np
import pytest

from src.liquidity.engine.hazard import compute_hazard, precompute_g_r

# ─────────────────────────────────────────────────────────────
# g(r) tests
# ─────────────────────────────────────────────────────────────


class TestPrecomputeGr:
    """SRD 2.2: g(r) = 1 + kappa/(r+1) for r < r_stable, else 1.0."""

    def test_shape(self):
        """g_r must have exactly R_MAX + 1 = 505 elements."""
        g_r = precompute_g_r(r_max=504, r_stable=63, kappa=5)
        assert g_r.shape == (505,)

    def test_dtype(self):
        """g_r must be float64 for numerical precision."""
        g_r = precompute_g_r()
        assert g_r.dtype == np.float64

    def test_r0_initial_convergence(self):
        """g(0) = 1 + 5/1 = 6.0 — maximum hazard boost for newborn regimes."""
        g_r = precompute_g_r()
        np.testing.assert_allclose(g_r[0], 6.0, atol=1e-12)

    def test_r1(self):
        """g(1) = 1 + 5/2 = 3.5."""
        g_r = precompute_g_r()
        np.testing.assert_allclose(g_r[1], 3.5, atol=1e-12)

    def test_r62_last_convergence(self):
        """g(62) = 1 + 5/63 ≈ 1.0794 — last step before stable zone."""
        g_r = precompute_g_r()
        expected = 1.0 + 5.0 / 63.0
        np.testing.assert_allclose(g_r[62], expected, atol=1e-12)

    def test_r63_stable_onset(self):
        """g(63) = 1.0 — stable zone begins here."""
        g_r = precompute_g_r()
        np.testing.assert_allclose(g_r[63], 1.0, atol=1e-12)

    def test_r100_deep_stable(self):
        """g(100) = 1.0 — well into stable zone."""
        g_r = precompute_g_r()
        np.testing.assert_allclose(g_r[100], 1.0, atol=1e-12)

    def test_r504_max(self):
        """g(504) = 1.0 — at R_MAX boundary."""
        g_r = precompute_g_r()
        np.testing.assert_allclose(g_r[504], 1.0, atol=1e-12)

    def test_monotonic_decrease_in_convergence_zone(self):
        """g(r) must be strictly decreasing for r in [0, 62]."""
        g_r = precompute_g_r()
        convergence = g_r[:63]
        diffs = np.diff(convergence)
        assert np.all(diffs < 0), "g(r) must be strictly decreasing in convergence zone"

    def test_all_positive(self):
        """g(r) >= 1.0 everywhere — no negative hazard modulation."""
        g_r = precompute_g_r()
        assert np.all(g_r >= 1.0)

    def test_stable_zone_all_ones(self):
        """g(r) == 1.0 for all r in [63, 504]."""
        g_r = precompute_g_r()
        stable = g_r[63:]
        np.testing.assert_allclose(stable, 1.0, atol=1e-12)

    def test_custom_params(self):
        """Verify with non-default params to ensure they're actually used."""
        g_r = precompute_g_r(r_max=100, r_stable=10, kappa=3)
        assert g_r.shape == (101,)
        np.testing.assert_allclose(g_r[0], 1.0 + 3.0 / 1.0, atol=1e-12)
        np.testing.assert_allclose(g_r[9], 1.0 + 3.0 / 10.0, atol=1e-12)
        np.testing.assert_allclose(g_r[10], 1.0, atol=1e-12)


# ─────────────────────────────────────────────────────────────
# compute_hazard tests
# ─────────────────────────────────────────────────────────────


class TestComputeHazard:
    """SRD 2.1: h(r,t) = clip(lambda_macro * g(r), 0, 1), with h[R_MAX] = 1.0."""

    @pytest.fixture()
    def g_r(self):
        """Standard g_r vector for hazard tests."""
        return precompute_g_r()

    def test_shape(self, g_r):
        """Hazard vector has same shape as g_r."""
        h = compute_hazard(g_r, lambda_macro=0.01)
        assert h.shape == (505,)

    def test_r_max_forced_truncation(self, g_r):
        """SRD 2.3: h[R_MAX] must be 1.0 regardless of lambda_macro."""
        for lm in [0.001, 0.01, 0.05, 0.10]:
            h = compute_hazard(g_r, lambda_macro=lm)
            np.testing.assert_allclose(
                h[504], 1.0, atol=1e-12,
                err_msg=f"h[504] must be 1.0 for lambda_macro={lm}",
            )

    def test_bounded_01(self, g_r):
        """All hazard values must be in [0, 1]."""
        h = compute_hazard(g_r, lambda_macro=0.05)
        assert np.all(h >= 0.0)
        assert np.all(h <= 1.0)

    def test_stable_zone_values(self, g_r):
        """In stable zone, h(r) = lambda_macro * 1.0 = lambda_macro."""
        lm = 0.01
        h = compute_hazard(g_r, lambda_macro=lm)
        # Check r=100 (deep stable, not R_MAX)
        np.testing.assert_allclose(h[100], lm, atol=1e-12)

    def test_convergence_zone_boosted(self, g_r):
        """In convergence zone, h(r) > lambda_macro due to g(r) > 1."""
        lm = 0.01
        h = compute_hazard(g_r, lambda_macro=lm)
        # h(0) = 0.01 * 6.0 = 0.06
        np.testing.assert_allclose(h[0], 0.06, atol=1e-12)
        # All convergence zone entries should be > base rate
        assert np.all(h[:63] > lm)

    def test_zero_lambda(self, g_r):
        """lambda_macro=0 means no changepoints... except at R_MAX."""
        h = compute_hazard(g_r, lambda_macro=0.0)
        assert np.all(h[:504] == 0.0)
        np.testing.assert_allclose(h[504], 1.0, atol=1e-12)

    def test_clipping_large_lambda(self, g_r):
        """Very large lambda_macro: h clipped to 1.0, never exceeds."""
        h = compute_hazard(g_r, lambda_macro=1.0)
        assert np.all(h <= 1.0)
        # h(0) = 1.0 * 6.0 → clipped to 1.0
        np.testing.assert_allclose(h[0], 1.0, atol=1e-12)

    def test_safety_constraint_default_params(self, g_r):
        """SRD safety: lambda_ceil(0.016) * g(0)(6.0) = 0.096 < 1.0."""
        h = compute_hazard(g_r, lambda_macro=0.016)
        np.testing.assert_allclose(h[0], 0.016 * 6.0, atol=1e-12)
        assert h[0] < 1.0, "Default params must keep h(0) < 1.0"
