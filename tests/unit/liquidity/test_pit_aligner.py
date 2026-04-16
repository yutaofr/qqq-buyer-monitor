"""Tests for PiT aligner module (Story 3.2 / T3.2.1, T3.2.4, T3.2.5).

All tests use deterministic synthetic data — no network calls.
Key behavioral contracts:
  - PiT offset: data available at T cannot be used before T+offset
  - Staircase fill: H.4.1 weekly value persists until next release
  - NaN gate: _assert_no_nan is a hard barrier, not a warning
  - Padding: trimmed panel starts exactly at start_date with zero NaN
"""

import numpy as np
import pandas as pd
import pytest

from src.liquidity.data.pit_aligner import (
    PIT_RULES,
    PiTConfig,
    _assert_no_nan,
    apply_pit_offset,
)


def _make_daily_series(start: str, end: str, value: float = 1.0) -> pd.DataFrame:
    """Synthetic FRED-style daily DataFrame with observation_date column."""
    idx = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"observation_date": idx, "VALUE": value})


def _make_weekly_series(start: str, periods: int, value: float = 100.0) -> pd.DataFrame:
    """Synthetic weekly (Thursday) series mimicking H.4.1 WALCL release cadence."""
    thursdays = pd.date_range(start, periods=periods, freq="W-THU")
    return pd.DataFrame({"observation_date": thursdays, "WALCL": value})


class TestPiTConfig:
    """PIT_RULES must cover all required series."""

    def test_required_series_present(self):
        required = {"WALCL", "RRPONTSYD", "WTREGEN", "SOFR", "VIXCLS"}
        missing = required - set(PIT_RULES.keys())
        assert not missing, f"PIT_RULES missing: {missing}"

    def test_config_has_offset_days(self):
        for key, cfg in PIT_RULES.items():
            assert "offset_days" in cfg, f"{key} missing 'offset_days' in PIT_RULES"

    def test_config_has_fill_method(self):
        for key, cfg in PIT_RULES.items():
            assert "fill_method" in cfg, f"{key} missing 'fill_method' in PIT_RULES"

    def test_sofr_offset_is_one(self):
        """SOFR T+1: published next business day."""
        assert PIT_RULES["SOFR"]["offset_days"] == 1

    def test_walcl_fill_is_staircase(self):
        """H.4.1 weekly: use staircase fill (not simple ffill)."""
        assert PIT_RULES["WALCL"]["fill_method"] == "staircase"


class TestApplyPiTOffset:
    """apply_pit_offset: shift observation dates by offset_days trading days."""

    def test_sofr_offset_1_shifts_by_one_trading_day(self):
        """SOFR (offset=1): value observed on Monday is usable on Tuesday."""
        trading_days = pd.bdate_range("2020-01-01", "2021-12-31")

        # Monday 2020-01-06 data should become available on Tuesday 2020-01-07
        raw = pd.DataFrame({
            "observation_date": [pd.Timestamp("2020-01-06")],
            "SOFR": [1.55],
        })
        cfg: PiTConfig = {"offset_days": 1, "fill_method": "ffill"}
        aligned = apply_pit_offset(raw, "SOFR", cfg, trading_days)

        # 2020-01-06 should NOT have the value (not yet available)
        assert pd.isna(aligned.loc["2020-01-06"]) if "2020-01-06" in aligned.index else True
        # 2020-01-07 must have the value (after offset)
        assert aligned.loc["2020-01-07"] == pytest.approx(1.55)

    def test_offset_zero_aligns_on_same_day(self):
        """VIX (offset=0): published same day, useable immediately."""
        trading_days = pd.bdate_range("2020-01-01", "2021-12-31")
        raw = pd.DataFrame({
            "observation_date": [pd.Timestamp("2020-01-06")],
            "VIXCLS": [14.5],
        })
        cfg: PiTConfig = {"offset_days": 0, "fill_method": "ffill"}
        aligned = apply_pit_offset(raw, "VIXCLS", cfg, trading_days)
        assert aligned.loc["2020-01-06"] == pytest.approx(14.5)

    def test_staircase_fill_persists_until_next_release(self):
        """H.4.1 weekly WALCL: Thursday value persists through next Wednesday."""
        trading_days = pd.bdate_range("2020-01-01", "2020-03-31")

        # Two consecutive Thursday releases
        raw = pd.DataFrame({
            "observation_date": [
                pd.Timestamp("2020-01-09"),   # Thu week 1
                pd.Timestamp("2020-01-16"),   # Thu week 2
            ],
            "WALCL": [4000.0, 4100.0],
        })
        cfg: PiTConfig = {"offset_days": 1, "fill_method": "staircase"}
        aligned = apply_pit_offset(raw, "WALCL", cfg, trading_days)

        # Week 1 value (4000) available from Fri 2020-01-10 to Thu 2020-01-16
        assert aligned.loc["2020-01-10"] == pytest.approx(4000.0)  # Fri after Thu1
        assert aligned.loc["2020-01-13"] == pytest.approx(4000.0)  # Mon next week
        assert aligned.loc["2020-01-15"] == pytest.approx(4000.0)  # Wed
        # Week 2 value (4100) available from Fri 2020-01-17 onward
        assert aligned.loc["2020-01-17"] == pytest.approx(4100.0)  # Fri after Thu2

    def test_output_is_series_with_datetimeindex(self):
        trading_days = pd.bdate_range("2020-01-01", "2021-12-31")
        raw = _make_daily_series("2020-01-01", "2021-12-31")
        cfg: PiTConfig = {"offset_days": 0, "fill_method": "ffill"}
        out = apply_pit_offset(raw, "VALUE", cfg, trading_days)
        assert isinstance(out, pd.Series)
        assert isinstance(out.index, pd.DatetimeIndex)

    def test_output_index_subset_of_trading_days(self):
        """Output index must be a subset of the provided trading calendar."""
        trading_days = pd.bdate_range("2020-01-01", "2021-12-31")
        raw = _make_daily_series("2020-01-01", "2021-06-30")
        cfg: PiTConfig = {"offset_days": 1, "fill_method": "ffill"}
        out = apply_pit_offset(raw, "VALUE", cfg, trading_days)
        assert out.index.isin(trading_days).all(), (
            "Output index contains non-trading-days"
        )

    def test_weekend_dates_not_in_output(self):
        """Saturdays and Sundays must not appear in the aligned series."""
        trading_days = pd.bdate_range("2020-01-01", "2021-12-31")
        raw = _make_daily_series("2020-01-01", "2020-12-31")
        cfg: PiTConfig = {"offset_days": 0, "fill_method": "ffill"}
        out = apply_pit_offset(raw, "VALUE", cfg, trading_days)
        assert (out.index.dayofweek < 5).all()


class TestAssertNoNan:
    """_assert_no_nan: hard physical safety valve — must raise, not warn."""

    def test_clean_panel_passes(self):
        idx = pd.bdate_range("2015-01-02", periods=10)
        panel = pd.DataFrame({"A": 1.0, "B": 2.0}, index=idx)
        # Must not raise
        _assert_no_nan(panel, "2015-01-02", idx[-1].strftime("%Y-%m-%d"))

    def test_nan_in_panel_raises_value_error(self):
        idx = pd.bdate_range("2015-01-02", periods=10)
        panel = pd.DataFrame({"A": 1.0, "B": np.nan}, index=idx)
        with pytest.raises(ValueError, match="NaN contamination"):
            _assert_no_nan(panel, "2015-01-02", idx[-1].strftime("%Y-%m-%d"))

    def test_error_message_names_affected_column(self):
        idx = pd.bdate_range("2015-01-02", periods=5)
        panel = pd.DataFrame({"WALCL": np.nan, "SOFR": 1.5}, index=idx)
        with pytest.raises(ValueError) as exc_info:
            _assert_no_nan(panel, "2015-01-02", idx[-1].strftime("%Y-%m-%d"))
        assert "WALCL" in str(exc_info.value)

    def test_nan_outside_trim_window_passes(self):
        """NaN before start_date must not trigger the assertion (pre-trim zone)."""
        idx = pd.bdate_range("2015-01-02", periods=20)
        panel = pd.DataFrame({"A": 1.0, "B": 2.0}, index=idx)
        # Inject NaN before start_date (should be invisible to the trimmed check)
        panel.loc[idx[0], "A"] = np.nan
        # Trim window starts at idx[5]
        trim_start = idx[5].strftime("%Y-%m-%d")
        trim_end = idx[-1].strftime("%Y-%m-%d")
        # Must NOT raise (NaN is outside the trimmed window)
        _assert_no_nan(panel, trim_start, trim_end)
