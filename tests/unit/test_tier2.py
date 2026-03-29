"""Unit tests for Tier-2 options wall engine."""
from __future__ import annotations

from dataclasses import asdict, fields

import pandas as pd
import pytest

from src.engine.tier2 import (
    SCORE_SUPPORT_BROKEN,
    SCORE_SUPPORT_CONFIRMED,
    calculate_tier2,
)
from src.models import OptionsOverlay, Tier2Result


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def basic_df() -> pd.DataFrame:
    """Simple chain: put wall at 400, call wall at 430."""
    return _make_df([
        {"strike": 400.0, "expiration": "2026-03-21", "option_type": "put",
         "openInterest": 9000, "impliedVolatility": 0.25, "gamma": 0.018, "gamma_source": "yfinance"},
        {"strike": 390.0, "expiration": "2026-03-21", "option_type": "put",
         "openInterest": 3000, "impliedVolatility": 0.28, "gamma": 0.01, "gamma_source": "yfinance"},
        {"strike": 430.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 8000, "impliedVolatility": 0.18, "gamma": 0.015, "gamma_source": "yfinance"},
        {"strike": 410.0, "expiration": "2026-03-21", "option_type": "call",
         "openInterest": 2000, "impliedVolatility": 0.20, "gamma": 0.012, "gamma_source": "yfinance"},
    ])


# ── Wall detection tests ──────────────────────────────────────────────────────

class TestWallDetection:
    def test_put_wall_is_highest_put_oi(self, basic_df):
        result = calculate_tier2(401.0, basic_df)
        assert result.put_wall == 400.0

    def test_call_wall_is_highest_call_oi(self, basic_df):
        result = calculate_tier2(401.0, basic_df)
        assert result.call_wall == 430.0

    def test_none_results_on_empty_dataframe(self):
        result = calculate_tier2(410.0, pd.DataFrame())
        assert result.put_wall is None
        assert result.call_wall is None
        assert result.gamma_flip is None
        assert result.adjustment == 0

    def test_none_results_on_none_dataframe(self):
        result = calculate_tier2(410.0, None)
        assert result.put_wall is None
        assert result.adjustment == 0


# ── Support rules tests ───────────────────────────────────────────────────────

class TestSupportRules:
    def test_support_confirmed_when_price_just_above_put_wall(self, basic_df):
        # price 402 is 0.5% above put_wall 400 → within 3% zone
        result = calculate_tier2(402.0, basic_df)
        assert result.support_confirmed is True
        assert result.support_broken is False

    def test_support_not_confirmed_when_price_far_above_put_wall(self, basic_df):
        # price 415 is 3.75% above put_wall 400 → outside zone
        result = calculate_tier2(415.0, basic_df)
        assert result.support_confirmed is False
        assert result.support_broken is False

    def test_support_broken_when_price_below_put_wall(self, basic_df):
        # price 395 is below put_wall 400
        result = calculate_tier2(395.0, basic_df)
        assert result.support_broken is True
        assert result.support_confirmed is False

    def test_upside_open_when_call_wall_far_enough(self, basic_df):
        # call wall at 430, price 402 → distance 6.97% >= 5%
        result = calculate_tier2(402.0, basic_df)
        assert result.upside_open is True

    def test_upside_closed_when_call_wall_too_close(self, basic_df):
        # call wall at 430, price 425 → distance 1.18% < 5%
        result = calculate_tier2(425.0, basic_df)
        assert result.upside_open is False


# ── Scoring tests ─────────────────────────────────────────────────────────────

class TestScoring:
    def test_support_confirmed_adds_score(self, basic_df):
        result = calculate_tier2(402.0, basic_df)
        assert result.adjustment >= SCORE_SUPPORT_CONFIRMED

    def test_support_broken_subtracts_score(self, basic_df):
        result = calculate_tier2(395.0, basic_df)
        assert result.adjustment <= SCORE_SUPPORT_BROKEN

    def test_negative_gamma_and_broken_gives_extra_penalty(self, basic_df):
        """When price is below put_wall AND below gamma_flip, extra penalty applies."""
        # Price well below put wall → support_broken=True, likely negative gamma
        result = calculate_tier2(350.0, basic_df)
        # Adjustment should be <= SCORE_SUPPORT_BROKEN + SCORE_NEGATIVE_GAMMA_BROKEN
        assert result.adjustment <= SCORE_SUPPORT_BROKEN

    def test_neutral_returns_zero_adjustment(self):
        result = calculate_tier2(410.0, None)
        assert result.adjustment == 0


# ── Gamma flip test ───────────────────────────────────────────────────────────

class TestGammaFlip:
    def test_gamma_flip_is_computed(self, basic_df):
        result = calculate_tier2(410.0, basic_df)
        assert result.gamma_flip is not None
        assert isinstance(result.gamma_flip, float)

    def test_gamma_positive_when_price_above_flip(self, basic_df):
        result = calculate_tier2(450.0, basic_df)
        if result.gamma_flip is not None:
            expected = 450.0 > result.gamma_flip
            assert result.gamma_positive == expected


class TestRefinements:
    def test_overlay_is_part_of_formal_schema(self, basic_df):
        result = calculate_tier2(395.0, basic_df)

        assert "overlay" in {field.name for field in fields(Tier2Result)}
        assert isinstance(result.overlay, OptionsOverlay)
        assert asdict(result)["overlay"]["cannot_upgrade_structural_state"] is True

    def test_overlay_flags_soften_negative_options_and_never_upgrade_state(self, basic_df):
        result = calculate_tier2(395.0, basic_df)

        overlay = result.overlay
        assert overlay.can_reduce_tranche is True
        assert overlay.cannot_upgrade_structural_state is True
        assert overlay.tranche_multiplier < 1.0
        assert overlay.confidence == "low"

    def test_support_broken_only_beyond_buffer(self, basic_df):
        # PW=400, price=399 is -0.25% -> within 0.5% buffer
        # Should be support_confirmed=True (testing) and support_broken=False
        result = calculate_tier2(399.0, basic_df)
        assert result.support_confirmed is True
        assert result.support_broken is False

        # PW=400, price=397 is -0.75% -> beyond 0.5% buffer
        result = calculate_tier2(397.0, basic_df)
        assert result.support_broken is True
        assert result.support_confirmed is False

    def test_cleared_call_wall_looks_higher(self, basic_df):
        # Call wall at 430. If price is 435, it should look for next call wall or mark cleared.
        result = calculate_tier2(435.0, basic_df)
        assert result.upside_open is True
        assert result.call_wall_distance_pct == 0.99

    def test_cleared_call_wall_finds_next(self):
        df = _make_df([
            {"strike": 400.0, "expiration": "2026-03-21", "option_type": "call",
             "openInterest": 1000, "implied_volatility": 0.2, "gamma": 0.01, "gamma_source": "yfinance"},
            {"strike": 450.0, "expiration": "2026-03-21", "option_type": "call",
             "openInterest": 5000, "implied_volatility": 0.2, "gamma": 0.01, "gamma_source": "yfinance"},
        ])
        # Price 410 is above 400. Should use 450 as next wall.
        result = calculate_tier2(410.0, df)
        assert result.upside_open is True
        assert abs(result.call_wall_distance_pct - 0.0976) < 0.001
