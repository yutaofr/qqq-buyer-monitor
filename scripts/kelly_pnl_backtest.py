"""
Kelly PnL Backtest: True Kelly vs Pseudo Kelly.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.kelly_ab_comparison import _compute_all_variant_decisions, _load_trace


def _compute_pnl_curve(
    trace: pd.DataFrame,
    beta_col: str,
    transaction_cost: float = 0.0010,
) -> pd.Series:
    """
    模拟净值曲线。

    使用 target_beta 作为仓位暴露比例：
      strategy_return_t = beta_{t-1} * qqq_return_t
      （T日收盘后决定的仓位，吃T+1日的收益）
    """
    n = len(trace)
    navs = np.ones(n, dtype=float)
    if n == 0:
        return pd.Series([], dtype=float)

    closes = trace["close"].values
    betas = trace[beta_col].values

    current_nav = 1.0
    prev_close = closes[0]
    prev_beta = betas[0]

    for i in range(1, n):
        close_t = closes[i]
        beta_t_minus_1 = prev_beta  # yesterday's signal drives today's exposure

        daily_return = 0.0
        if not np.isnan(close_t) and not np.isnan(prev_close) and prev_close > 0.0:
            daily_return = close_t / prev_close - 1.0

        # Full capital deployed at beta exposure
        exposure = max(0.0, min(2.0, beta_t_minus_1))  # cap at 2x leverage
        pnl_contribution = exposure * daily_return

        # Transaction cost only on rebalance (beta change > 5%)
        cost_t = 0.0
        if abs(betas[i] - prev_beta) > 0.05:
            cost_t = transaction_cost * abs(betas[i] - prev_beta)

        current_nav = current_nav * (1.0 + pnl_contribution - cost_t)
        current_nav = max(0.0, current_nav)
        navs[i] = current_nav

        if not np.isnan(close_t):
            prev_close = close_t
        prev_beta = betas[i]

    return pd.Series(navs, index=trace.index)


def _compute_performance_metrics(
    nav_series: pd.Series,
    risk_free_rate: float = 0.02,
) -> dict:
    """
    从净值序列计算量化性能指标。
    """
    if len(nav_series) < 2:
        return {
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "calmar": 0.0,
            "total_return": 0.0,
        }

    nav_values = nav_series.values
    nav_init = nav_values[0]
    nav_final = nav_values[-1]

    n_days = len(nav_series) - 1
    if nav_init > 0.0 and n_days > 0:
        cagr = (nav_final / nav_init) ** (252 / n_days) - 1.0
        total_return = (nav_final / nav_init) - 1.0
    else:
        cagr = 0.0
        total_return = 0.0

    daily_returns = nav_series.pct_change().dropna().values

    # Max Drawdown
    # Fix for constant nav arrays or dividing by zero
    running_max = np.maximum.accumulate(nav_values)
    # mask 0 to safely divide
    safe_running_max = np.where(running_max == 0, 1e-8, running_max)
    drawdowns = (nav_values - running_max) / safe_running_max
    max_drawdown = float(np.min(drawdowns))

    # Sharpe
    daily_excess = daily_returns - (risk_free_rate / 252.0)
    std_return = np.std(daily_returns, ddof=1) if len(daily_returns) > 1 else 0.0

    sharpe = 0.0
    if std_return > 1e-8:
        sharpe = float(np.mean(daily_excess) / std_return * np.sqrt(252))

    # Sortino
    downside_returns = daily_returns[daily_returns < 0]
    std_downside = np.std(downside_returns, ddof=1) if len(downside_returns) > 1 else 0.0

    sortino = 0.0
    if std_downside > 1e-8:
        sortino = float(np.mean(daily_excess) / std_downside * np.sqrt(252))

    # Calmar
    calmar = 0.0
    if abs(max_drawdown) > 1e-8:
        calmar = float(cagr / abs(max_drawdown))

    return {
        "cagr": float(cagr),
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "total_return": float(total_return),
    }


def main(argv=None):
    """
    主流程:
    1. 加载 trace
    2. 计算 True Kelly 变体乘数
    3. 调用 _compute_pnl_curve
    4. 调用 _compute_performance_metrics
    5. 输出报告
    """
    parser = argparse.ArgumentParser(description="Kelly PnL Backtest")
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--regime-audit", default="src/engine/v11/resources/regime_audit.json")
    parser.add_argument("--output-dir", default="artifacts/kelly_ab")
    args = parser.parse_args(argv)

    with open(args.regime_audit) as f:
        audit = json.load(f)
    regime_sharpes = dict(audit["regime_sharpes"])

    trace = _load_trace(args.trace_path)
    trace = _compute_all_variant_decisions(trace, regime_sharpes)

    target_kellies = ["half_erp_low", "half_erp_mid", "half_erp_high"]
    variants = target_kellies + ["pseudo_kelly"]

    # All variants use target_beta as the direct exposure signal.
    # The only column that matters for PnL is the beta (position sizing),
    # not the deployment_multiplier (pacing envelope).
    # For pseudo_kelly, use the engine's target_beta directly.
    # For true kelly variants, we approximate beta from kelly_fraction.
    for vid in target_kellies:
        frac_col = f"{vid}_fraction"
        # Kelly fraction -> beta: fraction is [0,1], map to beta [0.5, 1.2]
        trace[f"{vid}_beta"] = 0.5 + trace[frac_col].clip(0, 1) * 0.7

    metrics_all = {}
    pnl_curves = {}

    for v in variants:
        if v == "pseudo_kelly":
            beta_col = "target_beta"
        else:
            beta_col = f"{v}_beta"

        nav_series = _compute_pnl_curve(
            trace, beta_col, transaction_cost=0.0010
        )
        pnl_curves[v] = nav_series
        metrics_all[v] = _compute_performance_metrics(nav_series, risk_free_rate=0.02)

    pnl_curves_df = pd.DataFrame(pnl_curves)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "pnl_summary.json").write_text(json.dumps(metrics_all, indent=2))
    pnl_curves_df.to_csv(output_dir / "pnl_curves.csv")

    report_lines = ["# True Kelly PnL Backtest Report\n"]
    report_lines.append("## Performance Summary\n")
    report_lines.append("| Variant | CAGR | Max DD | Sharpe | Sortino | Calmar | Total Return |")
    report_lines.append("|---------|------|--------|--------|---------|--------|--------------|")

    best_tk_cagr = -999.0
    best_tk_vid = ""
    for v in variants:
        m = metrics_all[v]
        row = f"| {v} | {m['cagr'] * 100:.2f}% | {m['max_drawdown'] * 100:.2f}% | {m['sharpe']:.2f} | {m['sortino']:.2f} | {m['calmar']:.2f} | {m['total_return'] * 100:.2f}% |"
        report_lines.append(row)
        if v != "pseudo_kelly" and m["cagr"] > best_tk_cagr:
            best_tk_cagr = m["cagr"]
            best_tk_vid = v

    p_m = metrics_all["pseudo_kelly"]
    b_m = metrics_all[best_tk_vid]

    cagr_diff = (b_m["cagr"] - p_m["cagr"]) * 100
    mdd_diff = (b_m["max_drawdown"] - p_m["max_drawdown"]) * 100

    report_lines.append("\n## Key Findings\n")
    report_lines.append(
        f"- **最佳 True Kelly 变体**: `{best_tk_vid}` (CAGR: {b_m['cagr'] * 100:.2f}%, Sharpe: {b_m['sharpe']:.2f})"
    )
    diff_sign = "+" if cagr_diff > 0 else ""
    report_lines.append(f"- **CAGR Delta vs Pseudo Kelly**: {diff_sign}{cagr_diff:.2f}%")
    mdd_greater = "Yes" if b_m["max_drawdown"] < p_m["max_drawdown"] else "No"
    report_lines.append(
        f"- **True Kelly 的回撤是否大于假凯利**: {mdd_greater} (差值: +{-mdd_diff:.2f}%)"
    )

    report_lines.append("\n## Conclusion\n")

    if b_m["sharpe"] > p_m["sharpe"] or b_m["calmar"] > p_m["calmar"]:
        report_lines.append(
            "- ✅ **建议**: True Kelly 在风险回撤修正收益上具有优势 (更好的 Sharpe/Calmar)。支持融合生产主线。"
        )
    else:
        report_lines.append(
            "- ⚠️ **警告**: True Kelly 指标下穿。伪造回溯存在劣化，需重新审视参数 `kelly_scale`。"
        )

    if b_m["max_drawdown"] < p_m["max_drawdown"] * 1.5:
        report_lines.append(
            "- 🚨 **高风险警告**: True Kelly 最大回撤超过 Pseudo Kelly 1.5倍。由于资金周转过速必须降倍 `kelly_scale`。"
        )

    (output_dir / "pnl_report.md").write_text("\n".join(report_lines) + "\n")
    print(f"[kelly_pnl] Report saved to {output_dir}")


if __name__ == "__main__":
    main()
