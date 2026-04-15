"""Eigenvalue Dispersion (ED) acceleration feature.

SRD v1.2 Section 3.1 d1: ED measures how 'crowded' the factor space is.
When a liquidity shock hits, stocks de-correlate rapidly — ED spikes because
a single dominant risk factor (e.g., 'sell everything') suddenly emerges.

The acceleration (10-day median-filtered diff) captures the *change rate*
of this crowding, making it a leading indicator vs raw ED level.

Both functions are pure — no state, no network calls.
"""

import numpy as np
import pandas as pd


def compute_ed(returns: pd.DataFrame, window: int = 60) -> pd.Series:
    """Compute rolling Eigenvalue Dispersion (ED).

    ED = max(eigenvalue) / sum(eigenvalues)

    This is the fraction of total variance explained by the first principal
    component. Values near 1.0 indicate highly co-integrated, 'crowded'
    markets. Values near 1/n indicate a fully diversified factor space.

    Args:
        returns: DataFrame of constituent daily returns. columns = tickers.
        window:  Rolling window in trading days. Default 60.

    Returns:
        pd.Series with same index as returns. First (window-1) values are NaN.
        Values in (0, 1]. NaN returned for degenerate (zero-variance) windows.
    """
    def _ed_one_window(mat: np.ndarray) -> float:
        """Compute ED for a single window matrix (shape: window × n_stocks)."""
        # Remove all-zero columns to handle degenerate inputs
        col_std = mat.std(axis=0)
        mat = mat[:, col_std > 0]
        if mat.shape[1] == 0:
            return np.nan
        cov = np.cov(mat.T)
        if cov.ndim == 0:
            # Single stock: eigenvalue trivially = variance
            return 1.0
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.maximum(eigenvalues, 0.0)  # clip numerical negatives
        total = eigenvalues.sum()
        if total == 0:
            return np.nan
        return float(eigenvalues.max() / total)

    values = returns.values  # (T, n_stocks)
    n = len(returns)
    ed_vals = np.full(n, np.nan)

    for i in range(window - 1, n):
        window_data = values[i - window + 1 : i + 1]
        ed_vals[i] = _ed_one_window(window_data)

    return pd.Series(ed_vals, index=returns.index, name="ED")


def compute_ed_accel(ed_series: pd.Series, median_window: int = 10) -> pd.Series:
    """Compute ED acceleration: 10-day rolling median, then first difference.

    SRD 3.1 d1: The median filter removes high-frequency micro-noise before
    differencing, so the acceleration signal reflects genuine structural shifts
    rather than day-to-day estimation variance.

    Args:
        ed_series:     Output of compute_ed(). pd.Series with DatetimeIndex.
        median_window: Rolling median window. Default 10.

    Returns:
        pd.Series of same length. First (median_window) values are NaN.
    """
    smoothed = ed_series.rolling(window=median_window, min_periods=median_window).median()
    accel = smoothed.diff()
    accel.name = "ED_ACCEL"
    return accel
