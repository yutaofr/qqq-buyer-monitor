import math
import pytest

from src.engine.v11.core.kelly_criterion import (
    compute_regime_expected_sharpe,
    compute_regime_sharpe_variance,
    compute_kelly_fraction,
    kelly_fraction_to_deployment_state,
    kelly_fraction_to_deployment_multiplier,
)

DEFAULT_SHARPES = {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.2, "BUST": -0.8, "RECOVERY": 1.2}

def test_compute_expected_sharpe_normal():
    # TC-K01
    posteriors = {"MID_CYCLE": 0.5, "BUST": 0.5}
    sharpe = compute_regime_expected_sharpe(posteriors, DEFAULT_SHARPES)
    assert math.isclose(sharpe, 0.1)

def test_compute_expected_sharpe_missing_regime():
    # TC-K02
    posteriors = {"MID_CYCLE": 0.5, "UNKNOWN": 0.5}
    sharpe = compute_regime_expected_sharpe(posteriors, DEFAULT_SHARPES)
    assert math.isclose(sharpe, 0.5)

def test_compute_expected_sharpe_empty():
    # TC-K03
    sharpe = compute_regime_expected_sharpe({}, DEFAULT_SHARPES)
    assert sharpe == 0.0

def test_compute_expected_sharpe_all_zero():
    # TC-K04
    posteriors = {"MID_CYCLE": 0.0, "BUST": 0.0}
    sharpe = compute_regime_expected_sharpe(posteriors, DEFAULT_SHARPES)
    assert sharpe == 0.0

def test_compute_variance_normal():
    # TC-K05
    posteriors = {"MID_CYCLE": 0.5, "BUST": 0.5}
    # Expected sharpe = 0.1
    # Var = 0.5 * (1.0 - 0.1)^2 + 0.5 * (-0.8 - 0.1)^2 = 0.5(0.81) + 0.5(0.81) = 0.81
    var = compute_regime_sharpe_variance(posteriors, DEFAULT_SHARPES, 0.1)
    assert math.isclose(var, 0.81)

def test_compute_variance_zero_returns_min():
    # TC-K06
    posteriors = {"MID_CYCLE": 1.0}
    var = compute_regime_sharpe_variance(posteriors, DEFAULT_SHARPES, 1.0)
    assert math.isclose(var, 1e-6)

def test_compute_variance_empty():
    # TC-K07
    var = compute_regime_sharpe_variance({}, DEFAULT_SHARPES, 0.5)
    assert math.isclose(var, 1e-6)

def test_compute_variance_unknown_regime():
    # TC-K08
    posteriors = {"UNKNOWN": 1.0}
    var = compute_regime_sharpe_variance(posteriors, DEFAULT_SHARPES, 0.0)
    assert math.isclose(var, 1e-6)

def test_kelly_fraction_basic():
    # TC-K09
    posteriors = {"RECOVERY": 1.0}
    # Expected Sharpe = 1.2, base Var = 1e-6, tilt = 1.0
    # True frac = 1.2 / 1e-6 * 0.5 = huge -> clipped to 1.0
    k = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=DEFAULT_SHARPES,
        entropy=0.0,
        erp_percentile=0.5,
        kelly_scale=0.5,
        erp_weight=0.4
    )
    assert math.isclose(k, 1.0)

def test_kelly_fraction_negative():
    # TC-K10
    posteriors = {"BUST": 1.0}
    k = compute_kelly_fraction(
        posteriors=posteriors, regime_sharpes=DEFAULT_SHARPES,
        entropy=0.0, erp_percentile=0.5
    )
    assert math.isclose(k, -1.0)

def test_kelly_fraction_with_entropy():
    # TC-K11
    # expected = 0.1, var = 0.81
    posteriors = {"MID_CYCLE": 0.5, "BUST": 0.5}
    # entropy = 0.3 -> total var = 0.81 + 0.09 = 0.90
    # tilt = 1.0 => raw = 0.1 / 0.9 = 0.111... -> * 0.5
    k = compute_kelly_fraction(
        posteriors=posteriors, regime_sharpes=DEFAULT_SHARPES,
        entropy=0.3, erp_percentile=0.5
    )
    assert math.isclose(k, (0.1 / 0.9) * 0.5)

def test_kelly_fraction_with_erp():
    # TC-K12
    posteriors = {"MID_CYCLE": 0.5, "BUST": 0.5} # edge=0.1
    # erp_percentile = 1.0 -> tilt = 1.0 + 0.5 * 0.4 = 1.2
    # var = 0.81 + 0 = 0.81
    # raw = 0.1 * 1.2 / 0.81
    k = compute_kelly_fraction(
        posteriors=posteriors, regime_sharpes=DEFAULT_SHARPES,
        entropy=0.0, erp_percentile=1.0
    )
    assert math.isclose(k, (0.1 * 1.2 / 0.81) * 0.5)

def test_kelly_fraction_clipping_inputs():
    # TC-K13
    posteriors = {"MID_CYCLE": 0.5, "BUST": 0.5} # edge = 0.1, base var = 0.81
    # entropy = 1.5 -> clipped to 1.0 -> var = 0.81 + 1.0 = 1.81
    # erp = -1.0 -> clipped to 0.0 -> tilt = 1.0 - 0.5*0.4 = 0.8
    # raw = 0.1 * 0.8 / 1.81 -> * 0.5
    k = compute_kelly_fraction(
        posteriors=posteriors, regime_sharpes=DEFAULT_SHARPES,
        entropy=1.5, erp_percentile=-1.0
    )
    expected = (0.1 * 0.8 / 1.81) * 0.5
    assert math.isclose(k, expected)

def test_kelly_state_pause():
    # TC-K14
    assert kelly_fraction_to_deployment_state(-0.5) == "DEPLOY_PAUSE"
    assert kelly_fraction_to_deployment_state(0.0) == "DEPLOY_PAUSE"

def test_kelly_state_slow():
    # TC-K15
    assert kelly_fraction_to_deployment_state(0.01) == "DEPLOY_SLOW"
    assert kelly_fraction_to_deployment_state(0.25) == "DEPLOY_SLOW"

def test_kelly_state_base():
    # TC-K16
    assert kelly_fraction_to_deployment_state(0.26) == "DEPLOY_BASE"
    assert kelly_fraction_to_deployment_state(0.60) == "DEPLOY_BASE"

def test_kelly_state_fast():
    # TC-K17
    assert kelly_fraction_to_deployment_state(0.61) == "DEPLOY_FAST"
    assert kelly_fraction_to_deployment_state(1.0) == "DEPLOY_FAST"

def test_kelly_multiplier_pause():
    # TC-K18
    assert kelly_fraction_to_deployment_multiplier(0.0) == 0.0

def test_kelly_multiplier_slow():
    # TC-K19
    assert kelly_fraction_to_deployment_multiplier(0.2) == 0.5

def test_kelly_multiplier_base_and_fast():
    # TC-K20
    assert kelly_fraction_to_deployment_multiplier(0.5) == 1.0
    assert kelly_fraction_to_deployment_multiplier(0.8) == 2.0
