"""Focused tests for the allocation policy mapping."""
from __future__ import annotations

from datetime import date

import pytest

from src.engine.aggregator import aggregate, recommend_allocation
from src.models import (
    AllocationState,
    OptionsOverlay,
    Signal,
    SignalDetail,
    Tier1Result,
    Tier2Result,
)


def _signal(name: str, points: int) -> SignalDetail:
    return SignalDetail(
        name=name,
        value=float(points),
        points=points,
        thresholds=(0.0, 0.0),
        triggered_half=points > 0,
        triggered_full=points >= 20,
    )


def _tier1(*, drawdown: int, ma200: int, vix: int, fear_greed: int, breadth: int, descent_velocity: str | None = None) -> Tier1Result:
    stress_score = drawdown + vix
    capitulation_score = fear_greed + breadth
    persistence_score = ma200
    return Tier1Result(
        score=drawdown + ma200 + vix + fear_greed + breadth,
        drawdown_52w=_signal("drawdown_52w", drawdown),
        ma200_deviation=_signal("ma200_deviation", ma200),
        vix=_signal("vix", vix),
        fear_greed=_signal("fear_greed", fear_greed),
        breadth=_signal("breadth", breadth),
        stress_score=stress_score,
        capitulation_score=capitulation_score,
        persistence_score=persistence_score,
        descent_velocity=descent_velocity,
    )


def _tier2(*, weak_overlay: bool = False) -> Tier2Result:
    return Tier2Result(
        adjustment=0,
        put_wall=400.0,
        call_wall=430.0,
        gamma_flip=405.0,
        support_confirmed=not weak_overlay,
        support_broken=weak_overlay,
        upside_open=not weak_overlay,
        gamma_positive=not weak_overlay,
        gamma_source="yfinance",
        put_wall_distance_pct=0.01,
        call_wall_distance_pct=0.07,
        overlay=OptionsOverlay(
            can_reduce_tranche=weak_overlay,
            cannot_upgrade_structural_state=True,
            tranche_multiplier=0.5 if weak_overlay else 1.0,
            confidence="low" if weak_overlay else "medium",
            delay_days=1 if weak_overlay else 0,
        ),
    )


class TestRecommendAllocation:
    def test_neutral_calm_maps_to_base_dca(self):
        assert recommend_allocation("NEUTRAL", "CALM") == AllocationState.BASE_DCA

    def test_transition_stress_capitulation_maps_to_slow_accumulate(self):
        assert recommend_allocation("TRANSITION_STRESS", "CAPITULATION") == AllocationState.SLOW_ACCUMULATE

    def test_crisis_panic_maps_to_risk_containment(self):
        assert recommend_allocation("CRISIS", "PANIC") == AllocationState.RISK_CONTAINMENT

    def test_neutral_capitulation_maps_to_fast_accumulate(self):
        assert recommend_allocation("NEUTRAL", "CAPITULATION") == AllocationState.FAST_ACCUMULATE

    def test_euphoric_calm_pauses_chasing(self):
        assert recommend_allocation("EUPHORIC", "CALM") == AllocationState.PAUSE_CHASING


class TestAllocationGuardrails:
    def test_fast_accumulate_sets_guardrails(self):
        tier1 = _tier1(drawdown=20, ma200=20, vix=20, fear_greed=20, breadth=20)
        tier2 = _tier2()

        result = aggregate(date(2026, 3, 8), 410.0, tier1, tier2)

        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.TRIGGERED
        assert result.daily_tranche_pct == 0.75
        assert result.max_total_add_pct == 2.0
        assert result.cooldown_days >= 2
        assert "all-in" not in result.explanation.lower()

    def test_overlay_softens_fast_accumulate_without_upgrading_state(self):
        tier1 = _tier1(drawdown=20, ma200=20, vix=20, fear_greed=20, breadth=20)
        tier2 = _tier2(weak_overlay=True)

        result = aggregate(date(2026, 3, 8), 410.0, tier1, tier2)

        assert result.allocation_state == AllocationState.FAST_ACCUMULATE
        assert result.signal == Signal.WATCH
        assert result.daily_tranche_pct < 0.75
        assert result.cooldown_days >= 2
        assert result.confidence == "low"

    def test_erp_value_is_preserved_on_result(self):
        tier1 = _tier1(drawdown=15, ma200=15, vix=15, fear_greed=15, breadth=15)
        tier2 = _tier2()

        result = aggregate(date(2026, 3, 8), 410.0, tier1, tier2, forward_pe=25.0, real_yield=2.0)

        assert result.erp == pytest.approx(2.0)
