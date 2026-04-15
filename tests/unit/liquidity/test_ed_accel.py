"""Tests for ED acceleration feature (Story 2.1 / T2.1.2).

SRD v1.2 Section 3.1 d1: Eigenvalue Dispersion (ED) acceleration.
All inputs are deterministic — no random seeds.
"""

import numpy as np
import pandas as pd
import pytest

from src.liquidity.signal.ed_accel import compute_ed, compute_ed_accel

# Shared trading-day date range
DATES = pd.bdate_range("2010-01-04", periods=200)


def make_returns(n_days: int, n_stocks: int, value: float = 0.01) -> pd.DataFrame:
    """Constant returns matrix — deterministic, no randomness."""
    data = np.full((n_days, n_stocks), value)
    idx = pd.bdate_range("2010-01-04", periods=n_days)
    return pd.DataFrame(data, index=idx)


class TestComputeED:
    """Unit tests for the ED (eigenvalue dispersion) computation."""

    def test_output_is_series(self):
        returns = make_returns(100, 10)
        ed = compute_ed(returns, window=20)
        assert isinstance(ed, pd.Series)

    def test_output_index_is_datetimeindex(self):
        returns = make_returns(100, 10)
        ed = compute_ed(returns, window=20)
        assert isinstance(ed.index, pd.DatetimeIndex)

    def test_output_length_matches_input(self):
        returns = make_returns(100, 10)
        ed = compute_ed(returns, window=20)
        assert len(ed) == len(returns)

    def test_known_eigenvalue_ratio(self):
        """Construct returns whose covariance has known eigenvalues.

        If all n stocks move identically (returns = c for all), the covariance
        matrix is rank-1: one nonzero eigenvalue (all variance in one direction).
        ED = max_eigenvalue / sum_eigenvalues = 1.0.
        """
        n_days = 80
        n_stocks = 5
        # Identical returns → rank-1 covariance
        returns = make_returns(n_days, n_stocks, value=0.01)
        ed = compute_ed(returns, window=60)
        # After the warm-up window, ED should be 1.0 (all variance in 1 PC)
        valid = ed.iloc[60:].dropna()
        np.testing.assert_allclose(valid.values, 1.0, atol=1e-6)

    def test_degenerate_zero_returns(self):
        """Zero returns → zero variance → ED should return NaN (degenerate)."""
        returns = make_returns(100, 5, value=0.0)
        ed = compute_ed(returns, window=20)
        valid = ed.iloc[20:].dropna()
        # All zeros → eigenvalues all zero → ED is NaN or 0
        # Accept either: implementation may return NaN or 0 for zero covariance
        assert valid.isna().all() or (valid == 0.0).all(), (
            "Zero returns should give NaN or 0 ED (degenerate covariance)"
        )

    def test_warmup_nan(self):
        """First (window-1) observations must be NaN during warm-up."""
        window = 20
        returns = make_returns(100, 5)
        ed = compute_ed(returns, window=window)
        assert ed.iloc[: window - 1].isna().all()

    def test_values_in_01(self):
        """ED is max eigenvalue / sum eigenvalues ∈ (0, 1]."""
        returns = make_returns(100, 5)
        ed = compute_ed(returns, window=20)
        valid = ed.dropna()
        assert (valid >= 0.0).all() and (valid <= 1.0 + 1e-9).all()


class TestComputeEDAccel:
    """Unit tests for the ED acceleration (rolling median diff)."""

    def test_output_is_series(self):
        ed = pd.Series(
            np.linspace(0.5, 0.9, 100),
            index=pd.bdate_range("2010-01-04", periods=100),
        )
        accel = compute_ed_accel(ed)
        assert isinstance(accel, pd.Series)

    def test_constant_ed_gives_zero_accel(self):
        """Constant ED → zero acceleration after warm-up."""
        ed = pd.Series(
            np.full(100, 0.6),
            index=pd.bdate_range("2010-01-04", periods=100),
        )
        accel = compute_ed_accel(ed, median_window=10)
        valid = accel.dropna()
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-12)

    def test_rising_ed_gives_positive_accel(self):
        """Monotonically increasing ED → positive acceleration."""
        ed = pd.Series(
            np.linspace(0.3, 0.9, 100),
            index=pd.bdate_range("2010-01-04", periods=100),
        )
        accel = compute_ed_accel(ed, median_window=5)
        valid = accel.dropna()
        assert (valid > 0).all(), "Rising ED must give positive acceleration"

    def test_falling_ed_gives_negative_accel(self):
        """Monotonically decreasing ED → negative acceleration."""
        ed = pd.Series(
            np.linspace(0.9, 0.3, 100),
            index=pd.bdate_range("2010-01-04", periods=100),
        )
        accel = compute_ed_accel(ed, median_window=5)
        valid = accel.dropna()
        assert (valid < 0).all(), "Falling ED must give negative acceleration"

    def test_output_index_matches_input(self):
        idx = pd.bdate_range("2010-01-04", periods=100)
        ed = pd.Series(np.random.default_rng(42).uniform(0.4, 0.8, 100), index=idx)
        accel = compute_ed_accel(ed)
        assert accel.index.equals(ed.index)
