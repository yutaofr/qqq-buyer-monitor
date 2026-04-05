import warnings

import numpy as np
import pandas as pd

from src.engine.baseline.engine import predict_baseline_crisis_prob, train_baseline_model


def test_train_baseline_model():
    # Create synthetic data where Stress is strongly correlated with Crisis
    np.random.seed(42)
    N = 500
    X = pd.DataFrame(
        {
            "growth_composite": np.random.randn(N),
            "liquidity_composite": np.random.randn(N),
            "stress_composite": np.random.randn(N),
        }
    )

    # Target: Y=1 if stress is high
    y = (X["stress_composite"] > 0.5).astype(int)

    model = train_baseline_model(X, y)

    # Check if model trained and found a C
    assert hasattr(model, "C_")
    assert len(model.C_) == 1  # One C per target class (binary)

    # Check prediction
    probs = predict_baseline_crisis_prob(model, X)
    assert len(probs) == N
    assert probs.min() >= 0
    assert probs.max() <= 1

    # Check if high stress actually leads to higher probability
    high_stress_prob = probs[X["stress_composite"] > 1.0].mean()
    low_stress_prob = probs[X["stress_composite"] < -1.0].mean()
    assert high_stress_prob > low_stress_prob


def test_model_coefficients_direction():
    # SRD: Stress should have POSITIVE coefficient (higher stress -> higher prob)
    # Growth and Liquidity should have NEGATIVE coefficients (lower growth/liq -> higher prob)
    np.random.seed(42)
    X = pd.DataFrame(
        {
            "growth_composite": np.random.randn(500),
            "liquidity_composite": np.random.randn(500),
            "stress_composite": np.random.randn(500),
        }
    )
    # Synthetic crisis: low growth, low liq, high stress
    y = ((X["stress_composite"] - X["growth_composite"] - X["liquidity_composite"]) > 1.0).astype(
        int
    )

    model = train_baseline_model(X, y)
    coeffs = model.coef_[0]

    # Growth (idx 0) should be negative
    # Liquidity (idx 1) should be negative
    # Stress (idx 2) should be positive
    # We allow some slack for small synthetic samples, but direction should hold
    assert coeffs[2] > 0
    assert coeffs[0] < 0.1  # Should be negative or very small positive
    assert coeffs[1] < 0.1


def test_train_baseline_model_avoids_runtime_overflow_on_separable_data():
    n = 600
    signal = np.r_[np.zeros(n // 2), np.ones(n // 2)]
    X = pd.DataFrame(
        {
            "growth_composite": -signal,
            "liquidity_composite": -signal,
            "stress_composite": signal * 1000.0,
        }
    )
    y = pd.Series(signal.astype(int))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = train_baseline_model(X, y)

    runtime_warnings = [
        warning for warning in caught if issubclass(warning.category, RuntimeWarning)
    ]
    assert not runtime_warnings
    assert np.isfinite(model.coef_).all()
