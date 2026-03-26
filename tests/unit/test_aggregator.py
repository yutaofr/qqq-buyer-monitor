"""Unit tests for the allocation policy and signal compatibility layer."""
from __future__ import annotations

from datetime import date

from src.engine.aggregator import TRIGGERED_THRESHOLD, WATCH_THRESHOLD, aggregate
from src.models import (
    AllocationState,
    OptionsOverlay,
    Signal,
    SignalDetail,
    Tier1Result,
    Tier2Result,
)


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
    drawdown = per + (10 if rem >= 1 else 0)
    ma200 = per
    vix = per
    fear_greed = per
    breadth = per
    return Tier1Result(
        score=score,
        drawdown_52w=sig("drawdown_52w", drawdown),
        ma200_deviation=sig("ma200_deviation", ma200),
        vix=sig("vix", vix),
        fear_greed=sig("fear_greed", fear_greed),
        breadth=sig("breadth", breadth),
        stress_score=drawdown + vix,
        capitulation_score=fear_greed + breadth,
        persistence_score=ma200,
    )


def _tier2(
    adjustment: int = 0,
    support_broken: bool = False,
    support_confirmed: bool = False,
    upside_open: bool = False,
    gamma_positive: bool = False,
) -> Tier2Result:
    can_reduce_tranche = support_broken
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
        overlay=OptionsOverlay(
            can_reduce_tranche=can_reduce_tranche,
            cannot_upgrade_structural_state=True,
            tranche_multiplier=0.5 if can_reduce_tranche else 1.0,
            confidence="low" if can_reduce_tranche else "medium",
            delay_days=1 if can_reduce_tranche else 0,
        ),
    )


# ── Three-state logic ────────────────────────────────────────────────────────

class TestThreeStateLogic:
    def test_triggered_when_score_high_and_no_broken(self):
        t1 = _tier1(80)
        t2 = _tier2(adjustment=0)  # final = 80
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.TRIGGERED

    def test_watch_when_score_medium_and_no_broken(self):
        t1 = _tier1(50)
        t2 = _tier2(adjustment=0)  # final = 50
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH

    def test_base_dca_when_score_low(self):
        t1 = _tier1(20)
        t2 = _tier2(adjustment=0)  # final = 20
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.BASE_DCA
        assert result.signal == Signal.NO_SIGNAL

    def test_score_70_maps_to_watch_under_allocation_first_projection(self):
        t1 = _tier1(TRIGGERED_THRESHOLD)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH

    def test_score_40_maps_to_base_dca_and_no_signal(self):
        t1 = _tier1(WATCH_THRESHOLD)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.BASE_DCA
        assert result.signal == Signal.NO_SIGNAL

    def test_score_39_still_maps_to_watch_with_helper_buckets(self):
        t1 = _tier1(WATCH_THRESHOLD - 1)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH


# ── PUT WALL SOFT OVERLAY tests ──────────────────────────────────────────────

class TestPutWallSoftOverlay:
    """support_broken=True may soften, but must not erase a strong Tier-1 setup."""

    def test_weak_overlay_softens_a_strong_setup_to_watch(self):
        t1 = _tier1(100)  # max tier1
        t2 = _tier2(adjustment=15, support_broken=True)  # soft overlay only
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.daily_tranche_pct < 0.75
        assert result.confidence == "low"

    def test_weak_overlay_softens_fast_accumulate_to_watch(self):
        t1 = _tier1(80)
        t2 = _tier2(adjustment=-40, support_broken=True)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.final_score == 40
        assert result.daily_tranche_pct < 0.75

    def test_low_score_projection_stays_no_signal(self):
        t1 = _tier1(20)
        t2 = _tier2(adjustment=0)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.BASE_DCA
        assert result.signal == Signal.NO_SIGNAL

    def test_no_veto_without_support_broken(self):
        t1 = _tier1(100)
        t2 = _tier2(adjustment=0, support_broken=False)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)
        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
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

    def test_positive_tier2_does_not_upgrade_signal_state(self):
        t1 = _tier1(55)
        t2 = _tier2(adjustment=15, support_confirmed=True, upside_open=True, gamma_positive=True)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)

        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.final_score == 70
        assert result.daily_tranche_pct == 0.5

    def test_overlay_gate_cannot_make_slow_allocation_more_aggressive(self):
        t1 = _tier1(55)
        t2 = Tier2Result(
            adjustment=15,
            put_wall=400.0,
            call_wall=430.0,
            gamma_flip=405.0,
            support_confirmed=True,
            support_broken=False,
            upside_open=True,
            gamma_positive=True,
            gamma_source="yfinance",
            put_wall_distance_pct=0.01,
            call_wall_distance_pct=0.07,
            overlay=OptionsOverlay(
                can_reduce_tranche=False,
                cannot_upgrade_structural_state=False,
                tranche_multiplier=1.0,
                confidence="high",
                delay_days=0,
            ),
        )

        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)

        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.final_score == 70


class TestAllocationSurface:
    def test_result_exposes_allocation_defaults(self):
        t1 = _tier1(20)
        t2 = _tier2(support_confirmed=True, upside_open=True, gamma_positive=True)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)

        assert result.allocation_state == AllocationState.BASE_DCA
        assert result.daily_tranche_pct == 0.25
        assert result.max_total_add_pct == 1.0
        assert result.cooldown_days == 0
        assert result.required_persistence_days == 1
        assert result.confidence == "medium"
        assert isinstance(result.data_quality, dict)

    def test_negative_tier2_softens_fast_accumulate_to_watch(self):
        t1 = _tier1(80)
        t2 = _tier2(adjustment=-40, support_broken=True)
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2)

        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.daily_tranche_pct < 0.75
        assert result.cooldown_days >= 2
        assert result.confidence == "low"

# ── Macro Veto & ERP Regime tests ─────────────────────────────────────────────
class TestMacroAndERPRegimes:
    def test_macro_veto_prevents_triggered(self):
        t1 = _tier1(100)
        t2 = _tier2()
        # Current structural crisis threshold is 650 bps.
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, credit_spread=650.0)
        assert result.allocation_state == AllocationState.RISK_CONTAINMENT
        assert result.signal == Signal.NO_SIGNAL
        assert "RISK_CONTAINMENT" in result.explanation

    def test_low_erp_slows_allocation(self):
        t1 = _tier1(75)
        t2 = _tier2()
        # forward_pe=25, real_yield=2.0 -> ERP=2.0%, which lands in rich-tightening.
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, forward_pe=25.0, real_yield=2.0)
        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH

    def test_high_erp_pauses_chasing(self):
        t1 = _tier1(65)
        t2 = _tier2()
        # forward_pe=14.28, real_yield=0.0 -> ERP=7.0%, which is euphoric.
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, credit_spread=180.0, forward_pe=14.28, real_yield=0.0)
        assert result.allocation_state == AllocationState.PAUSE_CHASING
        assert result.signal == Signal.NO_SIGNAL
        assert "all-in" not in result.explanation.lower()

    def test_erp_normal_mode(self):
        t1 = _tier1(70)
        t2 = _tier2()
        # forward_pe=20, real_yield=1.0 -> ERP=4.0%, which remains neutral.
        result = aggregate(date(2026, 3, 8), 410.0, t1, t2, forward_pe=20.0, real_yield=1.0)
        assert result.allocation_state == AllocationState.SLOW_ACCUMULATE
        assert result.signal == Signal.WATCH
