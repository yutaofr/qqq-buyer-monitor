import numpy as np
import pandas as pd
import pytest

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine


class MockClassifier:
    def __init__(self, regimes):
        self.classes_ = regimes
        self.n_features = 5
        self.theta_ = np.zeros((len(regimes), 5))
        self.var_ = np.ones((len(regimes), 5))

@pytest.fixture
def engine():
    regimes = ["RECOVERY", "MID_CYCLE", "LATE_CYCLE", "BUST"]
    priors = {r: 0.25 for r in regimes}
    return BayesianInferenceEngine(base_priors=priors)

@pytest.fixture
def logical_constraints():
    import json
    from pathlib import Path
    # Robust path resolution for Docker and Local
    possible_paths = [
        Path("/app/src/engine/v11/resources/logical_constraints.json"),
        Path(__file__).parents[3] / "src" / "engine" / "v11" / "resources" / "logical_constraints.json"
    ]
    for path in possible_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(f"logical_constraints.json not found in any of {possible_paths}")

def test_recovery_penalized_in_death_cross(engine, logical_constraints):
    """If MA50 < MA200 (ma_z < -0.5), RECOVERY should be penalized."""
    classifier = MockClassifier(engine.regimes)
    evidence = pd.DataFrame([np.zeros(5)], columns=["f1", "f2", "f3", "f4", "f5"])

    # CASE 1: Death Cross
    vals_death = {"qqq_ma_ratio": -1.0}
    post_death, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=vals_death,
        runtime_priors=engine.base_priors,
        tau=1.0,
        logical_constraints=logical_constraints
    )

    # CASE 2: Golden Cross
    vals_golden = {"qqq_ma_ratio": 1.0}
    post_golden, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=vals_golden,
        runtime_priors=engine.base_priors,
        tau=1.0,
        logical_constraints=logical_constraints
    )

    # RECOVERY should be lower in Death Cross than in Golden Cross
    assert post_death["RECOVERY"] < post_golden["RECOVERY"]
    print(f"Post Death RECOVERY: {post_death['RECOVERY']:.4f}")
    print(f"Post Golden RECOVERY: {post_golden['RECOVERY']:.4f}")

def test_late_stage_confirmed_by_divergence(engine, logical_constraints):
    """If MA < 0 and PV Divergence is extreme, RECOVERY/MID should be dampened."""
    classifier = MockClassifier(engine.regimes)
    evidence = pd.DataFrame([np.zeros(5)], columns=["f1", "f2", "f3", "f4", "f5"])

    vals_divergence = {
        "qqq_ma_ratio": -0.1,
        "qqq_pv_divergence_z": -2.0,
        "credit_acceleration": 1.5
    }

    post_div, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=vals_divergence,
        runtime_priors=engine.base_priors,
        tau=1.0,
        logical_constraints=logical_constraints
    )

    # RECOVERY and MID_CYCLE should be heavily dampened
    assert post_div["RECOVERY"] < 0.1
    assert post_div["MID_CYCLE"] < 0.1
    # BUST or LATE_CYCLE should dominate
    assert post_div["BUST"] > post_div["RECOVERY"]
    assert post_div["LATE_CYCLE"] > post_div["MID_CYCLE"]

def test_liquidity_shock_forces_bust(engine, logical_constraints):
    """If Liquidity Velocity collapses (-2.0), BUST should be boosted."""
    classifier = MockClassifier(engine.regimes)
    evidence = pd.DataFrame([np.zeros(5)], columns=["f1", "f2", "f3", "f4", "f5"])

    vals_shock = {
        "qqq_ma_ratio": -1.0,
        "liquidity_velocity": -3.0
    }

    post_shock, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=vals_shock,
        runtime_priors=engine.base_priors,
        tau=1.0,
        logical_constraints=logical_constraints
    )

    # BUST should be the dominant regime
    assert post_shock["BUST"] == max(post_shock.values())
    assert post_shock["MID_CYCLE"] < 0.05
