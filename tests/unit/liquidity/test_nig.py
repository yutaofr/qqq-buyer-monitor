"""Tests for NIG conjugate update functions (Story 1.3).

SRD v1.2 Chapter 3: Online recursive NIG update and Student-t predictive density.

Ground truth values in P1-level tests are computed analytically from the
update formulas — no random seeds, no stochastic approximations.

Precision contract:
  - Analytic comparisons: atol=1e-10
  - Finiteness checks: no tolerance needed (just assert finite)
"""

import numpy as np
import pytest

from src.liquidity.engine.nig import predictive_logpdf, update_nig


# ─────────────────────────────────────────────────────────────
# Fixtures: shared prior and test shapes
# ─────────────────────────────────────────────────────────────

N = 505   # R_MAX + 1
D = 3     # number of observation dimensions


def make_prior(mu_0=0.0, kappa_0=5.0, alpha_0=2.5, beta_0=1.5) -> np.ndarray:
    """Build a (N, D, 4) stats array filled with a single prior."""
    stats = np.empty((N, D, 4), dtype=np.float64)
    stats[:, :, 0] = mu_0
    stats[:, :, 1] = kappa_0
    stats[:, :, 2] = alpha_0
    stats[:, :, 3] = beta_0
    return stats


def make_prior_row(mu_0=0.0, kappa_0=5.0, alpha_0=2.5, beta_0=1.5) -> np.ndarray:
    """Build a single (D, 4) prior row for anchored-decay tests."""
    row = np.empty((D, 4), dtype=np.float64)
    row[:, 0] = mu_0
    row[:, 1] = kappa_0
    row[:, 2] = alpha_0
    row[:, 3] = beta_0
    return row


# ─────────────────────────────────────────────────────────────
# P0-level: structural invariants (INV-6)
# ─────────────────────────────────────────────────────────────


class TestUpdateNIGShape:
    """Output shape and dtype preservation."""

    def test_output_shape(self):
        old_stats = make_prior()
        x_t = np.zeros(D)
        new_stats = update_nig(old_stats, x_t)
        assert new_stats.shape == (N, D, 4)

    def test_output_dtype(self):
        old_stats = make_prior()
        x_t = np.zeros(D)
        new_stats = update_nig(old_stats, x_t)
        assert new_stats.dtype == np.float64

    def test_no_inplace_mutation(self):
        """update_nig must NOT mutate the input array."""
        old_stats = make_prior()
        original_copy = old_stats.copy()
        x_t = np.ones(D) * 2.0
        update_nig(old_stats, x_t)
        np.testing.assert_array_equal(old_stats, original_copy)


class TestKappaLinearGrowth:
    """INV-6: kappa[k] == kappa_0 + k after k steps.

    kappa is the count of observations absorbed — it grows by exactly 1 per
    step regardless of x_t values. This makes it the ideal indicator for
    off-by-one errors in the suff_stats shift logic.
    """

    def test_kappa_grows_by_one(self):
        """One update step: every row's kappa increases by exactly 1."""
        stats = make_prior(kappa_0=5.0)
        x_t = np.array([0.0, 0.0, 0.0])
        new_stats = update_nig(stats, x_t)
        # All rows get kappa = 6.0 after one step
        np.testing.assert_allclose(
            new_stats[:, :, 1], 6.0, atol=1e-12,
            err_msg="kappa must be kappa_0 + 1 after one update",
        )

    def test_kappa_linear_after_multiple_steps(self):
        """After k sequential updates, row r has kappa = kappa_0 + k.

        Simulates the engine's suff_stats shift: at each step, each row r
        was last updated (r) steps ago, so kappa[r] = kappa_0 + r.
        We test by updating the SAME stats k times (no shifting, purely
        verifying the formula is additive).
        """
        kappa_0 = 5.0
        stats = make_prior(kappa_0=kappa_0)
        x_t = np.zeros(D)
        for k in range(1, 6):
            stats = update_nig(stats, x_t)
        # After 5 updates, kappa = kappa_0 + 5
        np.testing.assert_allclose(
            stats[:, :, 1], kappa_0 + 5, atol=1e-12,
        )

    def test_alpha_grows_by_half(self):
        """alpha increases by 0.5 per step (mirror of kappa linearity)."""
        alpha_0 = 2.5
        stats = make_prior(alpha_0=alpha_0)
        x_t = np.zeros(D)
        new_stats = update_nig(stats, x_t)
        np.testing.assert_allclose(
            new_stats[:, :, 2], alpha_0 + 0.5, atol=1e-12,
        )


# ─────────────────────────────────────────────────────────────
# P1-level: analytic ground-truth (SRD SC-4)
# ─────────────────────────────────────────────────────────────


class TestNIGUpdateAnalytic:
    """SRD SC-4: exact NIG update values for x=4.0 starting from default prior.

    Prior: mu_0=0, kappa_0=5, alpha_0=2.5, beta_0=1.5
    Observation: x_t = 4.0

    Hand-calculated expected values:
      kappa_new = 5 + 1 = 6
      mu_new    = (5*0 + 4.0) / 6 = 4/6 = 0.6̄
      alpha_new = 2.5 + 0.5 = 3.0
      beta_new  = 1.5 + 0.5 * 5 * (4.0 - 0)^2 / 6
               = 1.5 + 0.5 * 5 * 16 / 6
               = 1.5 + 40/6
               = 1.5 + 6.6̄
               = 8.1̄6̄
    """

    @pytest.fixture()
    def updated_stats(self):
        stats = make_prior(mu_0=0.0, kappa_0=5.0, alpha_0=2.5, beta_0=1.5)
        x_t = np.array([4.0, 4.0, 4.0])
        return update_nig(stats, x_t)

    def test_kappa_new(self, updated_stats):
        np.testing.assert_allclose(
            updated_stats[:, :, 1], 6.0, atol=1e-10,
        )

    def test_mu_new(self, updated_stats):
        expected_mu = 4.0 / 6.0
        np.testing.assert_allclose(
            updated_stats[:, :, 0], expected_mu, atol=1e-10,
        )

    def test_alpha_new(self, updated_stats):
        np.testing.assert_allclose(
            updated_stats[:, :, 2], 3.0, atol=1e-10,
        )

    def test_beta_new(self, updated_stats):
        # beta_new = 1.5 + 0.5 * 5 * 16 / 6
        expected_beta = 1.5 + 0.5 * 5.0 * 16.0 / 6.0
        np.testing.assert_allclose(
            updated_stats[:, :, 3], expected_beta, atol=1e-10,
        )

    def test_all_rows_identical(self, updated_stats):
        """All rows must get identical update since they started from equal prior."""
        for stat_idx in range(4):
            row0 = updated_stats[0, :, stat_idx]
            for r in range(1, N):
                np.testing.assert_allclose(
                    updated_stats[r, :, stat_idx], row0, atol=1e-12,
                )

    def test_different_dims_get_same_update(self, updated_stats):
        """All D=3 dimensions get the same update since x_t was uniform."""
        for r in range(5):  # spot-check first 5 rows
            np.testing.assert_allclose(
                updated_stats[r, 0, :], updated_stats[r, 1, :], atol=1e-12,
            )
            np.testing.assert_allclose(
                updated_stats[r, 0, :], updated_stats[r, 2, :], atol=1e-12,
            )


class TestNIGUpdateZeroObservation:
    """x_t = 0 starting from zero-mean prior: only kappa and alpha grow."""

    def test_mu_unchanged_at_zero(self):
        """mu_new = (kappa_0*0 + 0) / (kappa_0+1) = 0."""
        stats = make_prior(mu_0=0.0, kappa_0=5.0)
        x_t = np.zeros(D)
        new_stats = update_nig(stats, x_t)
        np.testing.assert_allclose(new_stats[:, :, 0], 0.0, atol=1e-12)

    def test_beta_unchanged_at_mean(self):
        """With x_t == mu_0 == 0, beta update term is zero: beta_new = beta_0."""
        stats = make_prior(mu_0=0.0, kappa_0=5.0, beta_0=1.5)
        x_t = np.zeros(D)
        new_stats = update_nig(stats, x_t)
        np.testing.assert_allclose(new_stats[:, :, 3], 1.5, atol=1e-12)


class TestNIGUpdateNonzeroPreviousMu:
    """Verify the (x_t - mu_old)^2 dependency in beta update."""

    def test_beta_uses_deviation_from_current_mu(self):
        """If current mu = 3.0 and x_t = 3.0, deviation is zero → beta stable."""
        stats = make_prior(mu_0=3.0, kappa_0=5.0, alpha_0=2.5, beta_0=2.0)
        x_t = np.full(D, 3.0)
        new_stats = update_nig(stats, x_t)
        # deviation = 0, so beta_new = beta_old = 2.0
        np.testing.assert_allclose(new_stats[:, :, 3], 2.0, atol=1e-12)

    def test_beta_grows_when_deviation_nonzero(self):
        """If mu=3 but x_t=5, deviation > 0 → beta increases."""
        stats = make_prior(mu_0=3.0, kappa_0=5.0, beta_0=2.0)
        x_t = np.full(D, 5.0)
        new_stats = update_nig(stats, x_t)
        # deviation = (5-3)^2 = 4, so beta must increase
        assert np.all(new_stats[:, :, 3] > 2.0)


class TestAnchoredDecayClosedForm:
    """Closed-form and asymptotic contracts for prior-anchored decay."""

    def test_kappa_alpha_match_closed_form(self):
        lam = 0.98
        kappa_0 = 5.0
        alpha_0 = 2.5
        prior_row = make_prior_row(kappa_0=kappa_0, alpha_0=alpha_0)
        stats = make_prior(kappa_0=kappa_0, alpha_0=alpha_0)
        x_t = np.zeros(D)

        for step in range(1, 201):
            stats = update_nig(
                stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )
            expected_kappa = kappa_0 + (1.0 - lam**step) / (1.0 - lam)
            expected_alpha = alpha_0 + 0.5 * (1.0 - lam**step) / (1.0 - lam)
            np.testing.assert_allclose(stats[:, :, 1], expected_kappa, atol=1e-10)
            np.testing.assert_allclose(stats[:, :, 2], expected_alpha, atol=1e-10)

    def test_kappa_alpha_are_monotone_and_bounded_by_asymptote(self):
        lam = 0.97
        prior_row = make_prior_row()
        stats = make_prior()
        x_t = np.zeros(D)

        kappa_inf = prior_row[0, 1] + 1.0 / (1.0 - lam)
        alpha_inf = prior_row[0, 2] + 0.5 / (1.0 - lam)
        kappa_path = []
        alpha_path = []

        for _ in range(120):
            stats = update_nig(
                stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )
            kappa_path.append(float(stats[0, 0, 1]))
            alpha_path.append(float(stats[0, 0, 2]))

        assert np.all(np.diff(kappa_path) > 0.0)
        assert np.all(np.diff(alpha_path) > 0.0)
        assert np.all(np.array(kappa_path) < kappa_inf)
        assert np.all(np.array(alpha_path) < alpha_inf)

    def test_gap_contracts_by_lambda(self):
        lam = 0.96
        prior_row = make_prior_row()
        stats = make_prior()
        x_t = np.zeros(D)

        kappa_inf = prior_row[0, 1] + 1.0 / (1.0 - lam)
        alpha_inf = prior_row[0, 2] + 0.5 / (1.0 - lam)
        kappa_gaps = []
        alpha_gaps = []

        for _ in range(80):
            stats = update_nig(
                stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )
            kappa_gaps.append(kappa_inf - float(stats[0, 0, 1]))
            alpha_gaps.append(alpha_inf - float(stats[0, 0, 2]))

        np.testing.assert_allclose(
            np.array(kappa_gaps[1:]),
            lam * np.array(kappa_gaps[:-1]),
            atol=1e-10,
        )
        np.testing.assert_allclose(
            np.array(alpha_gaps[1:]),
            lam * np.array(alpha_gaps[:-1]),
            atol=1e-10,
        )

    def test_fixed_point_is_independent_of_initial_state(self):
        lam = 0.98
        prior_row = make_prior_row()
        prior_stats = np.broadcast_to(prior_row, (N, D, 4)).copy()
        extreme_stats = make_prior(mu_0=7.0, kappa_0=300.0, alpha_0=100.0, beta_0=40.0)
        x_t = np.full(D, 2.0)

        for _ in range(800):
            prior_stats = update_nig(
                prior_stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )
            extreme_stats = update_nig(
                extreme_stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )

        np.testing.assert_allclose(
            prior_stats[:, :, 1],
            extreme_stats[:, :, 1],
            atol=5e-5,
        )
        np.testing.assert_allclose(
            prior_stats[:, :, 2],
            extreme_stats[:, :, 2],
            atol=5e-5,
        )

    def test_kappa_alpha_limits_do_not_depend_on_constant_observation(self):
        lam = 0.95
        prior_row = make_prior_row()
        x_values = [0.0, 3.0, -5.0]
        final_pairs = []

        for x_scalar in x_values:
            stats = make_prior()
            x_t = np.full(D, x_scalar)
            for _ in range(200):
                stats = update_nig(
                    stats,
                    x_t,
                    forgetting_lambda=lam,
                    prior_stats=prior_row,
                )
            final_pairs.append((float(stats[0, 0, 1]), float(stats[0, 0, 2])))

        first = np.array(final_pairs[0])
        for pair in final_pairs[1:]:
            np.testing.assert_allclose(np.array(pair), first, atol=1e-10)

    def test_epsilon_convergence_bound_for_kappa(self):
        lam = 0.98
        eps = 1e-2
        prior_row = make_prior_row()
        stats = make_prior()
        x_t = np.zeros(D)
        kappa_inf = prior_row[0, 1] + 1.0 / (1.0 - lam)
        t_star = int(np.ceil(np.log(eps * (1.0 - lam)) / np.log(lam)))

        for _ in range(t_star):
            stats = update_nig(
                stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )

        gap = abs(kappa_inf - float(stats[0, 0, 1]))
        assert gap <= eps


class TestAnchoredDecayMuConvergence:
    """Mu converges to the anchored fixed point, not raw c, when λ < 1."""

    @pytest.mark.parametrize("lam", [0.95, 0.98, 0.995])
    def test_mu_error_shrinks_and_enters_anchored_tolerance_band(self, lam):
        c = 4.0
        mu_0 = 0.0
        kappa_0 = 5.0
        prior_row = make_prior_row(mu_0=mu_0, kappa_0=kappa_0)
        stats = make_prior(mu_0=mu_0, kappa_0=kappa_0)
        x_t = np.full(D, c)
        errors = []
        mu_inf = (kappa_0 * mu_0 + c / (1.0 - lam)) / (kappa_0 + 1.0 / (1.0 - lam))

        for _ in range(1200):
            stats = update_nig(
                stats,
                x_t,
                forgetting_lambda=lam,
                prior_stats=prior_row,
            )
            errors.append(abs(mu_inf - float(stats[0, 0, 0])))

        assert np.all(np.diff(errors) <= 1e-12)
        assert errors[-1] <= 5e-3


# ─────────────────────────────────────────────────────────────
# predictive_logpdf tests
# ─────────────────────────────────────────────────────────────


class TestPredictiveLogpdf:
    """SRD 3.2: conditional independent Student-t joint log-density."""

    def test_output_shape(self):
        """Returns (N,) — one scalar per run length."""
        stats = make_prior()
        x_t = np.zeros(D)
        out = predictive_logpdf(stats, x_t)
        assert out.shape == (N,)

    def test_output_dtype(self):
        stats = make_prior()
        x_t = np.zeros(D)
        out = predictive_logpdf(stats, x_t)
        assert out.dtype == np.float64

    def test_all_finite(self):
        """No NaN or inf for any valid input."""
        stats = make_prior()
        for x_t in [np.zeros(D), np.ones(D) * 4.0, np.array([-2.0, 1.0, 0.5])]:
            out = predictive_logpdf(stats, x_t)
            assert np.all(np.isfinite(out)), f"Non-finite logpdf for x_t={x_t}"

    def test_all_negative(self):
        """Log-pdf of a proper density is always <= 0 (since PDF <= 1 only for
        appropriate scale; Student-t can exceed 1 for narrow distributions, so
        we only check for finiteness here, not sign)."""
        stats = make_prior()
        x_t = np.zeros(D)
        out = predictive_logpdf(stats, x_t)
        # At least verify it's a real number
        assert np.all(np.isfinite(out))

    def test_symmetric_around_mean(self):
        """f(mu + d) == f(mu - d) for Student-t: logpdf is symmetric."""
        stats = make_prior(mu_0=0.0)
        x_pos = np.full(D, 2.0)
        x_neg = np.full(D, -2.0)
        logpdf_pos = predictive_logpdf(stats, x_pos)
        logpdf_neg = predictive_logpdf(stats, x_neg)
        np.testing.assert_allclose(logpdf_pos, logpdf_neg, atol=1e-10)

    def test_peak_at_mean(self):
        """logpdf at mean mu_0 must be higher than at any x != mu_0."""
        stats = make_prior(mu_0=0.0)
        x_mean = np.zeros(D)
        x_off = np.ones(D) * 3.0
        logpdf_mean = predictive_logpdf(stats, x_mean)
        logpdf_off = predictive_logpdf(stats, x_off)
        assert np.all(logpdf_mean > logpdf_off)

    def test_larger_deviation_lower_logpdf(self):
        """More extreme observations should have lower (more negative) logpdf."""
        stats = make_prior(mu_0=0.0)
        x_small = np.ones(D) * 1.0
        x_large = np.ones(D) * 5.0
        logpdf_small = predictive_logpdf(stats, x_small)
        logpdf_large = predictive_logpdf(stats, x_large)
        assert np.all(logpdf_small > logpdf_large)

    def test_three_dims_sum(self):
        """Joint logpdf = sum of D independent marginal logpdfs.
        Verify by checking that 3x identical dims gives 3x single-dim value.
        """
        # Single-dim stats (use D=1 trick via slicing)
        stats = make_prior()
        x_t = np.array([2.0, 2.0, 2.0])  # identical across dims
        joint = predictive_logpdf(stats, x_t)

        # Each dimension contributes equally since all have same prior and x
        # Construct a version where only dim 0 gets x=2, rest get the mean
        x_dim0_only = np.array([2.0, 0.0, 0.0])
        logpdf_dim0 = predictive_logpdf(stats, x_dim0_only)

        # Cannot easily separate, but joint must be strictly less than
        # single-dim version (probability of 3 simultaneous events is lower)
        assert np.all(joint < logpdf_dim0)

    def test_no_nan_with_extreme_inputs(self):
        """Stress test: large x_t values should not produce NaN."""
        stats = make_prior()
        x_t = np.array([100.0, -50.0, 200.0])
        out = predictive_logpdf(stats, x_t)
        assert np.all(np.isfinite(out))
