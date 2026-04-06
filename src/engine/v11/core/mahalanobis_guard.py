import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis


class MahalanobisGuard:
    """
    v11.7 Mahalanobis Guard
    Responsibility: Geometric Outlier Detection.
    Measures the distance of the current macro state from the historical bull-market core.
    Provides a continuous risk multiplier for the Entropy Controller.
    """

    def __init__(self):
        self.mean = None
        self.inv_cov = None
        self.is_initialized = False

    def fit_baseline(self, historical_features: pd.DataFrame):
        """
        Fits the baseline distribution (the 'Stable Core').
        Ideally fitted on periods of MID_CYCLE / RECOVERY.
        """
        if historical_features.empty:
            return

        frame = (
            historical_features.apply(pd.to_numeric, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .dropna(axis=0, how="any")
        )
        if frame.empty:
            return

        self.mean = frame.mean().values
        cov = frame.cov().values
        if cov.ndim == 0:
            cov = np.array([[float(cov)]], dtype=float)
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        cov = cov + np.eye(cov.shape[0]) * 1e-6
        # Use pseudo-inverse for stability in case of collinearity
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            self.inv_cov = np.linalg.pinv(cov)
        self.is_initialized = True

    def calculate_outlier_multiplier(self, current_vector: np.ndarray) -> float:
        """
        Calculates a risk multiplier based on geometric probability distance.
        Formula: exp(-D_M / K) where K is the sensitivity constant.
        No thresholds.
        """
        if not self.is_initialized:
            return 1.0

        try:
            d_m = mahalanobis(current_vector, self.mean, self.inv_cov)

            # Global Mean is ~2.3. 2022 is ~3.6. 2020 is ~7.2.
            # We want the multiplier to be ~1.0 at d_m=2.3
            # And start decaying smoothly after that.
            # No hard IF.
            # Multiplier = 1 / (1 + max(0, d_m - 2.0)^p)
            # Using exponential decay for 'probabilistic discomfort'.
            excess_distance = max(0.0, d_m - 2.3)
            multiplier = np.exp(-0.15 * excess_distance)

            return float(np.clip(multiplier, 0.5, 1.0))
        except Exception:
            return 1.0

    def is_outlier(self, current_vector: np.ndarray, threshold: float = 4.0, return_distance: bool = False) -> bool | tuple[bool, float]:
        """
        Binary trigger for out-of-distribution (OOD) events.
        Default threshold of 4.0 captures extreme regimes (e.g., 2020 was 7.2).
        """
        if not self.is_initialized:
            return (False, 0.0) if return_distance else False

        try:
            d_m = float(mahalanobis(current_vector, self.mean, self.inv_cov))
            is_ood = bool(d_m > threshold)
            return (is_ood, d_m) if return_distance else is_ood
        except Exception:
            return (False, 0.0) if return_distance else False
