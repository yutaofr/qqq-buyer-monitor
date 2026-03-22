"""CLI output formatting for QQQ monitor."""
from __future__ import annotations

from typing import Any

from src.models import AllocationState, Signal, SignalResult

# ANSI color codes
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BLUE = "\033[94m"
_CYAN = "\033[96m"
_RESET = "\033[0m"

_SIGNAL_STYLE = {
    Signal.STRONG_BUY: (_GREEN + _BOLD, "STRONG BUY"),
    Signal.TRIGGERED: (_GREEN, "TRIGGERED"),
    Signal.WATCH: (_CYAN, "WATCH"),
    Signal.NO_SIGNAL: (_DIM, "NO SIGNAL"),
    Signal.GREEDY: (_RED + _BOLD, "GREEDY WARNING"),
}

_ALLOCATION_STYLE = {
    AllocationState.PAUSE_CHASING: (_YELLOW, "暂停追高 (PAUSE)"),
    AllocationState.BASE_DCA: (_BLUE, "基础定投 (BASE DCA)"),
    AllocationState.SLOW_ACCUMULATE: (_CYAN, "小幅加仓 (SLOW)"),
    AllocationState.FAST_ACCUMULATE: (_GREEN + _BOLD, "加速买入 (FAST)"),
    AllocationState.RISK_CONTAINMENT: (_RED, "风险控制 (CONTAIN)"),
    # v6.2 Defensive Styles
    AllocationState.WATCH_DEFENSE: (_YELLOW + _BOLD, "防御观察 (WATCH DEF)"),
    AllocationState.DELEVERAGE: (_RED, "降低杠杆 (DELEVERAGE)"),
    AllocationState.CASH_FLIGHT: (_RED + _BOLD, "现金避险 (CASH FLIGHT)"),
}


def _allocation_label(state: AllocationState) -> str:
    if state == AllocationState.PAUSE_CHASING:
        return "暂停追高"
    if state == AllocationState.BASE_DCA:
        return "维持基础定投"
    if state == AllocationState.SLOW_ACCUMULATE:
        return "允许小幅加仓"
    if state == AllocationState.FAST_ACCUMULATE:
        return "允许提高加仓速度"
    if state == AllocationState.RISK_CONTAINMENT:
        return "进入风险控制"
    # v6.2 Labels
    if state == AllocationState.WATCH_DEFENSE:
        return "触发防御观察"
    if state == AllocationState.DELEVERAGE:
        return "执行减仓降杠杆"
    if state == AllocationState.CASH_FLIGHT:
        return "执行最高级避险"
    return "维持现状"


def print_signal(
    result: SignalResult,
    use_color: bool = True,
    compact: bool = False,
    consecutive_days: int = 1,
) -> None:
    """Print a formatted signal summary to stdout."""
    c = lambda code: code if use_color else ""  # noqa: E731
    r = c(_RESET)

    t1 = result.tier1
    color, label = _ALLOCATION_STYLE[result.allocation_state]

    if compact:
        msg = (
            f"{c(_BOLD)}[{result.date}]{r} "
            f"{c(color)}{label}{r} | "
            f"Price: ${result.price:.2f} | "
            f"Score: {result.final_score} | "
            f"({consecutive_days}d)"
        )
        print(msg)
        return

    sig_color, sig_label = _SIGNAL_STYLE[result.signal]

    print(f"\n{c(_BOLD)}=== QQQ BUY-SIGNAL MONITOR (v6.3) ==={r}")
    print(f"Date:      {result.date}")
    print(f"Price:     ${result.price:.2f}")
    print(f"Signal:    {c(sig_color)}{sig_label}{r} (Score: {result.final_score}/100)")
    print(f"Policy:    {c(color)}{label}{r}")
    print(f"Action:    {c(_BOLD)}{_allocation_label(result.allocation_state)}{r}")
    
    # Details summary
    print(f"Details:   单日加仓: {result.daily_tranche_pct:.0%}, 滚动上限: {result.max_total_add_pct:.1f}x, 置信度: {result.confidence}")
    
    # v6.3 Strategic Portfolio Alignment
    p = result.current_portfolio
    t = result.target_allocation
    if p and (p.current_cash_pct > 0 or p.qqq_pct > 0 or p.qld_pct > 0):
        print(f"Reality:   Cash={p.current_cash_pct*100:.1f}%, QQQ={p.qqq_pct*100:.1f}%, QLD={p.qld_pct*100:.1f}% | Exp={result.effective_exposure:.2f}x")
        print(f"Ideal:     Cash={t.target_cash_pct*100:.1f}%, QQQ={t.target_qqq_pct*100:.1f}%, QLD={t.target_qld_pct*100:.1f}% | Beta={t.target_beta:.2f}x")
    elif result.target_cash_pct > 0:
        # Fallback for older records
        old_p = result.portfolio
        print(f"Portfolio: Cash={old_p.current_cash_pct:.1f}% -> Target={result.target_cash_pct:.1f}% | Lev={old_p.leverage_ratio:.1f}x")

    # Data Quality Summary (v6.2: Logic corrected to match data_quality.py structure)
    if result.data_quality:
        total = len(result.data_quality)
        available = sum(1 for f in result.data_quality.values() if f.get('usable'))
        print(f"Quality:   数据质量: {available}/{total} 可用")

    if consecutive_days > 1:
        print(f"Status:    Confirmed for {consecutive_days} consecutive days")

    print(f"\n{c(_DIM)}Tier-1 Components:{r}")
    if t1.drawdown_52w:
        print(f"  - Drawdown:   {t1.drawdown_52w.value*100:5.1f}% ({t1.drawdown_52w.points:2d} pts)")
    if t1.ma200_deviation:
        print(f"  - MA200 Dev:  {t1.ma200_deviation.value*100:5.1f}% ({t1.ma200_deviation.points:2d} pts)")
    if t1.vix:
        print(f"  - VIX:        {t1.vix.value:5.1f}      ({t1.vix.points:2d} pts)")
    if t1.fear_greed:
        print(f"  - Fear&Greed: {t1.fear_greed.value:5.1f}      ({t1.fear_greed.points:2d} pts)")
    if t1.breadth:
        print(f"  - Breadth:    {t1.breadth.value*100:5.1f}% ({t1.breadth.points:2d} pts)")

    print(f"\n{c(_CYAN)}Rationale:{r}")
    print(result.explanation)
    print(f"{c(_BOLD)}---{r}")
