import numpy as np
import pandas as pd
import pytest

from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard


def test_fit_baseline_uses_shrinkage_to_regularize_collinear_covariance():
    rng = np.random.default_rng(7)
    base = rng.normal(size=300)
    frame = pd.DataFrame(
        {
            "spread_21d": base,
            "spread_absolute": base * 1.0001,
            "pmi_momentum": rng.normal(scale=0.5, size=300),
            "labor_slack": rng.normal(scale=0.8, size=300),
        }
    )

    empirical_cond = np.linalg.cond(frame.cov().values + np.eye(frame.shape[1]) * 1e-6)
    guard = MahalanobisGuard()
    guard.fit_baseline(frame)

    diagnostics = guard.baseline_diagnostics()

    assert diagnostics["covariance_estimator"] in {"ledoit_wolf", "oas", "shrunk_empirical"}
    assert diagnostics["shrinkage_alpha"] > 0.0
    assert diagnostics["condition_number"] < empirical_cond
    assert diagnostics["condition_number"] < 10_000


def test_regime_conditioned_distance_blends_calm_and_stress_covariance():
    rng = np.random.default_rng(11)
    calm = pd.DataFrame(
        rng.normal(scale=[0.25, 0.20, 0.30], size=(240, 3)),
        columns=["spread_21d", "pmi_momentum", "liquidity_velocity"],
    )
    stress = pd.DataFrame(
        rng.normal(scale=[2.0, 2.5, 3.0], size=(80, 3)),
        columns=calm.columns,
    )
    frame = pd.concat([calm, stress], ignore_index=True)
    stress_mask = pd.Series([False] * len(calm) + [True] * len(stress))

    guard = MahalanobisGuard()
    guard.fit_baseline(frame, stress_mask=stress_mask)
    x = np.array([1.6, 2.0, -2.2])

    calm_distance = guard.distance_diagnostics(x, stress_probability=0.0)[
        "mahalanobis_distance"
    ]
    stressed_distance = guard.distance_diagnostics(x, stress_probability=1.0)[
        "mahalanobis_distance"
    ]

    assert stressed_distance < calm_distance
    assert guard.distance_diagnostics(x, stress_probability=0.75)["stress_probability"] == pytest.approx(
        0.75
    )


def test_macro_derivative_subspace_reports_student_t_penalty():
    rng = np.random.default_rng(19)
    frame = pd.DataFrame(
        {
            "spread_21d": rng.normal(size=200),
            "pmi_momentum": rng.normal(size=200),
            "labor_slack": rng.normal(size=200),
            "liquidity_velocity": rng.normal(size=200),
        }
    )
    guard = MahalanobisGuard(macro_derivative_dof=5.0)
    guard.fit_baseline(frame)

    diagnostics = guard.distance_diagnostics(
        np.array([0.1, -4.0, -3.5, 4.5]),
        stress_probability=0.5,
    )
    derivative = diagnostics["macro_derivative_subspace"]

    assert derivative["distribution"] == "student_t"
    assert derivative["degrees_of_freedom"] == pytest.approx(5.0)
    assert derivative["dimension"] == 3
    assert derivative["distance_squared"] > 0.0
    assert np.isfinite(derivative["student_t_log_penalty"])
    assert derivative["student_t_log_penalty"] < 0.0


def test_outlier_status_does_not_emit_dead_feature_quality():
    rng = np.random.default_rng(23)
    frame = pd.DataFrame(
        rng.normal(size=(200, 3)),
        columns=["pmi_momentum", "labor_slack", "liquidity_velocity"],
    )
    guard = MahalanobisGuard()
    guard.fit_baseline(frame)

    is_ood, distance = guard.is_outlier(
        np.array([8.0, -8.0, 8.0]),
        threshold=3.0,
        stress_probability=0.0,
        return_distance=True,
    )
    diagnostics = guard.distance_diagnostics(np.array([8.0, -8.0, 8.0]))

    assert is_ood is True
    assert distance > 3.0
    assert "dead_features" not in diagnostics
    assert "feature_quality_weights" not in diagnostics
