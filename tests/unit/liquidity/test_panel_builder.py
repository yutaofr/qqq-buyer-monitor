"""Tests for PiT-aligned panel builder (P1-3).

Uses unittest.mock to replace all network calls (FRED, yfinance).
Verifies the orchestration logic: padded start, per-series alignment,
signal computation on padded data, trim, and NaN gate.

NO network calls, NO API keys required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ─── Synthetic data factories ───────────────────────────────────

def _make_fred_df(series_id: str, start: str, end: str) -> pd.DataFrame:
    """Mock FRED response: business-day indexed, single value column."""
    idx = pd.bdate_range(start, end)
    return pd.DataFrame({
        "observation_date": idx,
        series_id: np.random.default_rng(42).normal(100, 5, len(idx)),
    })


def _make_ohlc(tickers: list[str], start: str, end: str) -> dict:
    """Mock yfinance OHLC: each ticker gets a DataFrame with ticker_Close."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    result = {}
    for t in tickers:
        base = 100 + rng.normal(0, 1, len(idx)).cumsum()
        result[t] = pd.DataFrame(
            {f"{t}_Close": base, f"{t}_Open": base * 0.999}, index=idx
        )
    return result


def _make_constituent_rets(start: str, end: str, top_n: int) -> pd.DataFrame:
    """Mock constituent returns: top_n columns, bday indexed."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        rng.normal(0, 0.01, (len(idx), top_n)),
        index=idx,
        columns=[f"STOCK_{i}" for i in range(top_n)],
    )


def _make_trading_calendar(start: str, end: str) -> pd.DatetimeIndex:
    """Mock trading calendar: simple bday range."""
    return pd.bdate_range(start, end)


# ─── Fixtures ───────────────────────────────────────────────────

@pytest.fixture()
def _mock_all_io():
    """Patch all network I/O in panel_builder."""
    # We need to supply data from well before the padded start
    data_start = "2003-01-01"
    data_end   = "2010-12-31"

    with (
        patch(
            "src.liquidity.data.panel_builder.build_trading_calendar",
            return_value=_make_trading_calendar(data_start, data_end),
        ),
        patch(
            "src.liquidity.data.panel_builder.compute_padded_start",
            return_value=pd.Timestamp("2007-01-02"),
        ),
        patch(
            "src.liquidity.data.panel_builder.load_fred_series",
            side_effect=lambda sid, s, e: _make_fred_df(sid, "2006-01-01", e),
        ),
        patch(
            "src.liquidity.data.panel_builder.load_ohlc",
            side_effect=lambda tickers, s, e: _make_ohlc(tickers, "2006-01-01", e),
        ),
        patch(
            "src.liquidity.data.panel_builder.load_constituent_returns",
            side_effect=lambda s, e: _make_constituent_rets(
                "2006-01-01", e, 50
            ),
        ),
    ):
        yield


# ─── Tests ──────────────────────────────────────────────────────

class TestBuildPanelStructure:
    """Structural checks on the output panel."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_all_io):
        from src.liquidity.data.panel_builder import build_pit_aligned_panel
        self.panel = build_pit_aligned_panel("2009-01-02", "2010-06-30")

    def test_returns_dataframe(self):
        assert isinstance(self.panel, pd.DataFrame)

    def test_has_required_columns(self):
        required = {"QQQ_ret", "QLD_ret", "ED_ACCEL", "SPREAD_ANOMALY",
                     "FISHER_RHO", "LAMBDA_MACRO"}
        missing = required - set(self.panel.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_index_starts_on_or_after_start_date(self):
        assert self.panel.index[0] >= pd.Timestamp("2009-01-02")

    def test_index_ends_on_or_before_end_date(self):
        assert self.panel.index[-1] <= pd.Timestamp("2010-06-30")

    def test_zero_nan(self):
        """The entire panel must have zero NaN."""
        nan_count = self.panel.isna().sum().sum()
        assert nan_count == 0, (
            f"NaN found in panel: {self.panel.isna().sum().to_dict()}"
        )

    def test_index_is_datetimeindex(self):
        assert isinstance(self.panel.index, pd.DatetimeIndex)

    def test_no_weekends(self):
        weekdays = self.panel.index.dayofweek
        assert (weekdays < 5).all(), "Weekend dates found in panel index"


class TestBuildPanelValues:
    """Value-level checks on the output panel."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_all_io):
        from src.liquidity.data.panel_builder import build_pit_aligned_panel
        self.panel = build_pit_aligned_panel("2009-01-02", "2010-06-30")

    def test_qqq_ret_finite(self):
        assert np.all(np.isfinite(self.panel["QQQ_ret"].values))

    def test_qld_ret_finite(self):
        assert np.all(np.isfinite(self.panel["QLD_ret"].values))

    def test_lambda_macro_in_range(self):
        """λ_macro must be in [lambda_floor, lambda_ceil]."""
        from src.liquidity.config import load_config
        cfg = load_config()
        lm = self.panel["LAMBDA_MACRO"]
        floor = cfg["macro_hazard"]["lambda_floor"]
        ceil  = cfg["macro_hazard"]["lambda_ceil"]
        # Allow small tolerance for NaN fallback filling
        assert (lm >= floor - 1e-10).all(), f"Below floor: min={lm.min()}"
        assert (lm <= ceil + 1e-10).all(), f"Above ceil: max={lm.max()}"

    def test_spread_anomaly_finite(self):
        assert np.all(np.isfinite(self.panel["SPREAD_ANOMALY"].values))

    def test_ed_accel_finite(self):
        assert np.all(np.isfinite(self.panel["ED_ACCEL"].values))


class TestPaddingMechanism:
    """Verify that padding protects the formal backtest interval."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_all_io):
        pass

    def test_panel_starts_exactly_at_start_date(self, _mock_all_io):
        """Output panel must NOT include padded data before start_date."""
        from src.liquidity.data.panel_builder import build_pit_aligned_panel
        panel = build_pit_aligned_panel("2009-01-02", "2010-06-30")
        # First date must be >= start_date
        assert panel.index[0] >= pd.Timestamp("2009-01-02")

    def test_padded_panel_is_longer_than_output(self, _mock_all_io):
        """Internal padded panel should be longer than trimmed output.
        We verify this indirectly: if start=2009 and lookback=504 TDs,
        padded_start should be around 2007-01-02.
        """
        from src.liquidity.data.panel_builder import build_pit_aligned_panel
        panel = build_pit_aligned_panel("2009-01-02", "2010-06-30")
        # Panel should span ~1.5 years of trading days
        expected_min_rows = 250  # ~1 year minimum
        assert len(panel) > expected_min_rows
