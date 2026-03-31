"""Deterministic validation for fitted GaussianNB regime models."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def validate_gaussian_nb(
    model: object,
    *,
    expected_classes: Sequence[str] | None = None,
    feature_count: int | None = None,
) -> dict[str, object]:
    """Validate a fitted GaussianNB model before it can enter production or audit."""
    required_attrs = ("classes_", "theta_", "var_", "class_prior_")
    missing_attrs = [attr for attr in required_attrs if not hasattr(model, attr)]
    if missing_attrs:
        joined = ", ".join(missing_attrs)
        raise ValueError(f"GaussianNB validation failed: missing fitted attributes {joined}.")

    classes = [str(label) for label in model.classes_]
    theta = np.asarray(model.theta_, dtype=float)
    var = np.asarray(model.var_, dtype=float)
    class_prior = np.asarray(model.class_prior_, dtype=float)

    if expected_classes is not None:
        normalized_expected = sorted(str(label) for label in expected_classes)
        if sorted(classes) != normalized_expected:
            raise ValueError(
                "GaussianNB validation failed: "
                f"Expected classes {normalized_expected}, got {sorted(classes)}."
            )

    if theta.ndim != 2:
        raise ValueError("GaussianNB validation failed: theta_ must be a 2D coefficient matrix.")
    if var.shape != theta.shape:
        raise ValueError("GaussianNB validation failed: var_ must match theta_ shape.")
    if class_prior.shape != (theta.shape[0],):
        raise ValueError(
            "GaussianNB validation failed: class_prior_ length must match class dimension."
        )
    if feature_count is not None and theta.shape[1] != int(feature_count):
        raise ValueError(
            "GaussianNB validation failed: "
            f"expected {feature_count} features, got {theta.shape[1]}."
        )
    if len(classes) != theta.shape[0]:
        raise ValueError(
            "GaussianNB validation failed: classes_ length must match coefficient rows."
        )

    _require_finite(theta, "theta_")
    _require_finite(var, "var_")
    _require_finite(class_prior, "class_prior_")

    if np.any(var <= 0.0):
        raise ValueError("GaussianNB validation failed: var_ must be strictly positive.")
    if np.any(class_prior <= 0.0):
        raise ValueError("GaussianNB validation failed: class_prior_ must be strictly positive.")

    prior_sum = float(class_prior.sum())
    if not np.isclose(prior_sum, 1.0, atol=1e-6):
        raise ValueError(
            f"GaussianNB validation failed: class_prior_ must sum to 1.0, got {prior_sum:.8f}."
        )

    return {
        "classes": classes,
        "feature_count": int(theta.shape[1]),
        "theta_min": float(theta.min()),
        "theta_max": float(theta.max()),
        "var_min": float(var.min()),
        "var_max": float(var.max()),
    }


def validate_feature_contract(
    *,
    expected_hash: str | None,
    actual_hash: str,
    expected_features: Sequence[str] | None = None,
    actual_features: Sequence[str] | None = None,
) -> dict[str, object]:
    """Validate that production feature engineering matches the audited DNA contract."""
    if not expected_hash:
        raise ValueError("Audit archive is missing the ProbabilitySeeder feature contract hash.")
    if actual_hash != expected_hash:
        raise ValueError(
            "ProbabilitySeeder feature contract hash mismatch: "
            f"expected {expected_hash}, got {actual_hash}."
        )

    normalized_expected = sorted(str(feature) for feature in (expected_features or []))
    normalized_actual = sorted(str(feature) for feature in (actual_features or []))
    if normalized_expected and normalized_actual != normalized_expected:
        raise ValueError(
            "ProbabilitySeeder feature contract mismatch: "
            f"expected features {normalized_expected}, got {normalized_actual}."
        )

    return {
        "seeder_config_hash": actual_hash,
        "feature_names": list(actual_features or normalized_expected),
    }


def _require_finite(values: np.ndarray, label: str) -> None:
    if not np.isfinite(values).all():
        raise ValueError(f"GaussianNB validation failed: {label} contains non-finite values.")
