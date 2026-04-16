"""
run_full_cycle_physical_audit.py
Full 2005-2026 Backtest explicitly targeting Turnover Friction, Volatility Drag, and Calmar ratios.
"""

import logging

import numpy as np
import pandas as pd

from src.liquidity.backtest.attribution import compute_attribution
from src.liquidity.backtest.runner import run_backtest
from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("physical_audit")

def compute_benchmark_metrics(rets: pd.Series, name: str) -> None:
    nav = (1.0 + rets).cumprod()
    total_ret = nav.iloc[-1] - 1.0
    n_years = len(nav) / 252.0
    cagr = (1.0 + total_ret) ** (1.0 / n_years) - 1.0

    rolling_max = nav.cummax()
    mdd = ((nav - rolling_max) / rolling_max).min()

    std = rets.std()
    sharpe = (rets.mean() / std * np.sqrt(252)) if std > 0 else 0.0
    calmar = (cagr / abs(mdd)) if mdd < 0 else float('inf')

    logger.info(f"[{name}] CAGR: {cagr*100:.2f}% | MDD: {mdd*100:.2f}% | Sharpe: {sharpe:.2f} | Calmar: {calmar:.2f}")

def main():
    logger.info("Initializing 2005-2026 Full Lifecycle Physical Audit...")
    config = load_config()

    # We fetch enough data so that post-burn-in begins cleanly in 2005-2006.
    panel, c_rets = build_pit_aligned_panel("2005-01-01", "2026-04-16", config=config)

    # Suppress lower-level logs during calculation
    logging.getLogger("src.liquidity").setLevel(logging.WARNING)
    res = run_backtest(panel, c_rets, config)

    log_df = res["log"]
    nav_se = res["nav"]

    # 1. Performance Overview
    stats = compute_attribution(nav_se, log_df)
    cagr = stats['annualised_ret'] * 100
    mdd = stats['max_drawdown'] * 100
    sharpe = stats['sharpe']
    calmar = stats['annualised_ret'] / abs(stats['max_drawdown'])

    logger.info("\n========== CORE SYSTEM PERFORMANCE ==========")
    logger.info(f"Strategy CAGR:   {cagr:.2f}%")
    logger.info(f"Strategy MDD:    {mdd:.2f}%")
    logger.info(f"Sharpe Ratio:    {sharpe:.2f}")
    logger.info(f"Calmar Ratio:    {calmar:.2f}")

    # 2. Turnover & Friction
    n_trades = stats['n_trades']
    years = len(nav_se) / 252.0
    trades_per_year = n_trades / years
    qld_fraction = stats['qld_fraction'] * 100

    # To quantify friction roughly, compare to slippage cost
    # We run a frictionless theoretical simulation
    frictionless_nav = 1.0
    frictionless_se = []

    # Align log_df cleanly with the index of nav_se
    log_df = log_df.loc[nav_se.index]

    for _i, (_dt, row) in enumerate(log_df.iterrows()):
        w = row["weight"]
        qld_ret = row["qld_ret"]
        qqq_ret = row["qqq_ret"]

        day_ret = w * qld_ret + (1.0 - w) * qqq_ret
        frictionless_nav *= (1.0 + day_ret)
        frictionless_se.append(frictionless_nav)

    f_series = pd.Series(frictionless_se, index=nav_se.index)
    f_cagr = ((f_series.iloc[-1]) ** (1.0 / years) - 1.0) * 100.0

    logger.info("\n========== FRICTION & TURNOVER ==========")
    logger.info(f"Total Portfolio Trades: {n_trades} ({trades_per_year:.1f} per year / avg)")
    logger.info(f"QLD Allocation Time:    {qld_fraction:.1f}% of total days")
    logger.info(f"Frictionless CAGR:      {f_cagr:.2f}%")
    logger.info(f"Loss to slippage:       {f_cagr - cagr:.2f}% per year")

    # 3. Volatility Drag & Benchmark Comparison
    logger.info("\n========== BENCHMARK COMPARISON ==========")
    qqq_rets = panel.loc[nav_se.index, "QQQ_ret"]
    qld_rets = panel.loc[nav_se.index, "QLD_ret"]

    compute_benchmark_metrics(qqq_rets, "Buy & Hold QQQ")
    compute_benchmark_metrics(qld_rets, "Buy & Hold QLD")

    # Specific Audit: 2008 GFC
    logger.info("\n========== EVENT AUDIT: 2008 GFC ==========")
    if "2008-01-01" in nav_se.index and "2009-01-01" in nav_se.index:
        nav_2008 = nav_se.loc["2008-01-01":"2009-01-01"]
        qqq_2008 = (1.0 + qqq_rets.loc["2008-01-01":"2009-01-01"]).cumprod()
        qld_2008 = (1.0 + qld_rets.loc["2008-01-01":"2009-01-01"]).cumprod()
        strat_2008 = nav_2008 / nav_2008.iloc[0]

        logger.info(f"QQQ 2008 Max Drawdown: {((qqq_2008 - qqq_2008.cummax())/qqq_2008.cummax()).min()*100:.2f}%")
        logger.info(f"QLD 2008 Max Drawdown: {((qld_2008 - qld_2008.cummax())/qld_2008.cummax()).min()*100:.2f}%")
        logger.info(f"SYS 2008 Max Drawdown: {((strat_2008 - strat_2008.cummax())/strat_2008.cummax()).min()*100:.2f}%")

    # Specific Audit: 2022 Bear Market Chop
    logger.info("\n========== EVENT AUDIT: 2022 BEAR CHOP ==========")
    if "2022-01-01" in nav_se.index and "2023-01-01" in nav_se.index:
        nav_2022 = nav_se.loc["2022-01-01":"2023-01-01"]
        qqq_2022 = (1.0 + qqq_rets.loc["2022-01-01":"2023-01-01"]).cumprod()
        strat_2022 = nav_2022 / nav_2022.iloc[0]

        logger.info(f"QQQ 2022 Drop:         {(qqq_2022.iloc[-1] - 1.0)*100:.2f}% (MDD: {((qqq_2022 - qqq_2022.cummax())/qqq_2022.cummax()).min()*100:.2f}%)")
        logger.info(f"Strategy 2022 Drop:    {(strat_2022.iloc[-1] - 1.0)*100:.2f}% (MDD: {((strat_2022 - strat_2022.cummax())/strat_2022.cummax()).min()*100:.2f}%)")

    # 4. Telemetry Export for Dashboard
    logger.info("\n========== TELEMETRY EXPORT ==========")
    export_df = log_df.copy()
    export_df["NAV"] = nav_se
    export_df["QQQ_Hold"] = (1.0 + qqq_rets).cumprod().loc[nav_se.index]
    export_df["QLD_Hold"] = (1.0 + qld_rets).cumprod().loc[nav_se.index]

    # Normalize benchmarks to start at 1.0 same as Strategy NAV
    export_df["QQQ_Hold"] = export_df["QQQ_Hold"] / export_df["QQQ_Hold"].iloc[0]
    export_df["QLD_Hold"] = export_df["QLD_Hold"] / export_df["QLD_Hold"].iloc[0]

    output_path = "telemetry_data.csv"
    export_df.to_csv(output_path)
    logger.info(f"Exported telemetry data to {output_path} ({len(export_df)} rows)")

if __name__ == "__main__":
    main()
