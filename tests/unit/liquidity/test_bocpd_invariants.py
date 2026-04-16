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
        _expected_priors = np.array([
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
    """INV-6: kappa[r] follows forgetting-factor decay formula after >= r update steps.

    With forgetting_lambda=0.98, kappa starts from kappa_0 (fresh prior) and evolves:
        kappa after 1 absorption = λ * kappa_0 + 1
        kappa after r absorptions = λ^r * kappa_0 + (1-λ^r)/(1-λ)

    r=0 is always reset to the raw prior (INV-4), so kappa[0] == kappa_0.
    r=1..4 carry increasing absorption counts.

    Correct pattern for kappa_0=5, λ=0.98, r=0..4:
        r=0 → 5.0  (raw prior, always reset)
        r=1 → 0.98*5 + 1 = 5.9
        r=2 → 0.98*5.9 + 1 = 6.782
        r=3 → 0.98*6.782 + 1 = 7.646
        r=4 → 0.98*7.646 + 1 = 8.493
    """

    def test_kappa_invariant_after_5_steps(self, config, engine, calm_obs):
        kappa_0 = config["nig_priors"]["ed_accel"]["kappa_0"]  # 5.0
        lam = config["forgetting"]["lambda"]

        for x_t in calm_obs:
            engine.update(x_t, lambda_macro=0.01)

        state = engine.get_state()
        # r=0: always raw prior (INV-4)
        np.testing.assert_allclose(
            state.suff_stats[0, 0, 1], kappa_0, atol=1e-12,
            err_msg="INV-6: kappa[0] must always equal kappa_0 (INV-4)",
        )
        # r=1..4: follows decay formula
        for r in range(1, 5):
            expected_kappa = lam**r * kappa_0 + (1.0 - lam**r) / (1.0 - lam)
            np.testing.assert_allclose(
                state.suff_stats[r, 0, 1],
                expected_kappa,
                atol=1e-10,
                err_msg=(
                    f"INV-6: kappa[{r}]={state.suff_stats[r, 0, 1]:.6f} "
                    f"!= decay-formula expected {expected_kappa:.6f}. "
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


class TestRegimeDiagnostics:
    """BOCPD must expose regime water-level diagnostics separately from p_cp."""

    def test_last_regime_diagnostics_available_after_update(self, engine):
        engine.update(np.array([0.0, 3.0, 0.0]), lambda_macro=0.01)

        diag = engine.last_regime_diagnostics

        required = {
            "dominant_run_length",
            "dominant_run_prob",
            "regime_sigma2_ed",
            "regime_sigma2_spread",
            "regime_sigma2_fisher",
            "regime_severity_base",
            "regime_resonance_pr",
            "regime_resonance_multiplier",
            "regime_v_ed",
            "regime_v_spread",
            "regime_v_fisher",
            "regime_v_capped_ed",
            "regime_v_capped_spread",
            "regime_v_capped_fisher",
            "regime_severity",
        }
        assert required <= set(diag)
        assert diag["dominant_run_length"] >= 0
        assert 0.0 <= diag["dominant_run_prob"] <= 1.0
        assert 0.0 <= diag["regime_severity"] < 1.0

    def test_dimension_caps_limit_single_dimension_contribution(self, config):
        config = {
            **config,
            "regime_severity": {
                **config["regime_severity"],
                "weights": {"ed_accel": 0.0, "spread_anomaly": 1.0, "fisher_rho": 0.0},
                "dimension_caps": {
                    "ed_accel": 1.0,
                    "spread_anomaly": 0.5,
                    "fisher_rho": 1.0,
                },
            },
        }
        engine = BOCPDEngine(config)
        state = engine.get_state()
        state.run_length_probs[:] = 0.0
        state.run_length_probs[10] = 1.0
        state.suff_stats[10, 1, 3] = state.suff_stats[10, 1, 3] * 1_000.0
        engine.set_state(state)

        diag = engine.last_regime_diagnostics

        assert diag["regime_v_spread"] > 0.5
        assert diag["regime_v_capped_spread"] == pytest.approx(0.5)
        assert diag["regime_severity_base"] == pytest.approx(1.0 - np.exp(-0.5))
        assert diag["regime_resonance_pr"] == pytest.approx(1.0)
        assert diag["regime_resonance_multiplier"] == pytest.approx(1.0 / 3.0)
        assert diag["regime_severity"] == pytest.approx((1.0 - np.exp(-0.5)) / 3.0)

    def test_resonance_pr_is_computed_from_unweighted_dimension_intensity(self, config):
        config = {
            **config,
            "regime_severity": {
                **config["regime_severity"],
                "weights": {"ed_accel": 0.10, "spread_anomaly": 0.80, "fisher_rho": 0.10},
                "dimension_caps": {
                    "ed_accel": 1.0,
                    "spread_anomaly": 1.0,
                    "fisher_rho": 1.0,
                },
                "resonance_gamma": 1.0,
            },
        }
        engine = BOCPDEngine(config)
        state = engine.get_state()
        state.run_length_probs[:] = 0.0
        state.run_length_probs[10] = 1.0
        state.suff_stats[10, :, 3] = state.suff_stats[10, :, 3] * np.exp(0.5)
        engine.set_state(state)

        diag = engine.last_regime_diagnostics

        assert diag["regime_resonance_pr"] == pytest.approx(3.0)
        assert diag["regime_resonance_multiplier"] == pytest.approx(1.0)
        assert diag["regime_severity"] == pytest.approx(diag["regime_severity_base"])

    def test_resonance_pr_continuously_penalizes_isolated_spike(self, config):
        config = {
            **config,
            "regime_severity": {
                **config["regime_severity"],
                "weights": {"ed_accel": 0.0, "spread_anomaly": 1.0, "fisher_rho": 0.0},
                "resonance_gamma": 2.0,
            },
        }
        engine = BOCPDEngine(config)
        state = engine.get_state()
        state.run_length_probs[:] = 0.0
        state.run_length_probs[10] = 1.0
        state.suff_stats[10, 1, 3] = state.suff_stats[10, 1, 3] * np.exp(1.0)
        engine.set_state(state)

        diag = engine.last_regime_diagnostics

        assert diag["regime_resonance_pr"] == pytest.approx(1.0)
        assert diag["regime_resonance_multiplier"] == pytest.approx((1.0 / 3.0) ** 2)
        assert diag["regime_severity"] == pytest.approx(diag["regime_severity_base"] / 9.0)


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
