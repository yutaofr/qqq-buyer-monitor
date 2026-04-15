"""Tests for spread anomaly Z-score feature (Story 2.2 / T2.2.2).

SRD v1.2 Section 3.1 d2: buy-sell spread anomaly (VIX proxy).
"""

import numpy as np
import pandas as pd
import pytest

from src.liquidity.signal.spread_anomaly import compute_spread_anomaly


def make_vix(values: list[float]) -> pd.Series:
    idx = pd.bdate_range("2005-01-03", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


class TestComputeSpreadAnomaly:

    def test_output_is_series(self):
        vix = make_vix([20.0] * 300)
        z = compute_spread_anomaly(vix, lookback=252)
        assert isinstance(z, pd.Series)

    def test_output_index_matches_input(self):
        vix = make_vix([20.0] * 300)
        z = compute_spread_anomaly(vix, lookback=252)
        assert z.index.equals(vix.index)

    def test_constant_series_gives_zero(self):
        """Constant VIX → Z = 0 everywhere (mean = value, std = 0+eps)."""
        vix = make_vix([20.0] * 300)
        z = compute_spread_anomaly(vix, lookback=252)
        valid = z.dropna()
        # std≈0 → Z≈0 (implementation must guard against division by zero)
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-6)

    def test_spike_gives_positive_z(self):
        """Large upward spike in VIX → highly positive Z-score."""
        normal = [15.0] * 300
        spike = normal + [80.0]  # massive spike
        vix = make_vix(spike)
        z = compute_spread_anomaly(vix, lookback=252)
        assert z.iloc[-1] > 5.0, (
            f"Spike should give Z > 5, got {z.iloc[-1]:.2f}"
        )

    def test_below_mean_gives_negative_z(self):
        """Value below rolling mean → negative Z-score."""
        high = [30.0] * 300
        low_spike = high + [10.0]
        vix = make_vix(low_spike)
        z = compute_spread_anomaly(vix, lookback=252)
        assert z.iloc[-1] < 0.0

    def test_no_nan_after_warmup(self):
        """After half-lookback warmup, no NaN in output."""
        vix = make_vix([20.0] * 400)
        lookback = 252
        z = compute_spread_anomaly(vix, lookback=lookback)
        # After min_periods warm-up, there should be no NaN
        min_p = lookback // 2
        no_nan_section = z.iloc[min_p:]
        assert not no_nan_section.isna().any(), (
            "NaN found after warmup — check min_periods setting"
        )

    def test_pure_function_no_network(self):
        """Must not raise any import or network errors."""
        vix = make_vix([20.0] * 300)
        result = compute_spread_anomaly(vix)
        assert result is not None
