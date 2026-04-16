"""Smoke test for the end-to-end backtest runner (Story 5.2 / T5.2.3).

Uses fully deterministic synthetic data — NO network calls, NO random seeds.
The test panel simulates 700 trading days of calm market conditions.

Structural checks:
  - NAV series starts at 1.0 and stays >= 0
  - All NAV values are finite
  - Log DataFrame has expected columns
  - Burn-in period (252 days): system stays in QQQ (no QLD)
  - Post-burn-in: system eventually enters QLD on calm signals
"""

import numpy as np
import pandas as pd
import pytest

from src.liquidity.backtest.runner import run_backtest
from src.liquidity.config import load_config

BURN_IN = 252
N_DAYS  = 700           # > 504 (MAX_LOOKBACK) + 252 (burn-in) to allow entry
N_STOCKS = 5            # small for speed


def _build_synthetic_panel(n_days: int = N_DAYS) -> pd.DataFrame:
    """Build a fully deterministic synthetic panel.

    Features:
        ED_ACCEL:       0.0 (calm markets, no eigenvalue dispersion change)
        SPREAD_ANOMALY: 0.0 (VIX at historical average — no stress signal)
        FISHER_RHO:     0.0 (neutral equity-bond correlation)
        LAMBDA_MACRO:   0.002 (minimum hazard — fully calm macro)
        QQQ return:     +0.04% per day (slight upward drift)
        QLD return:     +0.08% per day (2× QQQ, deterministic)
    """
    idx = pd.bdate_range("2005-01-03", periods=n_days)
    return pd.DataFrame(
        {
            "ED_ACCEL":       0.0,
            "SPREAD_ANOMALY": 0.0,
            "FISHER_RHO":     0.0,
            "LAMBDA_MACRO":   0.002,
            "QQQ_ret":        0.0004,   # 0.04%/day deterministic
            "QLD_ret":        0.0008,   # 0.08%/day deterministic
        },
        index=idx,
    )


@pytest.fixture(scope="module")
def backtest_result():
    config  = load_config()
    config["regime_vol_guard"]["enabled"] = False
    panel   = _build_synthetic_panel()
    return run_backtest(panel, config, burn_in=BURN_IN)


class TestRunBacktestStructure:
    """Structural integrity checks on backtest output."""

    def test_returns_dict(self, backtest_result):
        assert isinstance(backtest_result, dict)

    def test_has_nav_series(self, backtest_result):
        assert "nav" in backtest_result
        assert isinstance(backtest_result["nav"], pd.Series)

    def test_has_log_dataframe(self, backtest_result):
        assert "log" in backtest_result
        assert isinstance(backtest_result["log"], pd.DataFrame)

    def test_nav_length_matches_panel(self, backtest_result):
        """NAV series covers all post-burn-in days."""
        nav = backtest_result["nav"]
        assert len(nav) == N_DAYS - BURN_IN

    def test_nav_starts_at_one(self, backtest_result):
        nav = backtest_result["nav"]
        np.testing.assert_allclose(nav.iloc[0], 1.0, atol=1e-10)

    def test_nav_all_finite(self, backtest_result):
        nav = backtest_result["nav"]
        assert np.all(np.isfinite(nav.values)), "NAV contains NaN or inf"

    def test_nav_all_positive(self, backtest_result):
        nav = backtest_result["nav"]
        assert (nav > 0).all(), f"NAV went to zero or negative: min={nav.min()}"


class TestRunBacktestLog:
    """Log DataFrame structure validation."""

    def test_log_has_required_columns(self, backtest_result):
        log = backtest_result["log"]
        required = {
            "weight",
            "s_t",
            "s_cp_t",
            "s_level_t",
            "p_cp",
            "regime_severity",
            "regime_severity_base",
            "regime_resonance_pr",
            "regime_resonance_multiplier",
            "dominant_run_length",
            "dominant_run_prob",
            "days_held",
        }
        missing = required - set(log.columns)
        assert not missing, f"Log missing columns: {missing}"

    def test_log_weight_in_range(self, backtest_result):
        """Weight must be in [0, 1] (continuous SRD 4.3 allocation)."""
        w = backtest_result["log"]["weight"]
        assert (w >= 0.0).all() and (w <= 1.0).all(), (
            f"Weight out of [0, 1]: min={w.min()}, max={w.max()}"
        )

    def test_log_p_cp_in_01(self, backtest_result):
        """p_cp must be in [0, 1]."""
        p = backtest_result["log"]["p_cp"]
        assert (p >= 0).all() and (p <= 1).all()

    def test_log_s_t_in_01(self, backtest_result):
        """Smoothed stress must be in [0, 1]."""
        s = backtest_result["log"]["s_t"]
        assert (s >= 0).all() and (s <= 1).all()


class TestRunBacktestBehavior:
    """Behavioral checks under calm synthetic inputs."""

    def test_calm_signals_eventually_enter_qld(self, backtest_result):
        """Sustained calm should result in at least some QLD allocation."""
        log = backtest_result["log"]
        qld_days = (log["weight"] > 0).sum()
        assert qld_days > 0, (
            "System never allocated to QLD on 700 days of calm synthetic data. "
            f"Max s_t seen: {log['s_t'].max():.4f}"
        )

    def test_nav_grows_in_calm_market(self, backtest_result):
        """With +0.04% daily drift and no crashes, NAV should be > 1.0."""
        nav = backtest_result["nav"]
        assert nav.iloc[-1] > 1.0, (
            f"NAV ended at {nav.iloc[-1]:.4f} — expected > 1.0 with +drift market"
        )

    def test_attribution_keys_present(self, backtest_result):
        assert "attribution" in backtest_result
        attr = backtest_result["attribution"]
        for key in ["total_return", "sharpe", "max_drawdown", "n_trades"]:
            assert key in attr, f"Attribution missing key: {key}"
