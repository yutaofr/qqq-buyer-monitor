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
    
    current_triggered_thresh = 65 if is_prev_triggered else TRIGGERED_THRESHOLD
    current_watch_thresh = 35 if is_prev_watch else WATCH_THRESHOLD

    # ── Tier-0 Macro Veto ────────────────────────────────────────────────────
    is_macro_crisis = check_macro_regime(credit_spread)
    erp_regime = check_erp_regime(forward_pe, real_yield)
    
    if erp_regime == "Defense":
        current_triggered_thresh = 85
    elif erp_regime == "Aggressive" and current_triggered_thresh == TRIGGERED_THRESHOLD:
        current_triggered_thresh = 60 # Easier to trigger in a generational bottom

    # ── Three-state logic with hard vetoes ───────────────────────────────────
    # Macro crisis blocks all buys.
    # Put-wall hard veto blocks TRIGGERED only.
    if is_macro_crisis:
        signal = Signal.NO_SIGNAL
    elif final_score >= current_triggered_thresh and not tier2.support_broken:
        signal = Signal.TRIGGERED
    elif final_score >= current_watch_thresh:
        signal = Signal.WATCH
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
    if tier2.support_broken:
        next_wall_info = ""
        if tier2.next_put_wall is not None:
            pct = (tier2.next_put_wall_distance_pct or 0) * 100
            next_wall_info = f"，下档次级支撑: ${tier2.next_put_wall} (距离 {pct:.1f}%)"
            
        parts.append(
            f"价格已跌破 Put Wall（{tier2.put_wall}），做市商 delta 对冲压力可能加速下跌，"
            f"支撑结构失效{next_wall_info}，否决买入信号"
        )
    elif tier2.support_confirmed:
        pct = (tier2.put_wall_distance_pct or 0) * 100
        parts.append(
            f"价格站在 Put Wall（{tier2.put_wall}）上方 {pct:.1f}%，支撑确认有效"
        )
    else:
        parts.append("当前价格距 Put Wall 较远，期权支撑结构为中性")

    if tier2.call_wall is not None:
        pct = (tier2.call_wall_distance_pct or 0) * 100
        if tier2.upside_open:
            parts.append(f"上方 Call Wall（{tier2.call_wall}）距离 {pct:.1f}%，反弹空间充足")
        else:
            parts.append(f"上方 Call Wall（{tier2.call_wall}）距离仅 {pct:.1f}%，阻力较近")

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
        parts.append(f"综合判断：触发买点，进入分批加仓（5% 级回调）区间{hysteresis_note}。{erp_note}")
    elif signal == Signal.WATCH:
        parts.append(f"综合判断：进入观察区，等待更多信号确认后再入场{hysteresis_note}。{erp_note}")
    else:
        parts.append(f"综合判断：条件尚未满足，无买点信号{hysteresis_note}。{erp_note}")

    return "。".join(parts) + "。"
