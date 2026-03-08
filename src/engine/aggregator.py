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

TRIGGERED_THRESHOLD = 70
WATCH_THRESHOLD = 40


def aggregate(
    market_date: date,
    price: float,
    tier1: Tier1Result,
    tier2: Tier2Result,
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

    # ── Three-state logic with hard veto ─────────────────────────────────────
    # Put-wall hard veto: support_broken blocks TRIGGERED only.
    # PRD §4.3: "最高只能输出 '观察'", so WATCH is still valid when support_broken.
    if final_score >= TRIGGERED_THRESHOLD and not tier2.support_broken:
        signal = Signal.TRIGGERED
    elif final_score >= WATCH_THRESHOLD:
        signal = Signal.WATCH
    else:
        signal = Signal.NO_SIGNAL

    explanation = _build_explanation(signal, tier1, tier2, final_score)

    return SignalResult(
        date=market_date,
        price=price,
        signal=signal,
        final_score=final_score,
        tier1=tier1,
        tier2=tier2,
        explanation=explanation,
    )


def _build_explanation(
    signal: Signal,
    tier1: Tier1Result,
    tier2: Tier2Result,
    final_score: int,
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
        parts.append(
            f"价格已跌破 Put Wall（{tier2.put_wall}），做市商 delta 对冲压力可能加速下跌，"
            f"支撑结构失效，否决买入信号"
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
    if signal == Signal.TRIGGERED:
        parts.append("综合判断：触发买点，性价比较高。")
    elif signal == Signal.WATCH:
        parts.append("综合判断：进入观察区，等待更多信号确认后再入场。")
    else:
        parts.append("综合判断：条件尚未满足，无买点信号。")

    return "。".join(parts) + "。"
