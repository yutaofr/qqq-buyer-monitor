"""OOS Stress Audit: 2011, 2015, 2018.

Evaluates the orthogonal armor response to out-of-sample stress events.
Quantifies "Whipsaw Penalty" (both time delay and economic lag).
"""

from __future__ import annotations

import copy
import logging

import numpy as np
import pandas as pd

from src.liquidity.backtest.runner import run_backtest
from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("oos_audit")

# Three Out-Of-Sample crisis windows
WINDOWS = {
    "2011_Debt_Downgrade": ("2011-06-01", "2011-12-31"),
    "2015_Yuan_Deval":     ("2015-08-01", "2016-03-31"),
    "2018_Volmageddon":    ("2018-01-15", "2018-05-31"),
}

ALPHA_DOWN_GRID = [0.02, 0.04, 0.06, 0.08, 0.10, 0.15]

def analyze_window(name: str, start: str, end: str, log_df: pd.DataFrame, nav_se: pd.Series, panel: pd.DataFrame, alpha: float = 0.0):
    w_log = log_df.loc[start:end]
    w_nav = nav_se.loc[start:end]
    w_panel = panel.loc[start:end]

    if w_log.empty:
        return {"mdd": 0.0, "opp_cost": None, "delay": None, "never_recon": True}

    max_pcp = w_log['p_cp'].max()
    max_pcp_date = w_log['p_cp'].idxmax()

    cap_active = w_log['vol_guard_cap'] < 1.0
    if cap_active.any():
        first_cap_date = cap_active.idxmax()
        min_cap = w_log['vol_guard_cap'].min()
    else:
        first_cap_date = None
        min_cap = 1.0

    qqq_cum = (1 + w_panel['QQQ_ret']).cumprod()
    bottom_date = qqq_cum.idxmin()

    post_bottom_log = w_log.loc[bottom_date:]
    post_bottom_panel = w_panel.loc[bottom_date:]
    post_bottom_nav = w_nav.loc[bottom_date:]
    recovered_mask = post_bottom_log['l_final'] >= 0.99

    if "2018" == name and alpha == 0.04:
        print("\n================== DAILY DEBUG α=0.04 ==================")
        print(f"Bottom Date: {bottom_date.date()}")
        for dt, row in post_bottom_log.iterrows():
            ceil_val = max(np.ceil(row['l_target']), 1.0)
            delta = row['l_target'] - row['l_final']
            rel_gap = delta / (ceil_val - row['l_final'] + 1e-6) if delta > 0 else 0.0
            print(f"{dt.date()} | l_tgt: {row['l_target']:.4f} | l_fin: {row['l_final']:.4f} | cap: {row['vol_guard_cap']:.4f} | delta: {delta:.4f} | rel_gap: {rel_gap:.4f}")
        print("====================================================\n")

    if recovered_mask.any():
        recovered_date = recovered_mask.idxmax()
        delay_days = len(post_bottom_log.loc[:recovered_date]) - 1

        whipsaw_qld_ret = (1 + post_bottom_panel.loc[:recovered_date, 'QLD_ret']).prod() - 1
        whipsaw_nav_ret = (post_bottom_nav.loc[recovered_date] / post_bottom_nav.loc[bottom_date]) - 1
        opportunity_cost = whipsaw_qld_ret - whipsaw_nav_ret
        never_recon = False
    else:
        never_recon = True
        delay_days = None
        opportunity_cost = None

    macro_tau_avg = w_log['tau_t'].mean()
    macro_tau_max = w_log['tau_t'].max()

    # Overall NAV drawdown
    mdd = ((w_nav - w_nav.expanding().max()) / w_nav.expanding().max()).min()

    res = {
        "mdd": mdd,
        "opp_cost": opportunity_cost if 'opportunity_cost' in locals() else None,
        "delay": delay_days if 'delay_days' in locals() else None,
        "never_recon": False if 'recovered_mask' in locals() and recovered_mask.any() else True
    }
    return res



def main():
    logger.info("Loading master panel and config...")
    panel, constituent_rets = build_pit_aligned_panel("2005-01-01", "2025-01-01")
    base_config = load_config()

    logger.info("OOS Alpha_down Grid Search:")
    logger.info(f"{'Alpha':<6} | {'2011 MDD':<10} | {'15 VolMax MDD':<13} | {'18 Delay(d)':<11} | {'18 OppCost':<10}")
    logger.info("-" * 65)

    for alpha in ALPHA_DOWN_GRID:
        config = copy.deepcopy(base_config)
        config["regime_vol_guard"]["floor_alpha_down"] = alpha

        # Suppress noise
        logger.setLevel(logging.WARNING)
        res = run_backtest(panel, constituent_rets, config)
        logger.setLevel(logging.INFO)

        log_df = res["log"]
        nav_se = res["nav"]

        w_2011 = analyze_window("2011", WINDOWS["2011_Debt_Downgrade"][0], WINDOWS["2011_Debt_Downgrade"][1], log_df, nav_se, panel, alpha)
        w_2015 = analyze_window("2015", WINDOWS["2015_Yuan_Deval"][0], WINDOWS["2015_Yuan_Deval"][1], log_df, nav_se, panel, alpha)
        w_2018 = analyze_window("2018", WINDOWS["2018_Volmageddon"][0], WINDOWS["2018_Volmageddon"][1], log_df, nav_se, panel, alpha)

        mdd_2011 = f"{w_2011['mdd']:.2%}"
        mdd_2015 = f"{w_2015['mdd']:.2%}"
        delay_18 = "Never" if w_2018['never_recon'] else str(w_2018['delay'])
        cost_18 = "N/A" if w_2018['never_recon'] else f"{w_2018['opp_cost']:.2%}"

        logger.info(f"{alpha:<6.2f} | {mdd_2011:<10} | {mdd_2015:<13} | {delay_18:<11} | {cost_18:<10}")

if __name__ == "__main__":
    main()
