"""CLI output formatter for QQQ signal results."""
from __future__ import annotations

from src.models import Signal, SignalResult

# ANSI colours
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

_SIGNAL_STYLE = {
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
    print(f"{c(_CYAN)}║{r}")

    # ── Tier 1 ────────────────────────────────────────────────────────────
    t1 = result.tier1
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

    # ── Tier 1.5: 背离与估值 ──────────────────────────────────────────────
    val_b = getattr(t1, "valuation_bonus", 0)
    div_b = getattr(t1, "divergence_bonus", 0)
    fcf_b = getattr(t1, "fcf_bonus", 0)
    if val_b != 0 or div_b != 0 or fcf_b != 0:
        print(f"{c(_CYAN)}║{r}  {c(_BOLD)}── 附加分: 估值与背离红利 ─────────────────────{r}")
        if val_b > 0:
            print(f"{c(_CYAN)}║{r}  🟢 估值优势 (Forward PE): {c(_GREEN)}+{val_b}{r}")
        elif val_b < 0:
            print(f"{c(_CYAN)}║{r}  🔴 估值偏高 (Forward PE): {c(_RED)}{val_b}{r}")
            
        if fcf_b > 0:
            print(f"{c(_CYAN)}║{r}  💰 现金流深蹲 (FCF Yield): {c(_GREEN)}+{fcf_b}{r}")
            
        if div_b > 0:
            flags = getattr(t1, "divergence_flags", {})
            active_divs = [k.replace("price_", "") for k, v in flags.items() if v]
            print(f"{c(_CYAN)}║{r}  🔥 底部背离红利 ({', '.join(active_divs)}): {c(_GREEN)}+{div_b}{r}")
            
        print(f"{c(_CYAN)}║{r}")

    # ── Tier 2 ────────────────────────────────────────────────────────────
    t2 = result.tier2
    adj_color = c(_GREEN) if t2.adjustment > 0 else c(_RED)
    print(
        f"{c(_CYAN)}║{r}  {c(_BOLD)}── Tier 2: 期权墙确认 ─────────── "
        f"调整: {adj_color}{t2.adjustment:+d}{r}{c(_BOLD)} ────{r}"
    )

    pw_str = f"${t2.put_wall:.0f}" if t2.put_wall else "N/A"
    pw_dist = f"{t2.put_wall_distance_pct*100:.1f}%" if t2.put_wall_distance_pct is not None else "---"
    pw_flag = "支撑确认 ✓" if t2.support_confirmed else ("支撑破位 ✗" if t2.support_broken else "中性")
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
    score_color = c(_GREEN) if result.final_score >= 70 else (c(_YELLOW) if result.final_score >= 40 else c(_RED))
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
