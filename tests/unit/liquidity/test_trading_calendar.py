"""Tests for trading calendar module (Story 3.2 / T3.2.2).

All tests use mocked yfinance — no network calls.
The trading calendar is the source of truth for the Lookback Padding architecture.
"""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.liquidity.data.trading_calendar import (
    MAX_LOOKBACK,
    CALENDAR_BUFFER,
    build_trading_calendar,
    compute_padded_start,
)


def _make_mock_hist(start: str, end: str) -> pd.DataFrame:
    """Build a synthetic QQQ history DataFrame with a trading-day index."""
    idx = pd.bdate_range(start, end)
    return pd.DataFrame({"Close": [1.0] * len(idx)}, index=idx)


class TestConstants:
    def test_max_lookback_is_504(self):
        assert MAX_LOOKBACK == 504

    def test_calendar_buffer_gte_730(self):
        """800 cal days > 730 (≈ 504 trading days). Must have safety margin."""
        assert CALENDAR_BUFFER >= 730


class TestBuildTradingCalendar:
    """build_trading_calendar returns a DatetimeIndex from yfinance QQQ data."""

    def _patch_yf(self, mock_hist: pd.DataFrame):
        """Context manager: patch yfinance.download to return synthetic data."""
        m = MagicMock()
        m.return_value = mock_hist
        return patch("src.liquidity.data.trading_calendar.yf.download", m)

    def test_returns_datetimeindex(self):
        hist = _make_mock_hist("2009-01-01", "2011-12-31")
        with self._patch_yf(hist):
            cal = build_trading_calendar("2011-01-03", "2011-12-30")
        assert isinstance(cal, pd.DatetimeIndex)

    def test_index_contains_start_date(self):
        hist = _make_mock_hist("2009-01-01", "2011-12-31")
        with self._patch_yf(hist):
            cal = build_trading_calendar("2011-01-03", "2011-12-30")
        assert pd.Timestamp("2011-01-03") in cal

    def test_no_weekends_in_calendar(self):
        hist = _make_mock_hist("2009-01-01", "2011-12-31")
        with self._patch_yf(hist):
            cal = build_trading_calendar("2011-01-03", "2011-12-30")
        day_of_week = cal.dayofweek
        assert (day_of_week < 5).all(), "Trading calendar must contain no weekends"

    def test_raises_on_empty_response(self):
        """Empty yfinance response → RuntimeError (not silent NaN propagation)."""
        with patch(
            "src.liquidity.data.trading_calendar.yf.download",
            return_value=pd.DataFrame(),
        ):
            with pytest.raises(RuntimeError, match="No price data"):
                build_trading_calendar("2011-01-03", "2011-12-30")


class TestComputePaddedStart:
    """compute_padded_start: exact lookback in trading-day space."""

    @pytest.fixture()
    def long_calendar(self) -> pd.DatetimeIndex:
        """4 years of bdate range — enough for all lookback tests."""
        return pd.bdate_range("2005-01-03", "2009-12-31")

    def test_returns_timestamp(self, long_calendar):
        result = compute_padded_start(long_calendar, "2008-01-02")
        assert isinstance(result, pd.Timestamp)

    def test_exact_trading_day_count(self, long_calendar):
        """padded_start must be exactly MAX_LOOKBACK trading days before target."""
        target = "2008-01-02"
        padded = compute_padded_start(long_calendar, target)

        # Count trading days between padded_start and target (inclusive of target)
        count = long_calendar[
            (long_calendar >= padded) & (long_calendar <= target)
        ]
        # Should be MAX_LOOKBACK + 1 (padded_start through target inclusive)
        assert len(count) == MAX_LOOKBACK + 1, (
            f"Expected {MAX_LOOKBACK + 1} trading days from padded_start to target, "
            f"got {len(count)}. padded_start={padded}, target={target}"
        )

    def test_padded_start_is_trading_day(self, long_calendar):
        """padded_start must itself be a valid trading day (in the calendar)."""
        padded = compute_padded_start(long_calendar, "2008-01-02")
        assert padded in long_calendar

    def test_custom_lookback(self, long_calendar):
        """Custom lookback=100 → exactly 100 trading days before target."""
        target = "2008-01-02"
        padded = compute_padded_start(long_calendar, target, lookback=100)
        count = long_calendar[
            (long_calendar >= padded) & (long_calendar <= target)
        ]
        assert len(count) == 101  # 100 days + target itself

    def test_raises_if_insufficient_history(self):
        """Short calendar (< MAX_LOOKBACK) → IndexError (not silent clamp)."""
        short_cal = pd.bdate_range("2010-01-04", periods=100)
        with pytest.raises((IndexError, ValueError)):
            compute_padded_start(short_cal, "2010-06-01")
