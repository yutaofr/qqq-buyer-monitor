from __future__ import annotations

import numpy as np
import pandas as pd
import warnings
from scipy.spatial.distance import mahalanobis

try:
    from sklearn.covariance import LedoitWolf, OAS
except Exception:  # pragma: no cover - sklearn is a runtime dependency in this project.
    LedoitWolf = None
    OAS = None


_DEFAULT_MACRO_DERIVATIVE_FEATURES = frozenset(
    {
        "pmi_momentum",
        "labor_slack",
        "liquidity_velocity",
        "credit_acceleration",
        "breakeven_accel",
        "core_capex_momentum",
    }
)


class MahalanobisGuard:
    """
    Robust geometric outlier detector.

    The guard treats spatial surprise as a geometry/confidence signal only. It
    never emits source-quality gates and never marks present features as dead.
    """

    def __init__(
        self,
        *,
        covariance_estimator: str = "ledoit_wolf",
        macro_derivative_features: set[str] | frozenset[str] | None = None,
        macro_derivative_dof: float = 5.0,
    ):
        self.covariance_estimator = str(covariance_estimator)
        self.macro_derivative_features = set(
            macro_derivative_features or _DEFAULT_MACRO_DERIVATIVE_FEATURES
        )
        self.macro_derivative_dof = max(1.0, float(macro_derivative_dof))
        self.feature_names: list[str] = []
        self.mean: np.ndarray | None = None
        self.cov: np.ndarray | None = None
        self.inv_cov: np.ndarray | None = None
        self.calm_cov: np.ndarray | None = None
        self.stress_cov: np.ndarray | None = None
        self.is_initialized = False
        self._baseline_diagnostics: dict[str, object] = {}

    def fit_baseline(
        self,
        historical_features: pd.DataFrame,
        *,
        stress_mask: pd.Series | np.ndarray | list[bool] | None = None,
    ) -> None:
        """
        Fit robust covariance baselines.

        If a stress mask is supplied, the guard additionally fits calm and
        stressed covariance matrices and blends them at evaluation time:

        Sigma_t = (1 - pi_stress) Sigma_calm + pi_stress Sigma_stress
        """
        if historical_features.empty:
            return

        frame = self._clean_frame(historical_features)
        if frame.empty:
            return

        self.feature_names = list(frame.columns)
        self.mean, self.cov, self.inv_cov, base_diag = self._fit_covariance(frame)
        self.calm_cov = self.cov
        self.stress_cov = self.cov

        stress_diag: dict[str, object] = {"enabled": False}
        if stress_mask is not None:
            mask = pd.Series(stress_mask, index=historical_features.index).reindex(frame.index)
            mask = mask.fillna(False).astype(bool)
            min_rows = max(20, len(self.feature_names) + 5)
            calm = frame.loc[~mask]
            stress = frame.loc[mask]
            if len(calm) >= min_rows and len(stress) >= min_rows:
                _, self.calm_cov, _, calm_diag = self._fit_covariance(calm)
                _, self.stress_cov, _, stress_fit_diag = self._fit_covariance(stress)
                stress_diag = {
                    "enabled": True,
                    "calm_rows": int(len(calm)),
                    "stress_rows": int(len(stress)),
                    "calm_condition_number": calm_diag["condition_number"],
                    "stress_condition_number": stress_fit_diag["condition_number"],
                }

        self._baseline_diagnostics = {
            **base_diag,
            "rows": int(len(frame)),
            "feature_count": int(len(self.feature_names)),
            "features": list(self.feature_names),
            "stress_baseline": stress_diag,
        }
        self.is_initialized = True

    def baseline_diagnostics(self) -> dict[str, object]:
        return dict(self._baseline_diagnostics)

    def distance_diagnostics(
        self,
        current_vector: np.ndarray,
        *,
        stress_probability: float = 0.0,
    ) -> dict[str, object]:
        if not self.is_initialized or self.mean is None or self.cov is None:
            return {
                "mahalanobis_distance": 0.0,
                "adjusted_mahalanobis_distance": 0.0,
                "stress_probability": 0.0,
            }

        x = np.asarray(current_vector, dtype=float)
        pi_stress = float(np.clip(stress_probability, 0.0, 1.0))
        cov = self._blended_covariance(pi_stress)
        inv_cov = self._safe_pinv(cov)
        raw_distance = float(mahalanobis(x, self.mean, inv_cov))
        raw_d2 = raw_distance * raw_distance
        derivative = self._macro_derivative_diagnostics(x, cov)
        adjusted_d2 = max(
            0.0,
            raw_d2
            - float(derivative.get("gaussian_distance_squared", 0.0))
            + float(derivative.get("student_t_equivalent_distance_squared", 0.0)),
        )

        sign, logdet = np.linalg.slogdet(cov)
        return {
            "mahalanobis_distance": raw_distance,
            "mahalanobis_distance_squared": raw_d2,
            "adjusted_mahalanobis_distance": float(np.sqrt(adjusted_d2)),
            "adjusted_mahalanobis_distance_squared": float(adjusted_d2),
            "stress_probability": pi_stress,
            "condition_number": float(np.linalg.cond(cov)),
            "log_determinant": float(logdet),
            "determinant_sign": float(sign),
            "macro_derivative_subspace": derivative,
        }

    def calculate_outlier_multiplier(
        self,
        current_vector: np.ndarray,
        *,
        stress_probability: float = 0.0,
    ) -> float:
        """Smooth confidence multiplier based on robust adjusted distance."""
        if not self.is_initialized:
            return 1.0

        try:
            d_m = float(
                self.distance_diagnostics(
                    current_vector,
                    stress_probability=stress_probability,
                )["adjusted_mahalanobis_distance"]
            )
            excess_distance = max(0.0, d_m - 2.3)
            multiplier = np.exp(-0.15 * excess_distance)
            return float(np.clip(multiplier, 0.5, 1.0))
        except Exception:
            return 1.0

    def is_outlier(
        self,
        current_vector: np.ndarray,
        threshold: float = 4.0,
        return_distance: bool = False,
        *,
        stress_probability: float = 0.0,
    ) -> bool | tuple[bool, float]:
        """Binary OOD trigger using stress-conditioned, heavy-tail-adjusted distance."""
        if not self.is_initialized:
            return (False, 0.0) if return_distance else False

        try:
            diagnostics = self.distance_diagnostics(
                current_vector,
                stress_probability=stress_probability,
            )
            d_m = float(diagnostics["adjusted_mahalanobis_distance"])
            is_ood = bool(d_m > float(threshold))
            return (is_ood, d_m) if return_distance else is_ood
        except Exception:
            return (False, 0.0) if return_distance else False

    @staticmethod
    def _clean_frame(historical_features: pd.DataFrame) -> pd.DataFrame:
        return (
            historical_features.apply(pd.to_numeric, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .dropna(axis=0, how="any")
        )

    def _fit_covariance(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
        values = frame.to_numpy(dtype=float)
        mean = values.mean(axis=0)
        centered = values - mean

        estimator_name = self.covariance_estimator
        shrinkage_alpha = 0.0
        cov: np.ndarray
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                if estimator_name == "oas" and OAS is not None:
                    estimator = OAS().fit(values)
                elif LedoitWolf is not None:
                    estimator_name = "ledoit_wolf"
                    estimator = LedoitWolf().fit(values)
                else:
                    raise RuntimeError("sklearn covariance estimators unavailable")
            cov = np.asarray(estimator.covariance_, dtype=float)
            shrinkage_alpha = float(getattr(estimator, "shrinkage_", 0.0))
            if not np.isfinite(cov).all():
                raise RuntimeError("non-finite shrinkage covariance")
        except Exception:
            estimator_name = "shrunk_empirical"
            empirical = np.cov(centered, rowvar=False)
            if empirical.ndim == 0:
                empirical = np.array([[float(empirical)]], dtype=float)
            target_scale = float(np.trace(empirical) / max(1, empirical.shape[0]))
            shrinkage_alpha = 0.10
            cov = ((1.0 - shrinkage_alpha) * empirical) + (
                shrinkage_alpha * target_scale * np.eye(empirical.shape[0])
            )

        cov = self._regularize_covariance(cov)
        inv_cov = self._safe_pinv(cov)
        sign, logdet = np.linalg.slogdet(cov)
        diagnostics = {
            "covariance_estimator": estimator_name,
            "shrinkage_alpha": shrinkage_alpha,
            "condition_number": float(np.linalg.cond(cov)),
            "log_determinant": float(logdet),
            "determinant_sign": float(sign),
        }
        return mean, cov, inv_cov, diagnostics

    @staticmethod
    def _regularize_covariance(cov: np.ndarray) -> np.ndarray:
        if cov.ndim == 0:
            cov = np.array([[float(cov)]], dtype=float)
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        trace_scale = float(np.trace(cov) / max(1, cov.shape[0]))
        jitter = max(1e-8, trace_scale * 1e-8)
        return cov + np.eye(cov.shape[0]) * jitter

    @staticmethod
    def _safe_pinv(cov: np.ndarray) -> np.ndarray:
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            return np.linalg.pinv(cov)

    def _blended_covariance(self, stress_probability: float) -> np.ndarray:
        if self.calm_cov is None or self.stress_cov is None:
            return np.asarray(self.cov, dtype=float)
        pi = float(np.clip(stress_probability, 0.0, 1.0))
        cov = ((1.0 - pi) * self.calm_cov) + (pi * self.stress_cov)
        return self._regularize_covariance(cov)

    def _macro_derivative_diagnostics(self, x: np.ndarray, cov: np.ndarray) -> dict[str, object]:
        if not self.feature_names or self.mean is None:
            return {"distribution": "student_t", "dimension": 0}

        idx = [
            i
            for i, name in enumerate(self.feature_names)
            if str(name) in self.macro_derivative_features
        ]
        if not idx:
            return {"distribution": "student_t", "dimension": 0}

        sub_cov = self._regularize_covariance(cov[np.ix_(idx, idx)])
        sub_inv = self._safe_pinv(sub_cov)
        sub_x = x[idx]
        sub_mean = self.mean[idx]
        sub_d = float(mahalanobis(sub_x, sub_mean, sub_inv))
        sub_d2 = sub_d * sub_d
        p = len(idx)
        nu = self.macro_derivative_dof
        student_penalty = -0.5 * (nu + p) * np.log1p(sub_d2 / nu)
        student_equiv_d2 = -2.0 * student_penalty
        return {
            "distribution": "student_t",
            "features": [self.feature_names[i] for i in idx],
            "dimension": int(p),
            "degrees_of_freedom": float(nu),
            "distance": sub_d,
            "distance_squared": sub_d2,
            "gaussian_distance_squared": sub_d2,
            "student_t_log_penalty": float(student_penalty),
            "student_t_equivalent_distance_squared": float(student_equiv_d2),
        }
