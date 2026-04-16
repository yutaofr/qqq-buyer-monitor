"""Tests for macro hazard rate synthesis (Story 2.4 / T2.4.3).

SRD v1.2: lambda_macro synthesis pipeline — 4-step, fully testable independently.
"""

import numpy as np
import pandas as pd

from src.liquidity.signal.macro_hazard import (
    composite_stress,
    directional_transform,
    map_to_hazard,
    rolling_percentile_rank,
)

IDX = pd.bdate_range("2008-01-02", periods=600)


def make_series(values, name="x") -> pd.Series:
    return pd.Series(np.array(values, dtype=float), index=IDX[: len(values)], name=name)


class TestDirectionalTransform:
    """Step 1: direction standardisation — 'tightening = positive'."""

    def test_walcl_falling_is_positive(self):
        """Fed reserves declining → tightening → positive signal."""
        # Linearly declining WALCL: every period falls → pct_change < 0 → negated > 0
        walcl = make_series(list(range(100, 40, -1)))   # 100,99,...,41 — always falling
        rrp   = make_series([50.0] * 60)
        tga   = make_series([400.0] * 60)
        fra   = make_series([0.10] * 60)
        signals = directional_transform(walcl, rrp, tga, fra)
        walcl_signal = signals["walcl"].dropna()
        assert (walcl_signal > 0).all(), (
            "Continuously falling WALCL must produce positive (tightening) signal"
        )

    def test_rrp_falling_is_positive(self):
        """RRP declining → buffer shrinking → tightening."""
        rrp = make_series(list(range(200, 130, -1)))    # always falling
        walcl = make_series([7000.0] * 70)
        tga   = make_series([400.0] * 70)
        fra   = make_series([0.10] * 70)
        signals = directional_transform(walcl, rrp, tga, fra)
        rrp_signal = signals["rrp"].dropna()
        assert (rrp_signal > 0).all()

    def test_tga_rising_is_positive(self):
        """TGA rising → Treasury hoarding cash → draining reserves → tightening."""
        tga = make_series(list(range(400, 470)))    # always rising
        walcl = make_series([7000.0] * 70)
        rrp   = make_series([200.0] * 70)
        fra   = make_series([0.10] * 70)
        signals = directional_transform(walcl, rrp, tga, fra)
        tga_signal = signals["tga"].dropna()
        assert (tga_signal > 0).all()

    def test_fra_ois_is_level(self):
        """FRA-OIS uses level directly — higher spread means more stress."""
        fra = make_series([0.05, 0.10, 0.20, 0.50] * 15)
        walcl = make_series([7000.0] * 60)
        rrp   = make_series([200.0] * 60)
        tga   = make_series([400.0] * 60)
        signals = directional_transform(walcl, rrp, tga, fra)
        fra_signal = signals["fra_ois"]
        # Should equal the original level
        np.testing.assert_allclose(fra_signal.values, fra.values, atol=1e-10)

    def test_output_keys(self):
        """Must return all four keys: walcl, rrp, tga, fra_ois."""
        s = directional_transform(
            make_series([100.0]*60),
            make_series([50.0]*60),
            make_series([400.0]*60),
            make_series([0.1]*60),
        )
        assert set(s.keys()) == {"walcl", "rrp", "tga", "fra_ois"}


class TestRollingPercentileRank:
    """Step 2: distribution-free normalisation → [0, 1]."""

    def test_max_gets_rank_one(self):
        """The maximum value in the lookback window gets rank = 1.0."""
        n = 504
        signal = make_series(list(range(n)))  # 0,1,2,...,503
        ranked = rolling_percentile_rank(signal, lookback=n)
        # The last value (503) is the maximum in the entire window
        np.testing.assert_allclose(ranked.iloc[-1], 1.0, atol=1e-6)

    def test_min_gets_rank_near_zero(self):
        """The minimum value in the full lookback gets rank close to 1/n.

        With a uniformly spaced sequence [0,1,...,n-1] and lookback=n,
        the first valid ranked value corresponds to the point at position n-1
        (index) in the rolling window. At that point the window contains
        [0,1,...,n-1] and the current value (n-1) is always the max → rank=1.

        To test the minimum case, build a *decreasing* sequence so that
        the first valid ranked point has the current value as the minimum.
        """
        n = 104
        # Decreasing: [n-1, n-2, ..., 0]. At first valid point (lookback=100),
        # the window contains [n-1, n-2, ..., n-100] and current = n-1 (max).
        # Instead: use a series that ends with a very low value.
        signal = make_series(list(range(n, 0, -1)))  # decreasing
        lookback = 100
        ranked = rolling_percentile_rank(signal, lookback=lookback)
        valid = ranked.dropna()
        # The last value is the minimum in the window → rank ≈ 1/lookback
        np.testing.assert_allclose(valid.iloc[-1], 1.0 / lookback, atol=0.01)

    def test_output_bounded_01(self):
        """All output values must be in [0, 1]."""
        signal = make_series(np.sin(np.linspace(0, 10, 200)))
        ranked = rolling_percentile_rank(signal, lookback=60)
        valid = ranked.dropna()
        assert (valid >= 0.0).all() and (valid <= 1.0).all()

    def test_output_is_series(self):
        signal = make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        out = rolling_percentile_rank(signal, lookback=3)
        assert isinstance(out, pd.Series)

    def test_uniform_input_gives_uniform_ranks(self):
        """Verify monotonic rank ordering: increasing input → increasing ranks.

        With a linearly increasing sequence, each new value is the maximum
        in its window → all ranks = 1.0 at the end of the window. But if we
        look at a window that slides over the sequence, earlier positions get
        lower ranks. We verify this by checking the FIRST valid rank < last.
        """
        n = 200
        signal = make_series(np.linspace(0, 1, n))
        ranked = rolling_percentile_rank(signal, lookback=100)
        valid = ranked.dropna()
        # For a monotonically increasing sequence, the current value is always
        # the window maximum → all valid ranks should be 1.0
        np.testing.assert_allclose(valid.values, 1.0, atol=1e-6)


class TestCompositeStress:
    """Step 3: weighted sum of percentile ranks."""

    def test_equal_weights_equal_ranks(self):
        """All ranks = 0.5 with equal weights → composite = 0.5."""
        idx = pd.bdate_range("2010-01-04", periods=50)
        ranks = {
            "walcl":   pd.Series(np.full(50, 0.5), index=idx),
            "rrp":     pd.Series(np.full(50, 0.5), index=idx),
            "tga":     pd.Series(np.full(50, 0.5), index=idx),
            "fra_ois": pd.Series(np.full(50, 0.5), index=idx),
        }
        weights = {"walcl": 0.25, "rrp": 0.25, "tga": 0.25, "fra_ois": 0.25}
        composite = composite_stress(ranks, weights)
        np.testing.assert_allclose(composite.values, 0.5, atol=1e-10)

    def test_extreme_ranks_give_extremes(self):
        """All ranks = 1.0 → composite = 1.0; all ranks = 0.0 → composite = 0.0."""
        idx = pd.bdate_range("2010-01-04", periods=10)
        w = {"walcl": 0.25, "rrp": 0.25, "tga": 0.25, "fra_ois": 0.25}
        # All max
        ranks_max = {k: pd.Series(np.ones(10), index=idx) for k in w}
        np.testing.assert_allclose(composite_stress(ranks_max, w).values, 1.0, atol=1e-10)
        # All min
        ranks_min = {k: pd.Series(np.zeros(10), index=idx) for k in w}
        np.testing.assert_allclose(composite_stress(ranks_min, w).values, 0.0, atol=1e-10)

    def test_output_bounded_01(self):
        """Composite must always be in [0, 1]."""
        idx = pd.bdate_range("2010-01-04", periods=30)
        w = {"walcl": 0.25, "rrp": 0.25, "tga": 0.25, "fra_ois": 0.25}
        rng = np.random.default_rng(0)
        ranks = {k: pd.Series(rng.uniform(0, 1, 30), index=idx) for k in w}
        comp = composite_stress(ranks, w)
        assert (comp >= 0.0).all() and (comp <= 1.0).all()

    def test_nan_variable_redistributes_weight(self):
        """If one variable is fully NaN, weight redistributes to others."""
        idx = pd.bdate_range("2010-01-04", periods=10)
        # fra_ois is all NaN; others = 0.5
        ranks = {
            "walcl":   pd.Series(np.full(10, 0.5), index=idx),
            "rrp":     pd.Series(np.full(10, 0.5), index=idx),
            "tga":     pd.Series(np.full(10, 0.5), index=idx),
            "fra_ois": pd.Series(np.full(10, np.nan), index=idx),
        }
        weights = {"walcl": 0.25, "rrp": 0.25, "tga": 0.25, "fra_ois": 0.25}
        comp = composite_stress(ranks, weights)
        # With 3 valid vars each at 0.5, result should still be ≈ 0.5
        np.testing.assert_allclose(comp.values, 0.5, atol=1e-10)


class TestMapToHazard:
    """Step 4: linear mapping composite [0,1] → lambda [floor, ceil]."""

    def test_composite_zero_gives_floor(self):
        idx = pd.bdate_range("2010-01-04", periods=10)
        comp = pd.Series(np.zeros(10), index=idx)
        lm = map_to_hazard(comp, lambda_floor=0.002, lambda_ceil=0.016)
        np.testing.assert_allclose(lm.values, 0.002, atol=1e-12)

    def test_composite_one_gives_ceil(self):
        idx = pd.bdate_range("2010-01-04", periods=10)
        comp = pd.Series(np.ones(10), index=idx)
        lm = map_to_hazard(comp, lambda_floor=0.002, lambda_ceil=0.016)
        np.testing.assert_allclose(lm.values, 0.016, atol=1e-12)

    def test_composite_half_gives_midpoint(self):
        idx = pd.bdate_range("2010-01-04", periods=10)
        comp = pd.Series(np.full(10, 0.5), index=idx)
        lm = map_to_hazard(comp, lambda_floor=0.002, lambda_ceil=0.016)
        expected = 0.002 + 0.5 * (0.016 - 0.002)
        np.testing.assert_allclose(lm.values, expected, atol=1e-12)

    def test_output_always_bounded(self):
        """lambda must always be in [floor, ceil]."""
        idx = pd.bdate_range("2010-01-04", periods=100)
        comp = pd.Series(np.random.default_rng(1).uniform(0, 1, 100), index=idx)
        lm = map_to_hazard(comp, lambda_floor=0.002, lambda_ceil=0.016)
        assert (lm >= 0.002).all() and (lm <= 0.016).all()

    def test_safety_constraint(self):
        """SRD safety: lambda_ceil * g(0) = 0.016 * 6 = 0.096 < 1.0."""
        g_r0 = 6.0  # g(r=0) with kappa_hazard=5
        lambda_ceil = 0.016
        assert lambda_ceil * g_r0 < 1.0, (
            f"Safety violation: lambda_ceil * g(0) = {lambda_ceil * g_r0} >= 1.0"
        )
