"""
Allocation policy engine: combines slow-horizon structure, tactical stress,
and Tier-2 overlay into a long-term QQQ sizing recommendation.

Implements the Decision State Monad pattern for white-box transparency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.engine.tier0_macro import assess_structural_regime
from src.models import (
    AllocationState, OptionsOverlay, Signal, SignalResult, 
    Tier1Result, Tier2Result
)

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
    """Legacy wrapper for backward compatibility with tests/callers."""
    ctx = DecisionContext(
        market_date=date.today(), price=0.0, 
        tier1=None, tier2=None, # type: ignore
        structural_regime=structural, 
        tactical_state=tactical
    )
    ctx = _step_allocation_policy(ctx)
    return ctx.allocation_state

@dataclass(frozen=True)
class DecisionContext:
    """Monadic container for decision state accumulation."""
    market_date: date
    price: float
    tier1: Tier1Result
    tier2: Tier2Result
    credit_spread: Optional[float] = None
    erp_val: Optional[float] = None
    ma50: Optional[float] = None
    
    # State accumulated
    structural_regime: str = "NEUTRAL"
    tactical_state: str = "CALM"
    allocation_state: AllocationState = AllocationState.BASE_DCA
    signal: Signal = Signal.NO_SIGNAL
    
    # Trace (Evidence Chain)
    trace: list[dict] = field(default_factory=list)

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
    """Entry point for aggregated signal computation using pipeline."""
    
    erp_val = None
    if forward_pe is not None and real_yield is not None and forward_pe > 0:
        erp_val = (100.0 / forward_pe) - real_yield

    # 1. Initialize Context
    ctx = DecisionContext(
        market_date=market_date,
        price=price,
        tier1=tier1,
        tier2=tier2,
        credit_spread=credit_spread,
        erp_val=erp_val,
        ma50=ma50
    )

    # 2. Run Pipeline Steps
    ctx = _step_structural_regime(ctx)
    ctx = _step_tactical_state(ctx)
    ctx = _step_allocation_policy(ctx)
    ctx = _step_overlay_refinement(ctx)
    ctx = _step_finalize(ctx)

    profile = _ALLOCATION_PROFILE[ctx.allocation_state]
    
    # Compute dynamic parameters (preserving legacy override logic)
    daily_tranche_pct = profile["daily_tranche_pct"]
    cooldown_days = profile["cooldown_days"]
    confidence = profile["confidence"]
    
    overlay = ctx.tier2.overlay if ctx.tier2.overlay else OptionsOverlay()
    if overlay.can_reduce_tranche:
        daily_tranche_pct = round(daily_tranche_pct * overlay.tranche_multiplier, 4)
        cooldown_days = max(cooldown_days, overlay.delay_days)
        confidence = _weaken_confidence(confidence, overlay.confidence)

    explanation = _build_explanation(
        ctx.signal, ctx.tier1, ctx.tier2, ctx.tier1.score + ctx.tier2.adjustment,
        ctx.structural_regime, ctx.tactical_state, ctx.allocation_state,
        daily_tranche_pct, profile["max_total_add_pct"], cooldown_days, confidence
    )

    return SignalResult(
        date=ctx.market_date,
        price=ctx.price,
        signal=ctx.signal,
        final_score=ctx.tier1.score + ctx.tier2.adjustment,
        tier1=ctx.tier1,
        tier2=ctx.tier2,
        explanation=explanation,
        pe_source=ctx.tier1.pe_source,
        erp=ctx.erp_val,
        allocation_state=ctx.allocation_state,
        daily_tranche_pct=daily_tranche_pct,
        max_total_add_pct=profile["max_total_add_pct"],
        cooldown_days=cooldown_days,
        required_persistence_days=profile["required_persistence_days"],
        confidence=confidence,
        logic_trace=ctx.trace
    )

# ── Pipeline Steps ───────────────────────────────────────────────────────────

def _step_structural_regime(ctx: DecisionContext) -> DecisionContext:
    regime = assess_structural_regime(ctx.credit_spread, ctx.erp_val)
    trace_node = {
        "step": "structural_regime",
        "decision": regime,
        "reason": f"Regime identified as {regime}",
        "evidence": {"spread": ctx.credit_spread, "erp": ctx.erp_val}
    }
    return _update_ctx(ctx, structural_regime=regime, trace=ctx.trace + [trace_node])

def _step_tactical_state(ctx: DecisionContext) -> DecisionContext:
    t1 = ctx.tier1
    state = "CALM"
    if t1.descent_velocity == "PANIC":
        state = "PANIC"
    elif t1.capitulation_score >= 30 and t1.stress_score >= 20:
        state = "CAPITULATION"
    elif t1.descent_velocity == "GRIND" or (
        t1.persistence_score >= 20 and t1.stress_score >= 20
    ):
        state = "PERSISTENT_STRESS"
    elif t1.stress_score >= 20:
        state = "STRESS"
        
    trace_node = {
        "step": "tactical_state",
        "decision": state,
        "reason": f"Tactical state identified as {state}",
        "evidence": {
            "score": t1.score, 
            "stress": t1.stress_score, 
            "capitulation": t1.capitulation_score,
            "velocity": t1.descent_velocity
        }
    }
    return _update_ctx(ctx, tactical_state=state, trace=ctx.trace + [trace_node])

def _step_allocation_policy(ctx: DecisionContext) -> DecisionContext:
    s = ctx.structural_regime
    t = ctx.tactical_state
    
    res = AllocationState.BASE_DCA
    reason = "Default calibration"
    
    if s == "CRISIS":
        res, reason = AllocationState.RISK_CONTAINMENT, "Structural CRISIS forces risk containment"
    elif s == "EUPHORIC":
        res, reason = AllocationState.PAUSE_CHASING, "Structural EUPHORIA forces pause chasing"
    elif s in {"TRANSITION_STRESS", "RICH_TIGHTENING"}:
        if t == "PANIC":
            res, reason = AllocationState.RISK_CONTAINMENT, f"Tactical PANIC in {s} regime"
        elif t == "CAPITULATION":
            res, reason = AllocationState.SLOW_ACCUMULATE, f"Tactical CAPITULATION capped by {s} regime"
        elif t in {"STRESS", "PERSISTENT_STRESS"}:
            res, reason = AllocationState.SLOW_ACCUMULATE, f"Tactical STRESS in {s} regime"
        else:
            res, reason = AllocationState.BASE_DCA, f"Tactical CALM in {s} regime"
    else:
        # NEUTRAL regime
        if t == "PANIC":
            res, reason = AllocationState.RISK_CONTAINMENT, "Tactical PANIC in NEUTRAL regime"
        elif t == "CAPITULATION":
            res, reason = AllocationState.FAST_ACCUMULATE, "Tactical CAPITULATION in NEUTRAL regime allows acceleration"
        elif t in {"STRESS", "PERSISTENT_STRESS"}:
            res, reason = AllocationState.SLOW_ACCUMULATE, "Tactical STRESS in NEUTRAL regime"
        else:
            res, reason = AllocationState.BASE_DCA, "Standard calibration in NEUTRAL regime"

    trace_node = {
        "step": "allocation_policy",
        "decision": res.value,
        "reason": reason,
        "evidence": {"regime": s, "tactical": t}
    }
    return _update_ctx(ctx, allocation_state=res, trace=ctx.trace + [trace_node])

def _step_overlay_refinement(ctx: DecisionContext) -> DecisionContext:
    overlay = ctx.tier2.overlay if ctx.tier2.overlay else OptionsOverlay()
    score = ctx.tier1.score + ctx.tier2.adjustment
    
    # Map allocation to base signal
    sig = Signal.NO_SIGNAL
    if ctx.allocation_state == AllocationState.SLOW_ACCUMULATE:
        sig = Signal.WATCH
    elif ctx.allocation_state == AllocationState.FAST_ACCUMULATE:
        sig = Signal.TRIGGERED
        
    reason = "Signal derived from allocation state"
    
    # Allow upgrade if overlay permits
    if not overlay.cannot_upgrade_structural_state:
        if score >= TRIGGERED_THRESHOLD:
            sig = Signal.TRIGGERED
            reason = "Score-based upgrade allowed by overlay"
        elif score >= WATCH_THRESHOLD:
            sig = Signal.WATCH
            reason = "Score-based upgrade allowed by overlay"
            
    # Apply allocation cap
    cap = _MAX_SIGNAL_BY_ALLOCATION[ctx.allocation_state]
    if _SIGNAL_RANK[sig] > _SIGNAL_RANK[cap]:
        sig = cap
        reason = f"Signal capped by allocation state: {ctx.allocation_state.value}"
        
    # Extra caution rule
    if overlay.can_reduce_tranche and sig == Signal.TRIGGERED:
        sig = Signal.WATCH
        reason = "Downgraded to WATCH due to overlay caution"

    trace_node = {
        "step": "overlay_refinement",
        "decision": sig.value,
        "reason": reason,
        "evidence": {"final_score": score, "cap": cap.value, "veto": overlay.cannot_upgrade_structural_state}
    }
    return _update_ctx(ctx, signal=sig, trace=ctx.trace + [trace_node])

def _step_finalize(ctx: DecisionContext) -> DecisionContext:
    sig = ctx.signal
    reason = "Final result consolidated"
    
    # Greedy override
    if (
        sig == Signal.NO_SIGNAL
        and ctx.tier1.fear_greed.value > 75
        and ctx.tier1.score < 10
        and ctx.ma50 is not None
        and ctx.price > 1.06 * ctx.ma50
    ):
        sig = Signal.GREEDY
        reason = "GREEDY sentiment override"
        
    # Divergence upgrade
    has_major_div = (
        ctx.tier1.divergence_flags.get("price_revision") or
        ctx.tier1.divergence_flags.get("price_breadth") or
        ctx.tier1.divergence_flags.get("price_vix")
    )
    if sig == Signal.TRIGGERED and has_major_div:
        sig = Signal.STRONG_BUY
        reason = "Divergence confirmation upgrade"
        
    # Re-cap for safety
    cap = _MAX_SIGNAL_BY_ALLOCATION[ctx.allocation_state]
    if sig != Signal.GREEDY and _SIGNAL_RANK[sig] > _SIGNAL_RANK[cap]:
        sig = cap

    trace_node = {
        "step": "finalize",
        "decision": sig.value,
        "reason": reason,
        "evidence": {"greedy": (sig == Signal.GREEDY), "div_upgrade": has_major_div}
    }
    return _update_ctx(ctx, signal=sig, trace=ctx.trace + [trace_node])

# ── Helpers ──────────────────────────────────────────────────────────────────

def _update_ctx(ctx: DecisionContext, **kwargs) -> DecisionContext:
    """Helper for functional update of DecisionContext."""
    from dataclasses import replace
    return replace(ctx, **kwargs)

def _weaken_confidence(base: str, overlay: str) -> str:
    base_rank = _CONFIDENCE_ORDER.get(base, 1)
    overlay_rank = _CONFIDENCE_ORDER.get(overlay, base_rank)
    weakest_rank = min(base_rank, overlay_rank)
    for label, rank in _CONFIDENCE_ORDER.items():
        if rank == weakest_rank:
            return label
    return base

def _build_explanation(
    signal: Signal, tier1: Tier1Result, tier2: Tier2Result, final_score: int,
    structural_regime: str, tactical_state: str, allocation_state: AllocationState,
    daily_tranche_pct: float, max_total_add_pct: float, cooldown_days: int, confidence: str,
) -> str:
    """Preserve original Chinese explanation building logic."""
    parts: list[str] = []
    t1_score = tier1.score
    if t1_score >= 60:
        parts.append(f"Tier 1 多数信号达到触发级别（得分 {t1_score}/100）")
    elif t1_score >= 40:
        parts.append(f"Tier 1 部分信号处于观察区间（得分 {t1_score}/100）")
    else:
        parts.append(f"Tier 1 信号尚未进入关注区域（得分 {t1_score}/100）")

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
            if tier2.put_wall is not None:
                pct = (tier2.put_wall_distance_pct or 0) * 100
                if pct < 0:
                    parts.append(f"价格正处于 Put Wall（${tier2.put_wall}）回撤缓冲区 ({pct:.1f}%)，支撑面临考验")
                else:
                    parts.append(f"价格站在 Put Wall（${tier2.put_wall}）上方 {pct:.1f}%，支撑确认有效")
            elif tier2.poc is not None:
                parts.append(f"价格处于 Volume POC (${tier2.poc:.2f}) 筹码密集支撑区，结构性买盘显著")
        else:
            parts.append("当前价格距 Put Wall 较远，期权支撑结构为中性")

    if not is_pivot and cw is not None:
        pct = (tier2.call_wall_distance_pct or 0) * 100
        if tier2.upside_open:
            if tier2.call_wall_distance_pct > 0.5:
                parts.append(f"主要 Call Wall（${cw:.0f}）已被突破，上方空间打开")
            else:
                parts.append(f"上方 Call Wall（${cw:.0f}）距离 {pct:.1f}%，反弹空间充足")
        else:
            parts.append(f"上方 Call Wall（${cw:.0f}）距离仅 {pct:.1f}%，阻力较近")

    if tier2.gamma_flip is not None:
        if tier2.gamma_positive:
            parts.append(f"价格高于 Gamma Flip（{tier2.gamma_flip:.1f}），处于正 gamma 区域，波动趋于收敛")
        else:
            parts.append(f"价格低于 Gamma Flip（{tier2.gamma_flip:.1f}），处于负 gamma 区域，做市商对冲方向可能放大波动")

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
        parts.append(f"🔥 🌟 综合判断：技术与情绪共振，允许提高加仓速度。价格由于底背离（{div_str}）展现出逆势强度。")
    elif allocation_state == AllocationState.SLOW_ACCUMULATE:
        parts.append(f"综合判断：仅小幅试探，等待更多信号确认后再入场。{allocation_note}")
    elif allocation_state == AllocationState.BASE_DCA:
        parts.append(f"综合判断：维持基础定投，条件尚未满足。{allocation_note}")
    else:
        if tier1.descent_velocity == "GRIND":
            parts.append("阴跌预警：当前市场处于无量阴跌阶段，尚未出现恐慌性底背离，系统维持观望。")
        parts.append(f"综合判断：维持基础定投，条件尚未满足。{allocation_note}")

    return "。".join(parts) + "。"
