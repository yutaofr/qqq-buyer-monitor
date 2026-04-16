"""Tests for Fisher-transformed rolling correlation (Story 2.3 / T2.3.2).

SRD v1.2 Section 3.1 d3: Fisher(rho) feature.
"""

import numpy as np
import pandas as pd

from src.liquidity.signal.fisher_rho import compute_fisher_rho


def make_series(values, start="2010-01-04") -> pd.Series:
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(np.array(values, dtype=float), index=idx)


class TestComputeFisherRho:

    def test_output_is_series(self):
        a = make_series(np.linspace(0, 1, 100))
        b = make_series(np.linspace(0, 1, 100))
        out = compute_fisher_rho(a, b, window=20)
        assert isinstance(out, pd.Series)

    def test_output_index_matches_input(self):
        a = make_series(np.linspace(0, 1, 100))
        b = make_series(np.linspace(0, 1, 100))
        out = compute_fisher_rho(a, b, window=20)
        assert out.index.equals(a.index)

    def test_perfect_positive_correlation_finite(self):
        """a == b → rho ≈ 1.0 → clip to 0.9999 → Fisher large but finite."""
        vals = np.linspace(1.0, 2.0, 100)
        a = make_series(vals)
        b = make_series(vals)
        out = compute_fisher_rho(a, b, window=20)
        valid = out.dropna()
        assert np.all(np.isfinite(valid.values)), (
            "Perfect correlation must yield finite Fisher (clip guard needed)"
        )
        assert (valid > 0).all(), "Positive correlation → positive Fisher"

    def test_perfect_negative_correlation_finite(self):
        """a = -b → rho ≈ -1.0 → clip to -0.9999 → large negative but finite."""
        vals = np.linspace(1.0, 2.0, 100)
        a = make_series(vals)
        b = make_series(-vals)
        out = compute_fisher_rho(a, b, window=20)
        valid = out.dropna()
        assert np.all(np.isfinite(valid.values))
        assert (valid < 0).all()

    def test_near_zero_correlation(self):
        """Independent oscillating series → Fisher ≈ 0."""
        n = 200
        # Alternating ±1 (orthogonal to linear trend)
        a_vals = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(n)])
        b_vals = np.array([1.0 if i % 3 == 0 else -1.0 for i in range(n)])
        a = make_series(a_vals)
        b = make_series(b_vals)
        out = compute_fisher_rho(a, b, window=20)
        valid = out.dropna()
        # Not asserting exact zero — just finiteness and reasonable range
        assert np.all(np.isfinite(valid.values))
        assert (valid.abs() < 4.0).all(), "Weakly correlated series: |Fisher| < 4"

    def test_no_changepoint_parameter(self):
        """Function signature must not accept a 'changepoint' parameter (SRD 3.5)."""
        import inspect
        sig = inspect.signature(compute_fisher_rho)
        param_names = list(sig.parameters.keys())
        assert "changepoint" not in param_names
        assert "reset" not in param_names

    def test_all_finite_after_warmup(self):
        """No NaN or inf after warm-up window."""
        vals = np.linspace(0.0, 1.0, 100)
        a = make_series(vals)
        b = make_series(vals * 0.5 + 0.1)
        out = compute_fisher_rho(a, b, window=20)
        valid = out.iloc[20:]
        assert np.all(np.isfinite(valid.values)), (
            f"Non-finite values after warmup: {valid[~np.isfinite(valid)]}"
        )

    def test_warmup_nan(self):
        """First (window-1) values must be NaN."""
        window = 20
        vals = np.linspace(0.0, 1.0, 100)
        a = make_series(vals)
        b = make_series(vals)
        out = compute_fisher_rho(a, b, window=window)
        assert out.iloc[: window - 1].isna().all()
