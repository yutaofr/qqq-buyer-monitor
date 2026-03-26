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


def is_v8_runtime_result(result: SignalResult) -> bool:
    """Return True when the v8 linear pipeline fields are populated."""
    return any(
        [
            result.risk_state is not None,
            result.deployment_state is not None,
            result.selected_candidate_id is not None,
            result.registry_version is not None,
            result.tier0_regime is not None,
            result.target_beta is not None,
            result.should_adjust is not None,
        ]
    )


def build_v8_explanation(result: SignalResult) -> str:
    """Build a concise v8 explanation without legacy amount-based wording."""
    tier0 = result.tier0_regime or "n/a"
    risk = result.risk_state.value if result.risk_state else "n/a"
    deploy = result.deployment_state.value if result.deployment_state else "n/a"
    candidate = result.selected_candidate_id or "n/a"
    registry = result.registry_version or "n/a"
    target_beta = result.target_beta if result.target_beta is not None else result.target_allocation.target_beta
    should_adjust = result.should_adjust if result.should_adjust is not None else False
    adjust_reason = result.rebalance_action.get("reason", "n/a")
    deploy_reason = result.deployment_action.get("reason", "n/a")
    t = result.target_allocation

    parts = [
        f"v8.1 线性流水线：Tier-0={tier0}",
        f"风险={risk}",
        f"候选={candidate}",
        f"registry={registry}",
        f"target_beta={target_beta:.2f}x",
        f"adjust={should_adjust}",
        f"reason={adjust_reason}",
        f"deploy={deploy}",
        f"deploy_reason={deploy_reason}",
        f"配比 QQQ={t.target_qqq_pct*100:.1f}%",
        f"QLD={t.target_qld_pct*100:.1f}%",
        f"Cash={t.target_cash_pct*100:.1f}%",
    ]
    return " | ".join(parts)



def _print_v7_sections(result: SignalResult, c) -> None:
    """Render the v8 recommendation summary in two clearly separated sections."""
    if not (result.registry_version or result.risk_state or result.deployment_state or result.selected_candidate_id):
        return

    tier0 = result.tier0_regime or "n/a"
    risk = result.risk_state.value if result.risk_state else "n/a"
    deploy = result.deployment_state.value if result.deployment_state else "n/a"
    candidate = result.selected_candidate_id or "n/a"
    registry = result.registry_version or "n/a"
    target_beta = result.target_beta if result.target_beta is not None else result.target_allocation.target_beta
    should_adjust = result.should_adjust
    if should_adjust is None:
        should_adjust = result.rebalance_action.get("should_adjust")
    adjust_reason = result.rebalance_action.get("reason", "n/a")
    deploy_mode = result.deployment_action.get("deploy_mode", "n/a")
    deploy_reason = result.deployment_action.get("reason", "n/a")

    print(f"\n{c(_BOLD)}风险评估与目标 Beta{c(_RESET)}")
    print(
        f"  分析:    Tier-0={tier0} | 风险状态={risk} | "
        f"候选={candidate} | registry={registry}"
    )
    print(
        "  推荐:    "
        f"target_beta={target_beta:.2f}x | adjust={should_adjust} | reason={adjust_reason}"
    )
    t = result.target_allocation
    print(
        "  配比:    "
        f"QQQ={t.target_qqq_pct*100:.1f}% | "
        f"QLD={t.target_qld_pct*100:.1f}% | "
        f"Cash={t.target_cash_pct*100:.1f}%"
    )
    print("  ⚠️ 以上为推荐建议，不代表自动执行。")

    print(f"{c(_BOLD)}增量入场节奏推荐{c(_RESET)}")
    print(f"  分析:    deployment={deploy} | Tier-0 soft ceiling={tier0}")
    print(f"  推荐:    mode={deploy_mode} | reason={deploy_reason}")
    print("  ⚠️ 以上为推荐建议，不代表自动执行。")


def print_signal(
    result: SignalResult,
    use_color: bool = True,
    compact: bool = False,
    consecutive_days: int = 1,
) -> None:
    """Print a formatted signal summary to stdout."""
    c = lambda code: code if use_color else ""  # noqa: E731
    r = c(_RESET)
    runtime_version = "v8.1"

    t1 = result.tier1
    color, label = _ALLOCATION_STYLE[result.allocation_state]

    if compact:
        msg = (
            f"{c(_BOLD)}[{result.date}]{r} "
            f"{c(color)}{label}{r} | "
            f"Price: ${result.price:.2f} | "
            f"Score: {result.final_score} | "
            f"({consecutive_days}d) [报告折叠]"
        )
        print(msg)
        return

    sig_color, sig_label = _SIGNAL_STYLE[result.signal]

    print(f"\n{c(_BOLD)}=== QQQ BUY-SIGNAL MONITOR ({runtime_version}) ==={r}")
    print(f"Date:      {result.date}")
    print(f"Price:     ${result.price:.2f}")
    print(f"Signal:    {c(sig_color)}{sig_label}{r} (Score: {result.final_score}/100)")
    v8_runtime = is_v8_runtime_result(result)
    if v8_runtime:
        _print_v7_sections(result, c)
    else:
        print(f"Policy:    {c(color)}{label}{r}")
        print(f"Action:    {c(_BOLD)}{_allocation_label(result.allocation_state)}{r}")
        _print_v7_sections(result, c)

    # v6.4 Search Rationale from Logic Trace
    search_node = next((n for n in result.logic_trace if n.get("step") == "search"), None)
    if search_node:
        print(f"Search:    {search_node['decision']} ({search_node['reason']})")
    
    # Details summary
    if not v8_runtime:
        print(f"Details:   单日加仓: {result.daily_tranche_pct:.0%}, 滚动上限: {result.max_total_add_pct:.1f}x, 置信度: {result.confidence}")

    # v8.1 Strategic Portfolio Alignment
    t = result.target_allocation
    print(f"Target:    Cash={t.target_cash_pct*100:.1f}%, QQQ={t.target_qqq_pct*100:.1f}%, QLD={t.target_qld_pct*100:.1f}% | Beta={t.target_beta:.2f}x")

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
    print(build_v8_explanation(result) if v8_runtime else result.explanation)
    print(f"{c(_BOLD)}---{r}")
