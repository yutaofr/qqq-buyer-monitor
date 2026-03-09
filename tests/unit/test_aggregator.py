"""Unit tests for the signal aggregator."""
from __future__ import annotations

import pytest
from datetime import date
from src.engine.aggregator import aggregate, TRIGGERED_THRESHOLD, WATCH_THRESHOLD
from src.models import Signal, SignalDetail, Tier1Result, Tier2Result


def _tier1(score: int) -> Tier1Result:
    """Build a minimal Tier1Result with a given total score."""
    def sig(name, pts):
        return SignalDetail(
            name=name, value=0.0, points=pts,
            thresholds=(0.0, 0.0), triggered_half=pts > 0, triggered_full=pts >= 20
        )
    # Distribute score across 5 signals (simplified)
    per = score // 5
    rem = score % 5
    return Tier1Result(
        score=score,
        drawdown_52w=sig("drawdown_52w", per + (10 if rem >= 1 else 0)),
        ma200_deviation=sig("ma200_deviation", per),
        vix=sig("vix", per),
        fear_greed=sig("fear_greed", per),
        breadth=sig("breadth", per),
    )


def _tier2(
    adjustment: int = 0,
    support_broken: bool = False,
    support_confirmed: bool = False,
    upside_open: bool = False,
    gamma_positive: bool = False,
) -> Tier2Result:
    return Tier2Result(
        adjustment=adjustment,
        put_wall=400.0,
        call_wall=430.0,
        gamma_flip=405.0,
        support_confirmed=support_confirmed,
        support_broken=support_broken,
        upside_open=upside_open,
        gamma_positive=gamma_positive,
        gamma_source="yfinance",
        put_wall_distance_pct=0.01 if support_confirmed else 0.05,
        call_wall_distance_pct=0.07 if upside_open else 0.02,
    )


# ── Three-state logic ────────────────────────────────────────────────────────

class TestThreeStateLogic:
    def test_triggered_when_score_high_and_no_broken(self):
        t1 = _tier1(80)
        t2 = _tier2(adjustment=0)  # final = 80
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.TRIGGERED

    def test_watch_when_score_medium_and_no_broken(self):
        t1 = _tier1(50)
        t2 = _tier2(adjustment=0)  # final = 50
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.WATCH

    def test_no_signal_when_score_low(self):
        t1 = _tier1(20)
        t2 = _tier2(adjustment=0)  # final = 20
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.NO_SIGNAL

    def test_boundary_exactly_at_triggered_threshold(self):
        t1 = _tier1(TRIGGERED_THRESHOLD)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.TRIGGERED

    def test_boundary_exactly_at_watch_threshold(self):
        t1 = _tier1(WATCH_THRESHOLD)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.WATCH

    def test_just_below_watch_threshold_is_no_signal(self):
        t1 = _tier1(WATCH_THRESHOLD - 1)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.NO_SIGNAL


# ── PUT WALL HARD VETO tests ─────────────────────────────────────────────────

class TestPutWallHardVeto:
    """support_broken=True must NEVER allow TRIGGERED state."""

    def test_veto_prevents_triggered_even_with_perfect_tier1(self):
        t1 = _tier1(100)  # max tier1
        t2 = _tier2(adjustment=15, support_broken=True)  # final = 115 → but veto!
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal != Signal.TRIGGERED, (
            "HARD VETO FAILED: support_broken=True should prevent TRIGGERED"
        )

    def test_veto_allows_watch_when_score_in_watch_range(self):
        t1 = _tier1(80)
        t2 = _tier2(adjustment=-40, support_broken=True)  # final = 40 → WATCH range
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.WATCH

    def test_veto_allows_no_signal_when_score_below_watch(self):
        t1 = _tier1(30)
        t2 = _tier2(adjustment=-30, support_broken=True)  # final = 0 → NO_SIGNAL
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.NO_SIGNAL

    def test_no_veto_without_support_broken(self):
        t1 = _tier1(100)
        t2 = _tier2(adjustment=0, support_broken=False)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.signal == Signal.TRIGGERED


# ── Score and explanation tests ──────────────────────────────────────────────

class TestScoreAndExplanation:
    def test_final_score_is_tier1_plus_tier2(self):
        t1 = _tier1(60)
        t2 = _tier2(adjustment=15)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.final_score == 75

    def test_explanation_is_non_empty_string(self):
        t1 = _tier1(60)
        t2 = _tier2(adjustment=15, support_confirmed=True)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 10

    def test_result_date_and_price_preserved(self):
        t1 = _tier1(50)
        t2 = _tier2()
        d = date(2026, 3, 8)
        result = aggregate(d, 412.35, t1, t2)
        assert result.date == d
        assert result.price == 412.35

# ── Macro Veto & ERP Regime tests ─────────────────────────────────────────────
class TestMacroAndERPRegimes:
    def test_macro_veto_prevents_triggered(self):
        t1 = _tier1(100)
        t2 = _tier2()
        # Even with max score, macro veto overrides (threshold is 500 bps)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, credit_spread=600.0)
        assert result.signal != Signal.TRIGGERED
        assert "流动性危机" in result.explanation

    def test_erp_defense_mode_raises_threshold(self):
        # ERP < 1% -> Defense mode (Threshold 85)
        # Score 75 is normally TRIGGERED (75 >= 70), but in Defense it should be WATCH
        t1 = _tier1(75)
        t2 = _tier2()
        # forward_pe=25, us10y=4.0 -> EY=4%, ERP=0% (Defense)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, forward_pe=25.0, us10y=4.0)
        assert result.signal == Signal.WATCH
        assert "[防守模式]" in result.explanation

    def test_erp_aggressive_mode_lowers_threshold(self):
        # ERP > 5% -> Aggressive mode (Threshold 65)
        # Score 65 is normally WATCH (<70), but in Aggressive it should be TRIGGERED
        t1 = _tier1(65)
        t2 = _tier2()
        # forward_pe=14.28, us10y=1.0 -> EY=7.0%, ERP=6.0% (Aggressive)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, forward_pe=14.28, us10y=1.0)
        assert result.signal == Signal.TRIGGERED
        assert "[百年一遇]" in result.explanation

    def test_erp_normal_mode(self):
        # ERP between 1% and 5% -> Normal mode (Threshold 70)
        t1 = _tier1(70)
        t2 = _tier2()
        # forward_pe=20, us10y=3.0 -> EY=5.0%, ERP=2.0% (Normal)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, forward_pe=20.0, us10y=3.0)
        assert result.signal == Signal.TRIGGERED
        assert "[防守模式]" not in result.explanation
        assert "[百年一遇]" not in result.explanation
