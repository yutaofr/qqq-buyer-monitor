"""Asymmetric Exponential Moving Average (AEMA) filter.

SRD v1.2 Section 4.2: Smooths raw p_cp_raw from BOCPD into a risk
signal s_t with deliberate asymmetry:

    Rising: alpha_up=0.50   → fast elevation (half-life ≈ 1 step)
    Falling: alpha_down=0.08 → slow decay   (half-life ≈ 8.3 steps)

Rationale: liquidity stress should be acknowledged quickly and
forgotten slowly. This prevents whipsaw exits and re-entries that
would incur compounded volatility drag on the leveraged QLD position.

Both functions are pure (no state, no I/O).
"""

import numpy as np
import pandas as pd


def update_aema(
    s_prev: float,
    p_cp: float,
    alpha_up: float,
    alpha_down: float,
    circuit_breaker: float = 1.1,
) -> float:
    """Single-step AEMA update with circuit breaker bypass.

    SRD 4.1: When p_cp > circuit_breaker (default 0.70), bypass EMA smoothing
    entirely and return p_cp directly. Internal state is ALSO set to p_cp
    (Option A: penetrate + update) so that the slow alpha_down decay governs
    the recovery path after the crisis ends.

    Args:
        s_prev:          Previous smoothed stress value in [0, 1].
        p_cp:            Raw changepoint probability from BOCPD, in [0, 1].
        alpha_up:        EMA smoothing for rising stress. Default 0.50.
        alpha_down:      EMA smoothing for falling stress. Default 0.08.
        circuit_breaker: Threshold above which EMA is bypassed. Default 1.1
                         (disabled unless explicitly set).

    Returns:
        New smoothed stress value in [0, 1].
    """
    if p_cp > circuit_breaker:
        return float(p_cp)
    alpha = alpha_up if p_cp > s_prev else alpha_down
    return float(alpha * p_cp + (1.0 - alpha) * s_prev)


def run_aema_series(
    p_series: pd.Series,
    s0: float,
    alpha_up: float,
    alpha_down: float,
    circuit_breaker: float = 1.1,
) -> pd.Series:
    """Apply AEMA filter over a full time series.

    Args:
        p_series:        Series of raw p_cp values, indexed by date.
        s0:              Initial stress value (typically 0.0 at start of backtest).
        alpha_up:        Rising alpha.
        alpha_down:      Falling alpha.
        circuit_breaker: Threshold for bypass. Default 1.1 (disabled).

    Returns:
        pd.Series of smoothed stress values, same index as p_series.
    """
    values = p_series.values
    n = len(values)
    smoothed = np.empty(n, dtype=np.float64)

    s = s0
    for i in range(n):
        s = update_aema(s, float(values[i]), alpha_up, alpha_down, circuit_breaker)
        smoothed[i] = s

    return pd.Series(smoothed, index=p_series.index, name="S_T")
