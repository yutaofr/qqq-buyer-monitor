"""Performance attribution for backtest results.

Computes standard quantitative performance metrics from a NAV series
and trade log. All inputs are deterministic (no resampling/bootstrap).

Pure functions — no state, no I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def compute_attribution(
    nav: pd.Series,
    log: pd.DataFrame,
) -> dict:
    """Compute full performance attribution from NAV series and trade log.

    Args:
        nav: pd.Series of daily NAV values (indexed by date, starts at 1.0).
        log: pd.DataFrame with at least columns: weight, p_cp, s_t, days_held.

    Returns:
        dict with keys:
            total_return    — cumulative return from nav[0] to nav[-1]
            annualised_ret  — CAGR
            sharpe          — annualised Sharpe (rf=0)
            max_drawdown    — maximum peak-to-trough drawdown
            n_trades        — number of position changes
            qld_fraction    — fraction of days in QLD
            avg_hold_days   — average holding period per QLD position
    """
    rets = nav.pct_change().dropna()

    total_return   = float(nav.iloc[-1] / nav.iloc[0] - 1.0)
    n_years        = len(nav) / TRADING_DAYS_PER_YEAR
    annualised_ret = float((1.0 + total_return) ** (1.0 / max(n_years, 1e-6)) - 1.0)

    sharpe = _compute_sharpe(rets)
    max_dd = _compute_max_drawdown(nav)

    weights = log["weight"]
    n_trades = int((weights.diff().fillna(weights.iloc[0]).abs() > 0).sum())
    qld_fraction = float((weights == 1.0).mean())
    avg_hold = _compute_avg_hold(weights)

    return {
        "total_return":   total_return,
        "annualised_ret": annualised_ret,
        "sharpe":         sharpe,
        "max_drawdown":   max_dd,
        "n_trades":       n_trades,
        "qld_fraction":   qld_fraction,
        "avg_hold_days":  avg_hold,
    }


def _compute_sharpe(daily_rets: pd.Series) -> float:
    """Annualised Sharpe ratio (rf = 0)."""
    std = daily_rets.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(daily_rets.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _compute_max_drawdown(nav: pd.Series) -> float:
    """Maximum peak-to-trough drawdown (negative number, e.g. -0.15 = -15%)."""
    rolling_max = nav.cummax()
    drawdown = (nav - rolling_max) / rolling_max
    return float(drawdown.min())


def _compute_avg_hold(weights: pd.Series) -> float:
    """Average number of days per QLD holding period."""
    in_qld = (weights == 1.0).astype(int)
    # Group consecutive QLD days
    groups = (in_qld.diff().fillna(in_qld.iloc[0]).abs() > 0).cumsum()
    hold_lengths = []
    for _, grp in in_qld.groupby(groups):
        if grp.iloc[0] == 1:
            hold_lengths.append(len(grp))
    return float(np.mean(hold_lengths)) if hold_lengths else 0.0
