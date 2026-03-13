"""
Signal aggregator: combines Tier-1 + Tier-2 into a final three-state signal.

Three states:
  TRIGGERED  – strong buy signal
  WATCH      – worth monitoring
  NO_SIGNAL  – conditions not met

Put-wall veto (hard veto):
  If support_broken is True, signal can never be TRIGGERED regardless
  of total score.  This enforces the delta-hedging cascade logic from PRD §4.3.
"""
from __future__ import annotations

from datetime import date

from src.models import Signal, SignalResult, Tier1Result, Tier2Result
from src.engine.tier0_macro import check_macro_regime, check_erp_regime

TRIGGERED_THRESHOLD = 70
WATCH_THRESHOLD = 40


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
    final_score = tier1.score + tier2.adjustment

    # ── Hysteresis / Schmitt Trigger Thresholds ──────────────────────────────
    is_prev_triggered = prev_signal == Signal.TRIGGERED
    is_prev_watch = prev_signal in (Signal.WATCH, Signal.TRIGGERED)
    
    # ── Dynamic Adaptive Thresholds (v4.5) ───────────────────────────────────
    regime = tier1.market_regime
    drawdown = tier1.drawdown_52w.value  # (High - Price) / High
    
    if regime == "QUIET":
        # Drawdown-Gated: Requires 0.5% dip to enter sensitive mode (45), else 67.
        base_trigger = 45 if drawdown >= 0.005 else 67
    elif regime == "NORMAL":
        base_trigger = 60
    else: # STORM
        base_trigger = 65

    # v5.0 Velocity Filter: If "GRIND", raise threshold (be harder to trigger)
    descent_v = tier1.descent_velocity
    if descent_v == "GRIND":
        base_trigger += 10
    elif descent_v == "PANIC":
        base_trigger -= 5

    current_triggered_thresh = (base_trigger - 5) if is_prev_triggered else base_trigger
    current_watch_thresh = 35 if is_prev_watch else WATCH_THRESHOLD

    # ── Tier-0 Macro Veto ────────────────────────────────────────────────────
    is_macro_crisis = check_macro_regime(credit_spread)
    erp_regime = check_erp_regime(forward_pe, real_yield)
    
    if erp_regime == "Defense":
        current_triggered_thresh = 85
    elif erp_regime == "Aggressive":
        current_triggered_thresh = min(current_triggered_thresh, 60)

    # ── Three-state logic with hard vetoes ───────────────────────────────────
    # Macro crisis blocks all buys.
    # Put-wall hard veto blocks TRIGGERED only.
    if is_macro_crisis:
        signal = Signal.NO_SIGNAL
    elif final_score >= current_triggered_thresh and not tier2.support_broken:
        signal = Signal.TRIGGERED
    elif final_score >= current_watch_thresh:
        signal = Signal.WATCH
    # v5.0: GREEDY / Profit Taking Signal
    elif (
        tier1.fear_greed.value > 75 
        and final_score < 10 
        and ma50 is not None and price > 1.06 * ma50
    ):
        signal = Signal.GREEDY
    else:
        signal = Signal.NO_SIGNAL

    # Upgrade to STRONG_BUY if any major Divergence exists and we are in TRIGGERED state
    # Major divergences: Revision (Fundamental), Breadth (Technical), or VIX (Technical)
    has_major_div = (
        tier1.divergence_flags.get("price_revision") or
        tier1.divergence_flags.get("price_breadth") or
        tier1.divergence_flags.get("price_vix")
    )
    
    if (
        signal == Signal.TRIGGERED 
        and not tier2.support_broken 
        and has_major_div
    ):
        signal = Signal.STRONG_BUY

    explanation = _build_explanation(
        signal, tier1, tier2, final_score,
        current_triggered_thresh, current_watch_thresh, is_macro_crisis, erp_regime
    )

    # Calculate final ERP value for reporting
    erp_val = None
    if forward_pe and real_yield and forward_pe > 0:
        earnings_yield = 1.0 / forward_pe
        erp_val = (earnings_yield * 100) - real_yield

    return SignalResult(
        date=market_date,
        price=price,
        signal=signal,
        final_score=final_score,
        tier1=tier1,
        tier2=tier2,
        explanation=explanation,
        pe_source=tier1.pe_source,
        erp=erp_val
    )


def _build_explanation(
    signal: Signal,
    tier1: Tier1Result,
    tier2: Tier2Result,
    final_score: int,
    trigger_thresh: int,
    watch_thresh: int,
    is_macro_crisis: bool = False,
    erp_regime: str = "Normal"
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
                f"支撑结构失效{next_wall_info}，否决买入信号"
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
    hysteresis_note = ""
    if trigger_thresh < TRIGGERED_THRESHOLD or watch_thresh < WATCH_THRESHOLD:
        hysteresis_note = "（已触发滞后干预机制，维持近期连贯状态）"
        
    erp_note = ""
    if erp_regime == "Defense":
        erp_note = " 🛡️ [防守模式]: 股权风险溢价极低，触发门槛大幅提高。"
    elif erp_regime == "Aggressive":
        erp_note = " 💎 [百年一遇]: 股权风险溢价极高，触发绝佳长线击球区！"

    if is_macro_crisis:
        parts.append("🚨 综合判断：虽然技术面可能提示加仓，但当前信用利差爆表，触发宏观流动性危机熔断，系统强制切断一切买入信号！")
    elif signal == Signal.STRONG_BUY:
        div_reasons = []
        if tier1.divergence_flags.get("price_revision"): div_reasons.append("基本面上修")
        if tier1.divergence_flags.get("price_breadth"): div_reasons.append("市场广度提升")
        if tier1.divergence_flags.get("price_vix"): div_reasons.append("恐慌情绪衰减")
        if tier1.divergence_flags.get("price_rsi"): div_reasons.append("动能底背离")
        
        div_str = " + ".join(div_reasons) if div_reasons else "多重背离确认"
        parts.append(
            f"🔥 🌟 综合判断：触发【强烈买入】(STRONG BUY) 核心信号！价格由于底背离（{div_str}）展现出罕见的逆势强度，是极佳的加仓点{hysteresis_note}。{erp_note}"
        )
    elif signal == Signal.TRIGGERED:
        vel_note = ""
        if tier1.descent_velocity == "PANIC": vel_note = "【恐慌放量】"
        parts.append(f"综合判断：{vel_note}触发买点，进入分批加仓（5% 级回调）区间{hysteresis_note}。{erp_note}")
    elif signal == Signal.WATCH:
        parts.append(f"综合判断：进入观察区，等待更多信号确认后再入场{hysteresis_note}。{erp_note}")
    elif signal == Signal.GREEDY:
        parts.append(f"🚨 🌟 综合判断：触发【贪婪警告】(GREEDY)！当前市场情绪极度过热（F&G: {tier1.fear_greed.value}），且价格涨幅过快。建议分批止盈，落袋为安，切勿追高。")
    else:
        if tier1.descent_velocity == "GRIND":
            parts.append("阴跌预警：当前市场处于无量阴跌阶段，尚未出现恐慌性底背离，系统维持观望。")
        parts.append(f"综合判断：条件尚未满足，无买点信号{hysteresis_note}。{erp_note}")

    return "。".join(parts) + "。"
