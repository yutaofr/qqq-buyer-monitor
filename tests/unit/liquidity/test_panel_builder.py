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


def _make_constituent_diag(start: str, end: str, top_n: int) -> dict:
    idx = pd.bdate_range(start, end)
    valid = pd.Series(top_n, index=idx, name="ED_VALID_NAMES", dtype=int)
    return {
        "requested_tickers": [f"STOCK_{i}" for i in range(top_n)],
        "loaded_tickers": [f"STOCK_{i}" for i in range(top_n)],
        "failed_tickers": [],
        "available_names": pd.Series(top_n, index=idx, name="AVAILABLE_NAMES", dtype=int),
        "valid_names": valid,
    }


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
            side_effect=lambda tickers, s, e, **kwargs: _make_ohlc(
                tickers, "2006-01-01", e
            ),
        ),
        patch(
            "src.liquidity.data.panel_builder.load_constituent_returns_with_diagnostics",
            side_effect=lambda s, e, **kwargs: (
                _make_constituent_rets("2006-01-01", e, kwargs.get("top_n", 50)),
                _make_constituent_diag("2006-01-01", e, kwargs.get("top_n", 50)),
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
                     "FISHER_RHO", "LAMBDA_MACRO", "ED_VALID_NAMES",
                     "ED_IS_DEGRADED", "FISHER_IS_DEGRADED"}
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

    def test_degraded_flags_are_boolean(self):
        assert self.panel["ED_IS_DEGRADED"].dtype == bool
        assert self.panel["FISHER_IS_DEGRADED"].dtype == bool


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


class TestDynamicUniverseParameters:
    def test_panel_builder_uses_proxy_universe_and_ed_filters(self, _mock_all_io):
        from src.liquidity.data.panel_builder import build_pit_aligned_panel

        with (
            patch(
                "src.liquidity.data.panel_builder.load_ohlc",
                return_value=_make_ohlc(["QQQ", "QLD", "TLT"], "2006-01-01", "2010-06-30"),
            ) as ohlc_mock,
            patch(
                "src.liquidity.data.panel_builder.load_constituent_returns_with_diagnostics",
                return_value=(
                    _make_constituent_rets("2006-01-01", "2010-06-30", 50),
                    _make_constituent_diag("2006-01-01", "2010-06-30", 50),
                ),
            ) as load_mock,
            patch(
                "src.liquidity.data.panel_builder.compute_ed",
                return_value=pd.Series(
                    np.linspace(0.4, 0.8, len(pd.bdate_range("2003-01-01", "2010-12-31"))),
                    index=pd.bdate_range("2003-01-01", "2010-12-31"),
                    name="ED",
                ),
            ) as ed_mock,
        ):
            build_pit_aligned_panel("2009-01-02", "2010-06-30")

        _, ohlc_kwargs = ohlc_mock.call_args
        assert ohlc_kwargs["chunk_size"] == 5
        assert ohlc_kwargs["max_retries"] == 3
        assert ohlc_kwargs["base_delay_seconds"] == 1.0
        assert ohlc_kwargs["jitter_seconds"] == 0.25

        _, load_kwargs = load_mock.call_args
        assert load_kwargs["top_n"] == 50
        assert load_kwargs["min_listing_days"] == 63
        assert load_kwargs["liquidity_lookback"] == 60
        assert load_kwargs["chunk_size"] == 5
        assert load_kwargs["max_retries"] == 3
        assert load_kwargs["base_delay_seconds"] == 1.0
        assert load_kwargs["jitter_seconds"] == 0.25

        _, ed_kwargs = ed_mock.call_args
        assert ed_kwargs["window"] == 60
        assert ed_kwargs["min_coverage"] == 0.9
        assert ed_kwargs["min_names"] == 20

    def test_panel_builder_marks_degraded_rows_when_valid_names_too_low(self, _mock_all_io):
        from src.liquidity.data.panel_builder import build_pit_aligned_panel

        idx = pd.bdate_range("2006-01-01", "2010-06-30")
        valid_names = pd.Series(25, index=idx, name="ED_VALID_NAMES", dtype=int)
        valid_names.loc["2009-01-02":"2009-02-02"] = 10

        with patch(
            "src.liquidity.data.panel_builder.load_constituent_returns_with_diagnostics",
            return_value=(
                _make_constituent_rets("2006-01-01", "2010-06-30", 50),
                {
                    **_make_constituent_diag("2006-01-01", "2010-06-30", 50),
                    "valid_names": valid_names,
                    "failed_tickers": ["BAD1"],
                },
            ),
        ):
            panel = build_pit_aligned_panel("2009-01-02", "2010-06-30")

        assert panel["ED_IS_DEGRADED"].any()
        assert panel["FISHER_IS_DEGRADED"].any()
        assert panel.attrs["constituent_loader"]["failed_tickers"] == ["BAD1"]
