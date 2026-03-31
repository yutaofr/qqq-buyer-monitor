import numpy as np
import pytest
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.model_validation import validate_feature_contract, validate_gaussian_nb


def _fit_valid_model() -> GaussianNB:
    X = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.2],
            [1.0, 1.1],
            [1.2, 1.3],
            [2.0, 2.2],
            [2.1, 2.4],
        ]
    )
    y = np.array(["BUST", "BUST", "MID_CYCLE", "MID_CYCLE", "RECOVERY", "RECOVERY"])
    return GaussianNB(var_smoothing=1e-2).fit(X, y)


def test_validate_gaussian_nb_accepts_finite_positive_coefficients():
    model = _fit_valid_model()

    validate_gaussian_nb(model, expected_classes=["BUST", "MID_CYCLE", "RECOVERY"])


def test_validate_gaussian_nb_rejects_non_finite_theta():
    model = _fit_valid_model()
    model.theta_[0, 0] = np.nan

    with pytest.raises(ValueError, match="theta_"):
        validate_gaussian_nb(model, expected_classes=["BUST", "MID_CYCLE", "RECOVERY"])


def test_validate_gaussian_nb_rejects_class_drift():
    model = _fit_valid_model()

    with pytest.raises(ValueError, match="Expected classes"):
        validate_gaussian_nb(model, expected_classes=["BUST", "LATE_CYCLE", "MID_CYCLE"])


def test_validate_feature_contract_rejects_hash_drift():
    with pytest.raises(ValueError, match="feature contract hash"):
        validate_feature_contract(
            expected_hash="sha256:expected",
            actual_hash="sha256:actual",
            expected_features=["spread_21d"],
            actual_features=["spread_21d"],
        )
