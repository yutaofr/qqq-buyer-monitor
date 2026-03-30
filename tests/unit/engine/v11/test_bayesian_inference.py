import numpy as np

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine


class MockKDE:
    def __init__(self, likelihood_value):
        self.log_likelihood = np.log(likelihood_value)
    def score_samples(self, X):
        return [self.log_likelihood]

def test_sigmoid_prior_shift():
    # Setup mock KDEs (assume all evidences are equally likely for pure prior testing)
    mock_kdes = {
        "MID_CYCLE": MockKDE(0.1),
        "BUST": MockKDE(0.1),
        "CAPITULATION": MockKDE(0.1),
        "RECOVERY": MockKDE(0.1),
        "LATE_CYCLE": MockKDE(0.1)
    }

    base_priors = {
        "MID_CYCLE": 0.8,
        "BUST": 0.05,
        "CAPITULATION": 0.05,
        "RECOVERY": 0.05,
        "LATE_CYCLE": 0.05
    }

    engine = BayesianInferenceEngine(
        kde_models=mock_kdes,
        base_priors=base_priors,
        sigmoid_alpha=0.01,  # Gentle slope for testing
        spread_baseline=400.0
    )

    dummy_pca = np.array([0.0, 0.0])

    # 1. Normal environment (Spread = 300bps) -> Shift should be 0 (no negative shift)
    posteriors_normal = engine.infer_posterior(dummy_pca, current_spread=300.0)
    assert np.isclose(engine._compute_prior_shift(300.0), 0.0)
    assert np.isclose(posteriors_normal["BUST"], 0.05)
    assert np.isclose(posteriors_normal["MID_CYCLE"], 0.80)

    # 2. Elevated environment (Spread = 500bps) -> Mild shift
    shift_elevated = engine._compute_prior_shift(500.0)
    assert 0.0 < shift_elevated < 0.3
    posteriors_elevated = engine.infer_posterior(dummy_pca, current_spread=500.0)
    assert posteriors_elevated["BUST"] > 0.05
    assert posteriors_elevated["MID_CYCLE"] < 0.80

    # 3. Extreme environment (Spread = 1000bps) -> Massive shift
    shift_extreme = engine._compute_prior_shift(1000.0)
    assert shift_extreme > 0.49  # Almost maxed out at 0.5
    posteriors_extreme = engine.infer_posterior(dummy_pca, current_spread=1000.0)

    # BUST and CAP should absorb the probability
    assert posteriors_extreme["BUST"] > 0.25
    assert posteriors_extreme["MID_CYCLE"] < 0.40

    # 4. Math property: Total probability must always be 1.0
    assert np.isclose(sum(posteriors_normal.values()), 1.0)
    assert np.isclose(sum(posteriors_elevated.values()), 1.0)
    assert np.isclose(sum(posteriors_extreme.values()), 1.0)

def test_kde_likelihood_domination():
    # If a specific regime KDE returns massively higher likelihood, it should dominate
    mock_kdes = {
        "MID_CYCLE": MockKDE(1e-5),
        "BUST": MockKDE(0.99), # Overwhelming evidence for BUST
        "CAPITULATION": MockKDE(1e-5),
        "RECOVERY": MockKDE(1e-5),
        "LATE_CYCLE": MockKDE(1e-5)
    }

    base_priors = {k: 0.2 for k in mock_kdes.keys()}

    engine = BayesianInferenceEngine(
        kde_models=mock_kdes,
        base_priors=base_priors
    )

    posteriors = engine.infer_posterior(np.array([0,0]), current_spread=400.0)
    assert posteriors["BUST"] > 0.99
    assert np.isclose(sum(posteriors.values()), 1.0)
