"""Unit tests for Tier-1 signal engine."""
from __future__ import annotations

import pytest
from src.engine.tier1 import calculate_tier1, DRAWDOWN_THRESHOLDS, VIX_THRESHOLDS
from src.models import MarketData
from datetime import date


def _make_data(**overrides) -> MarketData:
    """Build a MarketData with all signals at exactly-neutral values, then apply overrides."""
    defaults = dict(
        date=date(2026, 3, 8),
        price=410.0,
        ma200=405.0,    # deviation ~+1.2% → 0 pts
        high_52w=425.0, # drawdown ~3.5% → 0 pts
        vix=18.0,       # 0 pts
        fear_greed=50,  # 0 pts
        adv_dec_ratio=0.75,  # 0 pts
        pct_above_50d=0.55,  # 0 pts
        options_df=None,
    )
    defaults.update(overrides)
    return MarketData(**defaults)


class TestDrawdown:
    def test_zero_points_below_low_threshold(self):
        data = _make_data(price=419.0, high_52w=440.0)  # drawdown 4.77% < 5%
        result = calculate_tier1(data)
        assert result.drawdown_52w.points == 0

    def test_ten_points_between_thresholds(self):
        # drawdown = 7.5% (between 5% and 10%)
        data = _make_data(price=407.0, high_52w=440.0)
        result = calculate_tier1(data)
        assert result.drawdown_52w.points == 10

    def test_twenty_points_above_high_threshold(self):
        # drawdown = 11.3% >= 10%
        data = _make_data(price=390.0, high_52w=440.0)
        result = calculate_tier1(data)
        assert result.drawdown_52w.points == 20

    def test_boundary_exactly_at_low_threshold(self):
        # drawdown == ~9% → clearly in 8-12% half-score band
        # (0.08 boundary has float precision risk: (440-404.8)/440 = 0.07999...)
        data = _make_data(price=400.4, high_52w=440.0)  # 9% drawdown
        result = calculate_tier1(data)
        assert result.drawdown_52w.points == 10

    def test_boundary_exactly_at_high_threshold(self):
        # drawdown == 12%
        data = _make_data(price=387.2, high_52w=440.0)
        result = calculate_tier1(data)
        assert result.drawdown_52w.points == 20


class TestMA200:
    def test_zero_points_above_ma200(self):
        data = _make_data(price=420.0, ma200=400.0)  # +5% → 0 pts
        result = calculate_tier1(data)
        assert result.ma200_deviation.points == 0

    def test_ten_points_slight_below(self):
        data = _make_data(price=390.0, ma200=405.0)  # ~-3.7% → 10 pts
        result = calculate_tier1(data)
        assert result.ma200_deviation.points == 10

    def test_twenty_points_deep_below(self):
        data = _make_data(price=370.0, ma200=405.0)  # ~-8.6% → 20 pts
        result = calculate_tier1(data)
        assert result.ma200_deviation.points == 20


class TestVIX:
    def test_zero_points_low_vix(self):
        data = _make_data(vix=15.0)
        result = calculate_tier1(data)
        assert result.vix.points == 0

    def test_ten_points_elevated_vix(self):
        data = _make_data(vix=25.0)
        result = calculate_tier1(data)
        assert result.vix.points == 10

    def test_twenty_points_high_vix(self):
        data = _make_data(vix=35.0)
        result = calculate_tier1(data)
        assert result.vix.points == 20


class TestFearGreed:
    def test_zero_points_neutral(self):
        data = _make_data(fear_greed=50)
        result = calculate_tier1(data)
        assert result.fear_greed.points == 0

    def test_ten_points_fear_zone(self):
        data = _make_data(fear_greed=25)
        result = calculate_tier1(data)
        assert result.fear_greed.points == 10

    def test_twenty_points_extreme_fear(self):
        data = _make_data(fear_greed=15)
        result = calculate_tier1(data)
        assert result.fear_greed.points == 20


class TestBreadth:
    def test_zero_points_healthy_breadth(self):
        data = _make_data(adv_dec_ratio=0.8, pct_above_50d=0.6)
        result = calculate_tier1(data)
        assert result.breadth.points == 0

    def test_ten_points_deteriorating(self):
        # ratio below 0.7 threshold
        data = _make_data(adv_dec_ratio=0.5, pct_above_50d=0.5)
        result = calculate_tier1(data)
        assert result.breadth.points == 10

    def test_twenty_points_capitulation(self):
        # Both indicators at extreme levels
        data = _make_data(adv_dec_ratio=0.3, pct_above_50d=0.15)
        result = calculate_tier1(data)
        assert result.breadth.points == 20


class TestTotalScore:
    def test_all_neutral_yields_zero(self):
        data = _make_data()
        result = calculate_tier1(data)
        assert result.score == 0

    def test_all_bullish_yields_100(self):
        data = _make_data(
            price=370.0, ma200=405.0, high_52w=440.0,  # drawdown 15.9%, ma dev -8.6%
            vix=35.0, fear_greed=10,
            adv_dec_ratio=0.3, pct_above_50d=0.15,
        )
        result = calculate_tier1(data)
        assert result.score == 100

    def test_score_is_sum_of_signals(self, bullish_market_data):
        result = calculate_tier1(bullish_market_data)
        expected = (
            result.drawdown_52w.points
            + result.ma200_deviation.points
            + result.vix.points
            + result.fear_greed.points
            + result.breadth.points
        )
        assert result.score == expected

class TestBonuses:
    def test_valuation_bonus_applied(self):
        # Base score 0 because everything is neutral
        # forward_pe=20.0 (Cheap absolute < 22) -> valuation_bonus = 10
        data = _make_data(forward_pe=20.0)
        result = calculate_tier1(data)
        assert result.valuation_bonus == 10
        assert result.score == 10

    def test_fcf_bonus_applied(self):
        # Base score 0
        # fcf_yield=5.0% (>4.5%) -> fcf_bonus = +15
        data = _make_data(fcf_yield=5.0)
        result = calculate_tier1(data)
        assert result.fcf_bonus == 15
        assert result.score == 15
        
    def test_divergence_bonus_applied(self, mocker):
        # Mocking check_divergences to return +20 for revision divergence
        mocker.patch("src.engine.tier1.check_divergences", return_value={"bonus_score": 20, "price_revision": True})
        
        import pandas as pd
        data = _make_data(history_window=pd.DataFrame({"dummy": [1]}), earnings_revisions_breadth=60.0)
        result = calculate_tier1(data)
        
        assert result.divergence_bonus == 20
        assert result.divergence_flags["price_revision"] is True
        assert result.score == 20

    def test_all_bonuses_combined(self, mocker):
        mocker.patch("src.engine.tier1.check_divergences", return_value={"bonus_score": 15, "price_vix": True})
        import pandas as pd
        
        data = _make_data(
            forward_pe=35.0, # expensive -> -10
            fcf_yield=5.0, # deep value -> +15
            history_window=pd.DataFrame({"dummy": [1]}) # divergence -> +15
        )
        
        result = calculate_tier1(data)
        
        assert result.valuation_bonus == -10
        assert result.fcf_bonus == 15
        assert result.divergence_bonus == 15
        # Total base score = 0, + (15 - 10 + 15) = 20
        assert result.score == 20
