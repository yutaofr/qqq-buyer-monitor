import numpy as np
import pytest

from src.engine.baseline.constrained_model import ConstrainedLogisticRegression


def test_constrained_lr_basic_fit():
    """Test if the model can fit a simple separable case."""
    X = np.array([[1.0, 2.0], [2.0, 1.0], [1.1, 2.1], [1.9, 0.9]])
    y = np.array([1, 0, 1, 0])

    model = ConstrainedLogisticRegression(C=1.0)
    model.fit(X, y)

    assert model.coef_ is not None
    assert model.intercept_ is not None

    probs = model.predict_proba(X)
    assert probs.shape == (4, 2)
    assert np.all(probs >= 0) and np.all(probs <= 1)

    # Check if it predicts correctly
    preds = (probs[:, 1] > 0.5).astype(int)
    np.testing.assert_array_equal(preds, y)


def test_constrained_lr_bounds_respect():
    """Test if the model strictly respects the provided bounds even with contradicting data."""
    # Data where feature 0 is STRONGLY positive for class 1
    # But we set a bound that feature 0 coefficient must be <= 0
    X = np.array([[10.0, 1.0], [10.5, 1.1], [-10.0, -1.0], [-10.5, -1.1]])
    y = np.array([1, 1, 0, 0])  # Positive correlation between X[0] and y

    # Rule: Feature 0 must be NEGATIVE or 0
    bounds = [(None, 0.0), (None, None)]

    model = ConstrainedLogisticRegression(C=1.0, bounds=bounds)
    model.fit(X, y)

    # Coeff for feature 0 should be <= 0.0
    assert model.coef_[0, 0] <= 1e-10  # Floating point slack

    # Check feature 1 (unconstrained, should be positive to compensate)
    assert model.coef_[0, 1] > 0


def test_constrained_lr_no_intercept():
    """Test model without intercept."""
    X = np.array([[1.0], [-1.0]])
    y = np.array([1, 0])

    model = ConstrainedLogisticRegression(fit_intercept=False)
    model.fit(X, y)

    assert model.intercept_[0] == 0.0
    assert model.coef_[0, 0] > 0


def test_constrained_lr_invalid_bounds():
    """Test error handling for mismatched bounds."""
    X = np.ones((5, 2))
    y = np.ones(5)
    model = ConstrainedLogisticRegression(bounds=[(0, 1)])  # Only 1 bound for 2 features
    with pytest.raises(ValueError, match="Bounds length 1 must match n_features 2"):
        model.fit(X, y)
