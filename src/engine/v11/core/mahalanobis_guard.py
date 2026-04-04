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

        # We compute the core distribution of the features
        self.mean = historical_features.mean().values
        cov = historical_features.cov().values
        # Use pseudo-inverse for stability in case of collinearity
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
