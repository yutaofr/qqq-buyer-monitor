"""End-to-end backtest runner.

SRD v1.2 Section 8: Integrates all Phase 1-4 modules into a single loop.

Data flow per day t (post burn-in):
  1. Extract observation vector x_t = [ED_ACCEL, SPREAD_ANOMALY, FISHER_RHO]
  2. BOCPDEngine.update(x_t, lambda_macro_t) → p_cp_raw
  3. Allocator.step(p_cp_raw, lambda_macro_t) → (weight, alloc_log)
  4. NavAccumulator.step(weight, qqq_ret, qld_ret) → nav_t

Burn-in period (default 252 days):
  - BOCPD engine runs and accumulates state (suff_stats fills in)
  - Allocator stays in QQQ (weight=0.0) — no QLD during burn-in
  - NAV: 100% QQQ returns during burn-in

The runner owns no side effects beyond building the results dict.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.liquidity.backtest.attribution import compute_attribution
from src.liquidity.backtest.nav import NavAccumulator
from src.liquidity.control.allocator import Allocator
from src.liquidity.engine.bocpd import BOCPDEngine

# Column names expected in the panel DataFrame
_REQUIRED_COLS = {
    "VIXCLS", "WALCL", "RRPONTSYD", "WTREGEN", "SOFR", "QQQ_ret", "QLD_ret"
}


def run_backtest(
    panel: pd.DataFrame,
    constituent_rets: pd.DataFrame,
    config: dict,
    burn_in: int = 252,
) -> dict:
    """Execute the full backtest loop over a pre-built PiT-aligned panel.

    Args:
        panel:    DataFrame with DatetimeIndex and columns in _REQUIRED_COLS.
        constituent_rets: DataFrame of top 50 constituent returns.
        config:   Parameter dict from load_config().
        burn_in:  Number of days for BOCPD engine warm-up. Default 252.

    Returns:
        dict with keys:
            nav         — pd.Series of daily NAV (post burn-in)
            log         — pd.DataFrame of per-day diagnostics (post burn-in)
            attribution — dict of performance metrics
    """
    from src.liquidity.engine.pipeline import LiquidityPipeline

    _validate_panel(panel)
    assert panel.index.equals(constituent_rets.index), "panel 与 constituent_rets 日期索引不对齐"

    pipeline = LiquidityPipeline(config, burn_in=burn_in)
    exec_cfg = config["execution"]
    map_cfg  = config["mapping"]
    nav_acc = NavAccumulator(
        slippage_bps=exec_cfg["s0_bps"],
        s0_bps=exec_cfg["s0_bps"],
        s1_bps=exec_cfg["s1_bps"],
        sigma_calm=map_cfg["sigma_calm"],
        sigma_stress=map_cfg["sigma_stress"],
        sigma_normal=exec_cfg["sigma_normal"],
    )

    nav_vals:    list[float] = []
    log_records: list[dict]  = []
    post_burn_idx: list      = []

    prev_weight = 0.0

    # Ensure constituent_rets is a numpy array view aligned with the loop
    rets_matrix = constituent_rets.to_numpy(dtype=float)

    for i, (date, row) in enumerate(panel.iterrows()):
        c_rets = rets_matrix[i, :]
        qqq_ret = float(row["QQQ_ret"])
        qld_ret = float(row["QLD_ret"])

        # 1. Pipeline processes everything automatically
        obs = {
            "vix": float(row["VIXCLS"]),
            "walcl": float(row["WALCL"]),
            "rrp": float(row["RRPONTSYD"]),
            "tga": float(row["WTREGEN"]),
            "sofr": float(row["SOFR"]),
            "constituent_returns": c_rets,
            "qqq_price": float(row.get("QQQ_price", 0.0)),
            "qqq_sma200": float(row.get("QQQ_sma200", 0.0))
        }
        
        weight, log = pipeline.step(timestamp=date, raw_obs=obs)
        
        # 2. Add structural variables for diagnostics
        log.update(
            date=date,
            weight=weight,
            qqq_ret=qqq_ret,
            qld_ret=qld_ret,
            s_t=log.get("s_t", 0.0),
        )

        # We must push returns into nav_acc even if in burn-in
        # (weight = 0.0, s_t = 0.0 to track baseline correctly)
        nav_acc.step(
            weight_qld=weight,
            qqq_ret=qqq_ret,
            qld_ret=qld_ret,
            prev_weight=prev_weight,
            s_t=log.get("s_t", 0.0),
        )

        if log["state"] == "active":
            nav_vals.append(nav_acc.current_nav)
            log_records.append(log)
            post_burn_idx.append(date)

        prev_weight = weight

    # Build output structures
    nav_series = pd.Series(nav_vals, index=post_burn_idx, name="NAV")
    # Normalise: first post-burn-in NAV = 1.0
    if len(nav_series) > 0 and nav_series.iloc[0] != 0:
        nav_series = nav_series / nav_series.iloc[0]

    log_df = pd.DataFrame(log_records, index=post_burn_idx)
    attr   = compute_attribution(nav_series, log_df)

    return {
        "nav":         nav_series,
        "log":         log_df,
        "attribution": attr,
    }


def _validate_panel(panel: pd.DataFrame) -> None:
    """Check panel has required columns and zero NaN in asset returns."""
    missing = _REQUIRED_COLS - set(panel.columns)
    if missing:
        raise ValueError(f"Panel missing required columns: {missing}")
        
    nan_count = panel[["QQQ_ret", "QLD_ret"]].isna().sum().sum()
    if nan_count > 0:
        raise ValueError(
            f"Panel has {nan_count} NaN values in QQQ/QLD returns. "
            f"Lookback padding or PiT alignment has failed."
        )
