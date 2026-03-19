"""
Allocation policy engine: combines slow-horizon structure, tactical stress,
and Tier-2 overlay into a long-term QQQ sizing recommendation.

The primary output surface is `allocation_state`. `signal` remains as a
compatibility projection for callers that still expect the legacy enum.
"""
from __future__ import annotations

from datetime import date

from src.engine.tier0_macro import assess_structural_regime, check_erp_regime
from src.models import AllocationState, OptionsOverlay, Signal, SignalResult, Tier1Result, Tier2Result

TRIGGERED_THRESHOLD = 70
WATCH_THRESHOLD = 40

_SIGNAL_RANK = {
    Signal.NO_SIGNAL: 0,
    Signal.WATCH: 1,
    Signal.TRIGGERED: 2,
    Signal.STRONG_BUY: 3,
    Signal.GREEDY: 0,
}

_MAX_SIGNAL_BY_ALLOCATION = {
    AllocationState.PAUSE_CHASING: Signal.NO_SIGNAL,
    AllocationState.BASE_DCA: Signal.NO_SIGNAL,
    AllocationState.SLOW_ACCUMULATE: Signal.WATCH,
    AllocationState.FAST_ACCUMULATE: Signal.TRIGGERED,
    AllocationState.RISK_CONTAINMENT: Signal.NO_SIGNAL,
}

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}

_ALLOCATION_PROFILE = {
    AllocationState.PAUSE_CHASING: {
        "daily_tranche_pct": 0.0,
        "max_total_add_pct": 0.0,
        "cooldown_days": 0,
        "required_persistence_days": 1,
        "confidence": "low",
    },
    AllocationState.BASE_DCA: {
        "daily_tranche_pct": 0.25,
        "max_total_add_pct": 1.0,
        "cooldown_days": 0,
        "required_persistence_days": 1,
        "confidence": "medium",
    },
    AllocationState.SLOW_ACCUMULATE: {
        "daily_tranche_pct": 0.50,
        "max_total_add_pct": 1.5,
        "cooldown_days": 0,
        "required_persistence_days": 1,
        "confidence": "medium",
    },
    AllocationState.FAST_ACCUMULATE: {
        "daily_tranche_pct": 0.75,
        "max_total_add_pct": 2.0,
        "cooldown_days": 2,
        "required_persistence_days": 2,
        "confidence": "high",
    },
    AllocationState.RISK_CONTAINMENT: {
        "daily_tranche_pct": 0.10,
        "max_total_add_pct": 0.5,
        "cooldown_days": 1,
        "required_persistence_days": 1,
        "confidence": "low",
    },
}


def recommend_allocation(structural: str, tactical: str) -> AllocationState:
    """Map structural regime + tactical state into an allocation state."""
    structural = (structural or "NEUTRAL").upper()
    tactical = (tactical or "CALM").upper()

    if structural == "CRISIS":
        return AllocationState.RISK_CONTAINMENT
    if structural == "EUPHORIC":
        return AllocationState.PAUSE_CHASING
    if structural == "TRANSITION_STRESS":
        if tactical == "PANIC":
            return AllocationState.RISK_CONTAINMENT
        if tactical == "CAPITULATION":
            return AllocationState.SLOW_ACCUMULATE
        if tactical in {"STRESS", "PERSISTENT_STRESS"}:
            return AllocationState.SLOW_ACCUMULATE
        return AllocationState.BASE_DCA
    if structural == "RICH_TIGHTENING":
        if tactical == "PANIC":
            return AllocationState.RISK_CONTAINMENT
        if tactical == "CAPITULATION":
            return AllocationState.SLOW_ACCUMULATE
        if tactical in {"STRESS", "PERSISTENT_STRESS"}:
            return AllocationState.SLOW_ACCUMULATE
        return AllocationState.BASE_DCA

    if tactical == "PANIC":
        return AllocationState.RISK_CONTAINMENT
    if tactical == "CAPITULATION":
        return AllocationState.FAST_ACCUMULATE
    if tactical in {"STRESS", "PERSISTENT_STRESS"}:
        return AllocationState.SLOW_ACCUMULATE
    return AllocationState.BASE_DCA


def aggregate(
    market_date: date,
    price: float,
    tier1: Tier1Result,
    tier2: Tier2Result,
    prev_signal: Signal | None = None,
    credit_spread: float | None = None,
    forward_pe: float | None = None,
    real_yield: float | None = None,
    ma50: float | None = None,
) -> SignalResult:
    """
    Combine Tier-1 and Tier-2 results into a final SignalResult.

    Args:
        market_date: Date the signal is computed for.
        price: QQQ closing price.
        tier1: Output of tier1.calculate_tier1().
        tier2: Output of tier2.calculate_tier2().

    Returns:
        SignalResult with three-state signal, scores, and explanation.
    """
    base_score = tier1.score
    overlay_adjustment = tier2.adjustment
    final_score = base_score + overlay_adjustment

    # Slow-horizon structure decides the regime. Tactical state decides how
    # aggressively we participate inside that regime.
    erp_val = None
    if forward_pe is not None and real_yield is not None and forward_pe > 0:
        earnings_yield = 1.0 / forward_pe
        erp_val = (earnings_yield * 100) - real_yield

    structural_regime = assess_structural_regime(credit_spread, erp_val)
    tactical_state = _classify_tactical_state(tier1)
    allocation_state = recommend_allocation(structural_regime, tactical_state)
    profile = _allocation_profile(allocation_state)
    options_overlay = tier2.overlay if tier2.overlay is not None else OptionsOverlay()

    daily_tranche_pct = profile["daily_tranche_pct"]
    max_total_add_pct = profile["max_total_add_pct"]
    cooldown_days = profile["cooldown_days"]
    required_persistence_days = profile["required_persistence_days"]
    confidence = profile["confidence"]

    if options_overlay.can_reduce_tranche:
        daily_tranche_pct = round(daily_tranche_pct * options_overlay.tranche_multiplier, 4)
        cooldown_days = max(cooldown_days, options_overlay.delay_days)
        confidence = _weaken_confidence(confidence, options_overlay.confidence)

    signal = _signal_for_allocation(allocation_state)
    if not options_overlay.cannot_upgrade_structural_state:
        signal = _signal_for_score(final_score)
    signal = _cap_signal_to_allocation(signal, allocation_state)
    if options_overlay.can_reduce_tranche and signal == Signal.TRIGGERED:
        signal = Signal.WATCH

    # Keep the legacy GREEDY escape hatch for obviously extended markets.
    if (
        signal == Signal.NO_SIGNAL
        and tier1.fear_greed.value > 75
        and base_score < 10
        and ma50 is not None
        and price > 1.06 * ma50
    ):
        signal = Signal.GREEDY

    has_major_div = (
        tier1.divergence_flags.get("price_revision") or
        tier1.divergence_flags.get("price_breadth") or
        tier1.divergence_flags.get("price_vix")
    )

    if signal == Signal.TRIGGERED and has_major_div:
        signal = Signal.STRONG_BUY
    signal = _cap_signal_to_allocation(signal, allocation_state)

    explanation = _build_explanation(
        signal,
        tier1,
        tier2,
        final_score,
        structural_regime,
        tactical_state,
        allocation_state,
        daily_tranche_pct,
        max_total_add_pct,
        cooldown_days,
        confidence,
    )
    return SignalResult(
        date=market_date,
        price=price,
        signal=signal,
        final_score=final_score,
        tier1=tier1,
        tier2=tier2,
        explanation=explanation,
        pe_source=tier1.pe_source,
        erp=erp_val,
        allocation_state=allocation_state,
        daily_tranche_pct=daily_tranche_pct,
        max_total_add_pct=max_total_add_pct,
        cooldown_days=cooldown_days,
        required_persistence_days=required_persistence_days,
        confidence=confidence,
    )


def _classify_tactical_state(tier1: Tier1Result) -> str:
    """Translate Tier-1 buckets into a tactical regime label."""
    if tier1.descent_velocity == "PANIC":
        return "PANIC"
    if tier1.capitulation_score >= 30 and tier1.stress_score >= 20:
        return "CAPITULATION"
    if tier1.descent_velocity == "GRIND" or (
        tier1.persistence_score >= 20 and tier1.stress_score >= 20
    ):
        return "PERSISTENT_STRESS"
    if tier1.stress_score >= 20:
        return "STRESS"
    return "CALM"


def _allocation_profile(state: AllocationState) -> dict[str, float | int | str]:
    return _ALLOCATION_PROFILE[state]


def _signal_for_allocation(state: AllocationState) -> Signal:
    if state == AllocationState.SLOW_ACCUMULATE:
        return Signal.WATCH
    if state == AllocationState.FAST_ACCUMULATE:
        return Signal.TRIGGERED
    return Signal.NO_SIGNAL


def _signal_for_score(score: int) -> Signal:
    if score >= TRIGGERED_THRESHOLD:
        return Signal.TRIGGERED
    if score >= WATCH_THRESHOLD:
        return Signal.WATCH
    return Signal.NO_SIGNAL


def _cap_signal_to_allocation(signal: Signal, allocation_state: AllocationState) -> Signal:
    if signal == Signal.GREEDY:
        return signal
    cap = _MAX_SIGNAL_BY_ALLOCATION[allocation_state]
    if _SIGNAL_RANK[signal] > _SIGNAL_RANK[cap]:
        return cap
    return signal


def _weaken_confidence(base: str, overlay: str) -> str:
    base_rank = _CONFIDENCE_ORDER.get(base, 1)
    overlay_rank = _CONFIDENCE_ORDER.get(overlay, base_rank)
    weakest_rank = min(base_rank, overlay_rank)
    for label, rank in _CONFIDENCE_ORDER.items():
        if rank == weakest_rank:
            return label
    return base


def _build_explanation(
    signal: Signal,
    tier1: Tier1Result,
    tier2: Tier2Result,
    final_score: int,
    structural_regime: str,
    tactical_state: str,
    allocation_state: AllocationState,
    daily_tranche_pct: float,
    max_total_add_pct: float,
    cooldown_days: int,
    confidence: str,
) -> str:
    """Generate a Chinese-language explanation of the signal rationale."""
    parts: list[str] = []

    # Tier-1 summary
    t1_score = tier1.score
    if t1_score >= 60:
        parts.append(f"Tier 1 多数信号达到触发级别（得分 {t1_score}/100）")
    elif t1_score >= 40:
        parts.append(f"Tier 1 部分信号处于观察区间（得分 {t1_score}/100）")
    else:
        parts.append(f"Tier 1 信号尚未进入关注区域（得分 {t1_score}/100）")

    # Tier-2 options wall
    pw, cw = tier2.put_wall, tier2.call_wall
    is_pivot = (pw is not None and cw is not None and pw == cw)
    
    if is_pivot:
        parts.append(f"当前价格处于 Pivot Wall（${pw}）关键争夺区")
        if tier2.support_broken:
            parts.append("价格低于 Pivot Wall，支撑转为阻力，暂缓买入")
        elif tier2.support_confirmed:
            pct = (tier2.put_wall_distance_pct or 0) * 100
            if pct < 0:
                parts.append(f"价格正在回测 Pivot Wall ({pct:.1f}%)，处于缓冲区内，需等待企稳确认")
            else:
                parts.append(f"价格守在 Pivot Wall 上方 ({pct:.1f}%)，支撑极强")
    else:
        if tier2.support_broken:
            next_wall_info = ""
            if tier2.next_put_wall is not None:
                pct = (tier2.next_put_wall_distance_pct or 0) * 100
                next_wall_info = f"，下档次级支撑: ${tier2.next_put_wall} (距离 {pct:.1f}%)"
                
            parts.append(
                f"价格已跌破 Put Wall（${tier2.put_wall}），做市商 delta 对冲压力可能加速下跌，"
                f"支撑结构转弱{next_wall_info}，建议降低单笔加仓规模并等待修复"
            )
        elif tier2.support_confirmed:
            pct = (tier2.put_wall_distance_pct or 0) * 100
            if pct < 0:
                parts.append(f"价格正处于 Put Wall（${tier2.put_wall}）回撤缓冲区 ({pct:.1f}%)，支撑面临考验")
            else:
                parts.append(f"价格站在 Put Wall（${tier2.put_wall}）上方 {pct:.1f}%，支撑确认有效")
        else:
            parts.append("当前价格距 Put Wall 较远，期权支撑结构为中性")

    # Call Wall explanation (skip if already handled in pivot)
    if not is_pivot and cw is not None:
        pct = (tier2.call_wall_distance_pct or 0) * 100
        if tier2.upside_open:
            if tier2.call_wall_distance_pct > 0.5: # Effectively means we cleared the main wall
                parts.append(f"主要 Call Wall（${cw:.0f}）已被突破，上方空间打开")
            else:
                parts.append(f"上方 Call Wall（${cw:.0f}）距离 {pct:.1f}%，反弹空间充足")
        else:
            parts.append(f"上方 Call Wall（${cw:.0f}）距离仅 {pct:.1f}%，阻力较近")

    if tier2.gamma_flip is not None:
        if tier2.gamma_positive:
            parts.append(f"价格高于 Gamma Flip（{tier2.gamma_flip:.1f}），处于正 gamma 区域，波动趋于收敛")
        else:
            parts.append(
                f"价格低于 Gamma Flip（{tier2.gamma_flip:.1f}），处于负 gamma 区域，"
                f"做市商对冲方向可能放大波动"
            )

    # Final verdict
    allocation_note = (
        f"结构 {structural_regime}，战术 {tactical_state}，仓位 {allocation_state.value}；"
        f"建议单日加仓 {daily_tranche_pct:.0%}，滚动上限 {max_total_add_pct:.1f}x，"
        f"冷却 {cooldown_days} 天，置信度 {confidence}"
    )

    if signal == Signal.GREEDY:
        parts.append(f"🚨 🌟 综合判断：触发【贪婪警告】(GREEDY)！当前市场情绪极度过热（F&G: {tier1.fear_greed.value}），且价格涨幅过快。建议分批止盈，落袋为安，切勿追高。")
    elif allocation_state == AllocationState.RISK_CONTAINMENT:
        parts.append(f"🚨 综合判断：当前进入流动性危机风险控制区间。{allocation_note}")
    elif allocation_state == AllocationState.PAUSE_CHASING:
        parts.append(f"综合判断：市场已偏热，暂停追高。{allocation_note}")
    elif allocation_state == AllocationState.FAST_ACCUMULATE:
        div_reasons = []
        if tier1.divergence_flags.get("price_revision"): div_reasons.append("基本面上修")
        if tier1.divergence_flags.get("price_breadth"): div_reasons.append("市场广度提升")
        if tier1.divergence_flags.get("price_vix"): div_reasons.append("恐慌情绪衰减")
        if tier1.divergence_flags.get("price_rsi"): div_reasons.append("动能底背离")

        div_str = " + ".join(div_reasons) if div_reasons else "多重背离确认"
        parts.append(
            f"🔥 🌟 综合判断：技术与情绪共振，允许提高加仓速度。"
            f"价格由于底背离（{div_str}）展现出逆势强度。"
        )
    elif allocation_state == AllocationState.SLOW_ACCUMULATE:
        parts.append(f"综合判断：仅小幅试探，等待更多信号确认后再入场。{allocation_note}")
    elif allocation_state == AllocationState.BASE_DCA:
        parts.append(f"综合判断：维持基础定投，条件尚未满足。{allocation_note}")
    else:
        if tier1.descent_velocity == "GRIND":
            parts.append("阴跌预警：当前市场处于无量阴跌阶段，尚未出现恐慌性底背离，系统维持观望。")
        parts.append(f"综合判断：维持基础定投，条件尚未满足。{allocation_note}")

    return "。".join(parts) + "。"
