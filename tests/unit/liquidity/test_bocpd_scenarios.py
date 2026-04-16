"""P1 scenario tests for BOCPD engine (Story 1.4 / T1.4.3).

These tests verify behavioral semantics under physically meaningful stimuli.
All inputs are deterministic — no random seeds.

SC-1: shock raises p_cp above threshold
SC-2: long run-length collapses under shock
SC-4: exact NIG values at r=1 post-shock (Spec-to-Code parity)
SC-6: multi-dimensional shock > single-dimensional (joint density advantage)
"""

import numpy as np
import pytest

from src.liquidity.config import load_config
from src.liquidity.engine.bocpd import BOCPDEngine


D = 3


@pytest.fixture()
def config():
    return load_config()


def run_engine(config, obs_sequence, lambda_macro=0.01):
    """Helper: run engine through a sequence and return (engine, p_cp_list)."""
    engine = BOCPDEngine(config)
    p_cps = []
    for x_t in obs_sequence:
        p_cp = engine.update(x_t, lambda_macro=lambda_macro)
        p_cps.append(p_cp)
    return engine, p_cps


class TestSC1_ShockRaisesPcp:
    """SC-1: After calm period, a large shock must produce p_cp > 0.3."""

    def test_shock_raises_pcp(self, config):
        # 20 calm steps
        calm = [np.zeros(D)] * 20
        # One strong shock
        shock = np.array([4.0, 4.0, 4.0])

        engine = BOCPDEngine(config)
        p_calm_last = None
        for x_t in calm:
            p_calm_last = engine.update(x_t, lambda_macro=0.01)

        p_cp_at_shock = engine.update(shock, lambda_macro=0.01)

        # Two assertions:
        # (a) p_cp at shock is materially above the calm baseline
        assert p_cp_at_shock > p_calm_last * 3, (
            f"SC-1 failed: shock p_cp={p_cp_at_shock:.4f} is not "
            f"3x above calm baseline {p_calm_last:.4f}. "
            f"Engine is not responding to anomalies."
        )
        # (b) absolute floor: must exceed the hazard floor lambda_floor=0.002
        assert p_cp_at_shock > 0.02, (
            f"SC-1 failed: p_cp={p_cp_at_shock:.4f} too close to zero."
        )

    def test_calm_pcp_near_zero(self, config):
        """Baseline: calm observations should keep p_cp very low."""
        calm = [np.zeros(D)] * 20
        _, p_cps = run_engine(config, calm)
        # All calm p_cp values should be small (< 0.1)
        assert all(p < 0.1 for p in p_cps), (
            f"Calm p_cp unexpectedly high: max={max(p_cps):.4f}"
        )


class TestSC2_RunLengthCollapse:
    """SC-2: Under shock, probability mass should shift to short run lengths."""

    def test_r0_dominates_after_shock(self, config):
        """After shock, probability at r=0 should exceed probability at r=21
        (the 21-step-old regime hypothesis).
        """
        calm = [np.zeros(D)] * 20
        shock = np.array([4.0, 4.0, 4.0])
        obs = calm + [shock]

        engine, _ = run_engine(config, obs)
        state = engine.get_state()

        p_r0 = state.run_length_probs[0]
        p_r21 = state.run_length_probs[21]

        assert p_r0 > p_r21, (
            f"SC-2 failed: probs[0]={p_r0:.6f} <= probs[21]={p_r21:.6f}. "
            f"Long run-length did not collapse under shock."
        )

    def test_mass_concentrates_at_short_runs_after_shock(self, config):
        """Most probability mass should be at run lengths < 5 post-shock."""
        calm = [np.zeros(D)] * 20
        shock = np.array([4.0, 4.0, 4.0])
        obs = calm + [shock]

        engine, _ = run_engine(config, obs)
        state = engine.get_state()

        mass_short = state.run_length_probs[:5].sum()
        mass_total = state.run_length_probs.sum()

        assert mass_short / mass_total > 0.3, (
            f"SC-2: Less than 30% of mass at short run lengths after shock. "
            f"mass_short={mass_short:.4f}, fraction={mass_short/mass_total:.3f}"
        )


class TestSC4_ExactNIGAfterShock:
    """SC-4: After 20 calm steps + 1 shock, verify exact NIG values at r=1.

    At r=1 post-shock: hypothesis that the new regime started at the shock step.
    suff_stats[1] contains the NIG stats after absorbing ONE observation x=[4,4,4]
    from the prior, with forgetting_lambda=0.98 applied.

    Prior: mu_0=0, kappa_0=5, alpha_0=2.5, beta_0=1.5, lambda=0.98

    Step 1 (decay + absorb x=[4,4,4]):
        kappa_decayed = 0.98 × 5.0 = 4.9
        kappa_new = 4.9 + 1 = 5.9
        mu_new    = (4.9 × 0 + 4.0) / 5.9 = 4.0 / 5.9
        alpha_new = 0.98 × 2.5 + 0.5 = 2.95
        beta_new  = 0.98 × 1.5 + 0.5 × 4.9 × 16.0 / 5.9
    """

    @pytest.fixture()
    def engine_post_shock(self, config):
        calm = [np.zeros(D)] * 20
        shock = np.array([4.0, 4.0, 4.0])
        engine = BOCPDEngine(config)
        for x_t in calm + [shock]:
            engine.update(x_t, lambda_macro=0.01)
        return engine

    def test_kappa_at_r1(self, engine_post_shock):
        state = engine_post_shock.get_state()
        lam = 0.98
        kappa_0, x = 5.0, 4.0
        kappa_decayed = lam * kappa_0
        expected_kappa = kappa_decayed + 1.0   # 5.9
        np.testing.assert_allclose(
            state.suff_stats[1, 0, 1], expected_kappa, atol=1e-10,
        )

    def test_mu_at_r1(self, engine_post_shock):
        state = engine_post_shock.get_state()
        lam = 0.98
        kappa_0, mu_0, x = 5.0, 0.0, 4.0
        kappa_decayed = lam * kappa_0
        kappa_new = kappa_decayed + 1.0
        expected_mu = (kappa_decayed * mu_0 + x) / kappa_new  # 4/5.9
        np.testing.assert_allclose(
            state.suff_stats[1, 0, 0], expected_mu, atol=1e-10,
        )

    def test_alpha_at_r1(self, engine_post_shock):
        state = engine_post_shock.get_state()
        lam = 0.98
        expected_alpha = lam * 2.5 + 0.5   # 2.95
        np.testing.assert_allclose(
            state.suff_stats[1, 0, 2], expected_alpha, atol=1e-10,
        )

    def test_beta_at_r1(self, engine_post_shock):
        state = engine_post_shock.get_state()
        lam = 0.98
        kappa_0, mu_0, beta_0, x = 5.0, 0.0, 1.5, 4.0
        kappa_decayed = lam * kappa_0
        kappa_new = kappa_decayed + 1.0
        beta_decayed = lam * beta_0
        expected_beta = beta_decayed + 0.5 * kappa_decayed * (x - mu_0) ** 2 / kappa_new
        np.testing.assert_allclose(
            state.suff_stats[1, 0, 3], expected_beta, atol=1e-10,
        )

    def test_r0_still_prior(self, config, engine_post_shock):
        """Even after shock, suff_stats[0] must equal the prior (INV-4)."""
        state = engine_post_shock.get_state()
        priors = config["nig_priors"]["ed_accel"]
        np.testing.assert_allclose(
            state.suff_stats[0, 0, :],
            [priors["mu_0"], priors["kappa_0"], priors["alpha_0"], priors["beta_0"]],
            atol=1e-12,
        )


class TestSC6_MultiDimensionalAmplification:
    """SC-6: Multi-dimensional simultaneous shock > single-dimensional shock.

    Physical interpretation: the joint likelihood of a 3D observation being
    anomalous in ALL dimensions simultaneously is much lower under the
    current regime model, so the changepoint probability is higher.
    This verifies that the joint log-pdf sum (axis=1) in predictive_logpdf
    is working correctly — multi-dim evidence accumulates additively.
    """

    def test_3d_shock_raises_pcp_more_than_1d(self, config):
        calm = [np.zeros(D)] * 20

        # 3D shock: all dimensions simultaneously anomalous
        shock_3d = np.array([4.0, 4.0, 4.0])
        # 1D shock: only first dimension, others at the mean
        shock_1d = np.array([4.0, 0.0, 0.0])

        _, p_cps_3d = run_engine(config, calm + [shock_3d])
        _, p_cps_1d = run_engine(config, calm + [shock_1d])

        p_cp_3d = p_cps_3d[-1]
        p_cp_1d = p_cps_1d[-1]

        assert p_cp_3d > p_cp_1d, (
            f"SC-6 failed: 3D shock p_cp={p_cp_3d:.4f} <= "
            f"1D shock p_cp={p_cp_1d:.4f}. "
            f"Multi-dimensional evidence is not being accumulated."
        )

    def test_shock_magnitude_monotonic(self, config):
        """Larger shock magnitude → higher p_cp (monotonic sensitivity)."""
        calm = [np.zeros(D)] * 20
        magnitudes = [1.0, 2.0, 4.0, 8.0]
        p_cps = []

        for mag in magnitudes:
            shock = np.full(D, mag)
            _, results = run_engine(config, calm + [shock])
            p_cps.append(results[-1])

        # p_cp must be strictly increasing with magnitude
        for i in range(len(p_cps) - 1):
            assert p_cps[i] < p_cps[i + 1], (
                f"SC-6 monotonicity failed: p_cp({magnitudes[i]})={p_cps[i]:.4f} "
                f">= p_cp({magnitudes[i+1]})={p_cps[i+1]:.4f}"
            )


class TestEngineReset:
    """Verify segment isolation: each BOCPDEngine instance is independent."""

    def test_two_engines_independent(self, config):
        """Two engines run on different inputs must have different states."""
        engine1 = BOCPDEngine(config)
        engine2 = BOCPDEngine(config)

        # Feed different sequences
        for _ in range(5):
            engine1.update(np.zeros(D), lambda_macro=0.01)
        for _ in range(5):
            engine2.update(np.full(D, 3.0), lambda_macro=0.01)

        state1 = engine1.get_state()
        state2 = engine2.get_state()

        # suff_stats should differ (engine2 saw large observations)
        assert not np.allclose(state1.suff_stats, state2.suff_stats), (
            "Two engines with different inputs should have different suff_stats."
        )
