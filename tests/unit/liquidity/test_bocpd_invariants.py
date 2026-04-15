"""P0 invariant tests for BOCPD engine (Story 1.4 / T1.4.2).

These tests use fully deterministic synthetic data (all zeros) and verify
structural invariants that must hold on every single update step.
If any of these fail the engine is fundamentally broken.

Precision contract: atol=1e-12 (floating-point ceiling, not approximation).
"""

import numpy as np
import pytest

from src.liquidity.config import load_config
from src.liquidity.engine.bocpd import BOCPDEngine


N = 505   # R_MAX + 1
D = 3     # observation dimensions


@pytest.fixture()
def config():
    return load_config()


@pytest.fixture()
def engine(config):
    return BOCPDEngine(config)


@pytest.fixture()
def calm_obs():
    """5-step deterministic sequence of zero observations (DETERMINISTIC_CALM)."""
    return [np.zeros(D) for _ in range(5)]


class TestInitialState:
    """Verify engine state after construction, before any updates."""

    def test_initial_probs_sums_to_one(self, engine):
        state = engine.get_state()
        np.testing.assert_allclose(
            state.run_length_probs.sum(), 1.0, atol=1e-12,
        )

    def test_initial_probs_all_mass_at_r0(self, engine):
        """At t=0, all probability mass is on r=0 (system just started)."""
        state = engine.get_state()
        np.testing.assert_allclose(state.run_length_probs[0], 1.0, atol=1e-12)
        np.testing.assert_allclose(state.run_length_probs[1:].sum(), 0.0, atol=1e-12)

    def test_initial_t_is_zero(self, engine):
        assert engine.get_state().t == 0

    def test_initial_suff_stats_equal_prior(self, config, engine):
        """All rows of suff_stats must equal the prior at initialization."""
        state = engine.get_state()
        priors = config["nig_priors"]
        prior_vals = [
            priors["ed_accel"]["mu_0"],
            priors["ed_accel"]["kappa_0"],
            priors["ed_accel"]["alpha_0"],
            priors["ed_accel"]["beta_0"],
        ]
        # Spot-check r=0, r=100, r=504
        for r in [0, 100, 504]:
            np.testing.assert_allclose(
                state.suff_stats[r, 0, :], prior_vals, atol=1e-12,
                err_msg=f"Initial suff_stats[{r}] != prior",
            )


class TestINV1_Normalization:
    """INV-1: run_length_probs must sum to 1.0 after every update."""

    def test_normalization_after_each_step(self, engine, calm_obs):
        for step, x_t in enumerate(calm_obs):
            engine.update(x_t, lambda_macro=0.01)
            state = engine.get_state()
            np.testing.assert_allclose(
                state.run_length_probs.sum(), 1.0, atol=1e-12,
                err_msg=f"Normalization violated at step {step + 1}",
            )


class TestINV2_NonNegativity:
    """INV-2: all run_length_probs must be >= 0."""

    def test_non_negative_after_each_step(self, engine, calm_obs):
        for step, x_t in enumerate(calm_obs):
            engine.update(x_t, lambda_macro=0.01)
            state = engine.get_state()
            assert np.all(state.run_length_probs >= 0.0), (
                f"Negative probability at step {step + 1}: "
                f"min={state.run_length_probs.min()}"
            )


class TestINV4_PriorLock:
    """INV-4: suff_stats[0] must ALWAYS equal the prior after every update.

    r=0 represents a brand-new regime (just started this step). It must
    always be initialized with the prior — never with accumulated evidence.
    Violation of this invariant means the off-by-one shift is broken.
    """

    def test_prior_lock_after_each_step(self, config, engine, calm_obs):
        priors = config["nig_priors"]
        # Build expected prior for each dimension
        dim_keys = ["ed_accel", "spread_anomaly", "fisher_rho"]
        expected_priors = np.array([
            [priors[k]["mu_0"], priors[k]["kappa_0"],
             priors[k]["alpha_0"], priors[k]["beta_0"]]
            for k in dim_keys
        ])  # shape (D, 4)

        for step, x_t in enumerate(calm_obs):
            engine.update(x_t, lambda_macro=0.01)
            state = engine.get_state()
            for d, key in enumerate(dim_keys):
                np.testing.assert_allclose(
                    state.suff_stats[0, d, :],
                    [priors[key]["mu_0"], priors[key]["kappa_0"],
                     priors[key]["alpha_0"], priors[key]["beta_0"]],
                    atol=1e-12,
                    err_msg=f"INV-4 violated at step {step+1}, dim={key}: "
                            f"suff_stats[0] has drifted from prior",
                )


class TestINV6_KappaLinearGrowth:
    """INV-6: kappa[r] == kappa_0 + r after >= r update steps.

    kappa is a pure run-length counter — it grows by 1 per observation
    absorbed, regardless of x_t values. This makes it the definitive
    diagnostic for off-by-one errors in the suff_stats shift.

    Correct:   [5, 6, 7, 8, 9]  for kappa_0=5 after 5 steps
    Corrupted: [6, 6, 7, 8, 9]  — r=0 was overwritten (shift error)
    """

    def test_kappa_invariant_after_5_steps(self, config, engine, calm_obs):
        kappa_0 = config["nig_priors"]["ed_accel"]["kappa_0"]  # 5.0

        for x_t in calm_obs:
            engine.update(x_t, lambda_macro=0.01)

        state = engine.get_state()
        # After 5 steps: kappa[r] == kappa_0 + r for r = 0..4
        for r in range(5):
            expected_kappa = kappa_0 + r
            np.testing.assert_allclose(
                state.suff_stats[r, 0, 1],  # dim=0 (ed_accel), param=kappa
                expected_kappa,
                atol=1e-12,
                err_msg=(
                    f"INV-6: kappa[{r}]={state.suff_stats[r, 0, 1]:.6f} "
                    f"!= expected {expected_kappa}. "
                    f"Correct: {list(range(int(kappa_0), int(kappa_0)+5))}  "
                    f"Got: {[state.suff_stats[i, 0, 1] for i in range(5)]}"
                ),
            )

    def test_step_counter_increments(self, engine, calm_obs):
        for i, x_t in enumerate(calm_obs):
            engine.update(x_t, lambda_macro=0.01)
            assert engine.get_state().t == i + 1


class TestReturnValue:
    """update() must return a valid float in [0, 1]."""

    def test_return_is_scalar_float(self, engine):
        p_cp = engine.update(np.zeros(D), lambda_macro=0.01)
        assert isinstance(p_cp, float)

    def test_return_in_01(self, engine, calm_obs):
        for x_t in calm_obs:
            p_cp = engine.update(x_t, lambda_macro=0.01)
            assert 0.0 <= p_cp <= 1.0, f"p_cp={p_cp} out of [0,1]"


class TestStateSerialisation:
    """get_state / set_state round-trip."""

    def test_state_roundtrip(self, engine):
        # Run a few steps
        for _ in range(3):
            engine.update(np.array([1.0, -0.5, 0.3]), lambda_macro=0.01)

        state1 = engine.get_state()

        # Overwrite with new steps
        engine.update(np.zeros(D), lambda_macro=0.01)

        # Restore
        engine.set_state(state1)
        state2 = engine.get_state()

        np.testing.assert_array_equal(state1.run_length_probs, state2.run_length_probs)
        np.testing.assert_array_equal(state1.suff_stats, state2.suff_stats)
        assert state1.t == state2.t
