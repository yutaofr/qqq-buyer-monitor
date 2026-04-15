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
    "ED_ACCEL", "SPREAD_ANOMALY", "FISHER_RHO",
    "LAMBDA_MACRO", "QQQ_ret", "QLD_ret",
}


def run_backtest(
    panel: pd.DataFrame,
    config: dict,
    burn_in: int = 252,
) -> dict:
    """Execute the full backtest loop over a pre-built PiT-aligned panel.

    Args:
        panel:    DataFrame with DatetimeIndex and columns in _REQUIRED_COLS.
                  Must have zero NaN (enforced by _assert_no_nan in Phase 3).
        config:   Parameter dict from load_config().
        burn_in:  Number of days for BOCPD engine warm-up. Default 252.

    Returns:
        dict with keys:
            nav         — pd.Series of daily NAV (post burn-in)
            log         — pd.DataFrame of per-day diagnostics (post burn-in)
            attribution — dict of performance metrics
    """
    _validate_panel(panel)

    bocpd   = BOCPDEngine(config)
    alloc   = Allocator(config)
    exec_cfg = config["execution"]
    map_cfg  = config["mapping"]
    nav_acc = NavAccumulator(
        slippage_bps=exec_cfg["s0_bps"],   # fallback only (when s_t not given)
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

    for i, (date, row) in enumerate(panel.iterrows()):
        x_t = np.array([
            row["ED_ACCEL"],
            row["SPREAD_ANOMALY"],
            row["FISHER_RHO"],
        ], dtype=np.float64)
        lambda_macro = float(row["LAMBDA_MACRO"])

        # Step 1+2: BOCPD update
        p_cp = bocpd.update(x_t, lambda_macro)

        if i < burn_in:
            # Burn-in: engine warms up, allocator stays in QQQ
            nav_acc.step(
                weight_qld=0.0,
                qqq_ret=float(row["QQQ_ret"]),
                qld_ret=float(row["QLD_ret"]),
                prev_weight=0.0,
            )
            prev_weight = 0.0
            continue

        # Post burn-in: full control chain
        weight, alloc_log = alloc.step(p_cp, lambda_macro)

        # Step 4: NAV update with SRD 6.2 dynamic slippage
        nav_acc.step(
            weight_qld=weight,
            qqq_ret=float(row["QQQ_ret"]),
            qld_ret=float(row["QLD_ret"]),
            prev_weight=prev_weight,
            s_t=alloc_log["s_t"],
        )

        nav_vals.append(nav_acc.current_nav)
        log_records.append({
            "weight":     weight,
            "p_cp":       p_cp,
            "s_t":        alloc_log["s_t"],
            "signal":     alloc_log["signal"],
            "days_held":  alloc_log["days_held"],
            "circuit_breaker": alloc_log["circuit_breaker"],
        })
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
    """Check panel has required columns and zero NaN."""
    missing = _REQUIRED_COLS - set(panel.columns)
    if missing:
        raise ValueError(f"Panel missing required columns: {missing}")
    nan_count = panel[list(_REQUIRED_COLS)].isna().sum().sum()
    if nan_count > 0:
        raise ValueError(
            f"Panel has {nan_count} NaN values in required columns. "
            f"Lookback padding or PiT alignment has failed."
        )
