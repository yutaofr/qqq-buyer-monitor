"""CLI output formatter for QQQ signal results."""
from __future__ import annotations

from src.models import Signal, SignalResult

# ANSI colours
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_PURPLE = "\033[95m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

_SIGNAL_STYLE = {
    Signal.STRONG_BUY: (_PURPLE, "🌟 强烈买入 (STRONG BUY)"),
    Signal.TRIGGERED: (_GREEN, "✅ 触发 (TRIGGERED)"),
    Signal.WATCH: (_YELLOW, "👀 观察 (WATCH)"),
    Signal.NO_SIGNAL: (_RED, "❌ 未触发 (NO_SIGNAL)"),
}

_BAR_FULL = "■"
_BAR_EMPTY = "░"


def _bar(points: int, max_pts: int = 20, width: int = 5) -> str:
    filled = round(points / max_pts * width)
    return _BAR_FULL * filled + _BAR_EMPTY * (width - filled)


def _fmt_flag(flag: bool) -> str:
    return "✓" if flag else "✗"


def print_signal(
    result: SignalResult,
    use_color: bool = True,
    compact: bool = False,
    consecutive_days: int = 1,
) -> None:
    """Print a formatted signal summary to stdout."""
    c = lambda code: code if use_color else ""  # noqa: E731
    r = c(_RESET)

    color, label = _SIGNAL_STYLE[result.signal]
    header_label = f"{c(color)}{c(_BOLD)}{label}{r}"

    width = 62
    border = "═" * width

    print(f"\n{c(_CYAN)}╔{border}╗{r}")
    print(
        f"{c(_CYAN)}║{r}  {c(_BOLD)}QQQ 买点信号监控{r}"
        f"  │  {result.date}  │  {header_label}"
    )
    print(f"{c(_CYAN)}╠{border}╣{r}")
    
    if compact:
        msg = f"🔕 【报告折叠】连续第 {consecutive_days} 天 {label}。当前得分 {result.final_score}，收盘价 ${result.price:.2f}。为防信号疲劳，已折叠详细输出。"
        print(f"{c(_CYAN)}║{r}  {msg}")
        print(f"{c(_CYAN)}╚{border}╝{r}\n")
        return

    print(f"{c(_CYAN)}║{r}  QQQ 收盘价: {c(_BOLD)}${result.price:.2f}{r}")
    
    t1 = result.tier1
    pe_str = f"PE: {t1.trailing_pe:.1f}" if t1.trailing_pe else "PE: N/A"
    fpe_str = f"Forward PE: {t1.forward_pe:.1f}" if t1.forward_pe else "Forward PE: N/A"
    source_tag = f" ({c(_DIM)}来源: {result.pe_source}{r})"
    print(f"{c(_CYAN)}║{r}  {pe_str}  │  {fpe_str} {source_tag}")
    
    if result.erp is not None:
        erp_color = c(_GREEN) if result.erp > 1.0 else (c(_RED) if result.erp < 0 else "")
        print(f"{c(_CYAN)}║{r}  股权风险溢价 (ERP): {erp_color}{result.erp:.2f}%{r}")
    
    print(f"{c(_CYAN)}║{r}")
    print(
        f"{c(_CYAN)}║{r}  {c(_BOLD)}── Tier 1: 现货与情绪 ─────────────── 得分: {t1.score}/100 ──{r}"
    )

    def t1_row(detail, label: str) -> str:
        pts = detail.points
        bar = _bar(pts)
        flag = _fmt_flag(detail.triggered_half)
        color_pts = c(_GREEN) if pts >= 20 else (c(_YELLOW) if pts >= 10 else c(_RED))
        return (
            f"{c(_CYAN)}║{r}  [{bar}] {label}: {detail.value}"
            f"  {flag}  {color_pts}{pts:+d}{r}"
        )

    print(t1_row(t1.drawdown_52w, f"52周回撤 {t1.drawdown_52w.value*100:.1f}%"))
    print(t1_row(t1.ma200_deviation, f"MA200偏离 {t1.ma200_deviation.value*100:.1f}%"))
    print(t1_row(t1.vix, f"VIX {t1.vix.value:.1f}"))
    print(t1_row(t1.fear_greed, f"F&G {int(t1.fear_greed.value)}"))
    print(t1_row(t1.breadth, f"市场广度 涨跌比 {t1.breadth.value:.2f}"))

    print(f"{c(_CYAN)}║{r}")

    # ── Tier 1.5: 宏观环境与背离红利 ───────────────────────────────────────────────
    print(f"{c(_CYAN)}║{r}  {c(_BOLD)}── Tier 1.5: 环境判别与背离 ─────────────────────────{r}")
    
    val_b = t1.valuation_bonus
    fcf_b = t1.fcf_bonus
    div_b = t1.divergence_bonus

    # 1. Macro & Valuation Details
    ry_str = f"{t1.real_yield:.2f}%" if t1.real_yield else "N/A"
    fpe = t1.forward_pe or 0.0
    fcf_y = t1.fcf_yield or 0.0
    
    print(f"{c(_CYAN)}║{r}  实际利率 (TIPS): {ry_str}  │ 远期 PE: {fpe:.1f} → {val_b:+d}")
    print(f"{c(_CYAN)}║{r}  现金收益 (FCF): {fcf_y*100:.1f}%  → {fcf_b:+d}")
    
    # 2. Divergence Checks
    flags = t1.divergence_flags
    def div_row(key, label):
        status = "🔥 [触发]" if flags.get(key) else "⚪ [未见]"
        return f"{c(_CYAN)}║{r}  {status} {label}"

    print(div_row("price_breadth", "市场广度背离"))
    print(div_row("price_vix", "恐慌指数背离"))
    print(div_row("price_rsi", "动能 RSI 背离"))
    print(div_row("price_revision", "盈利预期背离"))
    print(f"{c(_CYAN)}║{r}  背离红利总得分: {c(_GREEN)}+{div_b}{r}")
    
    # 3. Concentration Risk
    nc = t1.ndx_concentration * 100
    np = t1.concentration_penalty
    if np < 0:
        print(f"{c(_CYAN)}║{r}  纳指抱团预警: QQQ 领先 QQEW {nc:.1f}%  → {c(_RED)}{np}{r}")
    else:
        print(f"{c(_CYAN)}║{r}  纳指抱团预警: 内部结构健康 (差值 {nc:.1f}%)  → +0")
        
    print(f"{c(_CYAN)}║{r}")

    # ── Tier 2 ────────────────────────────────────────────────────────────
    t2 = result.tier2
    adj_color = c(_GREEN) if t2.adjustment > 0 else c(_RED)
    print(
        f"{c(_CYAN)}║{r}  {c(_BOLD)}── Tier 2: 期权墙确认 ─────────── "
        f"调整: {adj_color}{t2.adjustment:+d}{r}{c(_BOLD)} ────{r}"
    )

    pw_str = f"${t2.put_wall:.0f}" if t2.put_wall else "N/A"
    pw_str = f"${t2.put_wall:.0f}" if t2.put_wall else "N/A"
    pw_dist = f"{t2.put_wall_distance_pct*100:.1f}%" if t2.put_wall_distance_pct is not None else "---"
    pw_flag = "支撑确认 ✓" if t2.support_confirmed else ("支撑破位 ✗" if t2.support_broken else "中性")
    
    if t2.support_broken and t2.next_put_wall is not None:
        npw_dist = f"{t2.next_put_wall_distance_pct*100:.1f}%" if t2.next_put_wall_distance_pct is not None else "---"
        pw_flag += f" (下档次级支撑: ${t2.next_put_wall:.0f}，距离 {npw_dist})"
        
    print(f"{c(_CYAN)}║{r}  Put Wall: {pw_str}  │ 距离 {pw_dist}  → {pw_flag}")

    cw_str = f"${t2.call_wall:.0f}" if t2.call_wall else "N/A"
    cw_dist = f"{t2.call_wall_distance_pct*100:.1f}%" if t2.call_wall_distance_pct is not None else "---"
    cw_flag = "空间充足 ✓" if t2.upside_open else "阻力较近 ✗"
    print(f"{c(_CYAN)}║{r}  Call Wall: {cw_str}  │ 距离 {cw_dist}  → {cw_flag}")

    gf_str = f"${t2.gamma_flip:.1f}" if t2.gamma_flip else "N/A"
    gf_flag = "正 gamma ✓" if t2.gamma_positive else "负 gamma ✗"
    print(f"{c(_CYAN)}║{r}  Gamma Flip: {gf_str}  │ {gf_flag}  (来源: {t2.gamma_source})")

    print(f"{c(_CYAN)}║{r}")

    # ── Final ─────────────────────────────────────────────────────────────
    sig_code = result.signal
    score_p = result.final_score
    if sig_code == Signal.STRONG_BUY:
        score_color = c(_PURPLE)
    elif score_p >= 70:
        score_color = c(_GREEN)
    elif score_p >= 40:
        score_color = c(_YELLOW)
    else:
        score_color = c(_RED)

    print(
        f"{c(_CYAN)}║{r}  {c(_BOLD)}── 最终得分: {score_color}{result.final_score}{r}{c(_BOLD)}"
        f"  状态: {header_label} ────{r}"
    )

    # Wrap explanation at ~55 chars
    explanation = result.explanation
    words = explanation.split("。")
    for sentence in words:
        if sentence.strip():
            print(f"{c(_CYAN)}║{r}  {sentence.strip()}。")

    print(f"{c(_CYAN)}╚{border}╝{r}\n")
