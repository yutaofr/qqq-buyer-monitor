"""Macro hazard rate synthesis pipeline.

SRD v1.2: Converts four macro liquidity variables into a scalar prior
hazard rate lambda_macro for the BOCPD engine.

The four variables have wildly different scales:
    WALCL     — trillions of USD (Fed balance sheet)
    RRPONTSYD — hundreds of billions USD (overnight RRP)
    WTREGEN   — hundreds of billions USD (Treasury General Account)
    FRA-OIS   — basis points (funding market stress proxy)

Standard Z-score normalisation would fail here because:
  - WALCL and RRP are structurally non-stationary (QE regimes)
  - A Z-score from the pre-QE era has no meaning post-QE

Solution: rolling PERCENTILE RANK — purely non-parametric, no distribution
assumptions, naturally bounded in [0, 1], regime-agnostic.

Four-step pipeline (each step is an independently testable pure function):
    Step 1: directional_transform  — unify direction: 'tightening = positive'
    Step 2: rolling_percentile_rank — normalise to [0, 1], remove units
    Step 3: composite_stress        — weighted average of ranks
    Step 4: map_to_hazard           — linear map to [lambda_floor, lambda_ceil]

Safety constraint (verified in tests):
    lambda_ceil(0.016) × g(r=0)(6.0) = 0.096 < 1.0  → h never exceeds 1

All functions are pure — no state, no network calls.
"""

import numpy as np
import pandas as pd


def directional_transform(
    walcl: pd.Series,
    rrp: pd.Series,
    tga: pd.Series,
    fra_ois: pd.Series,
) -> dict[str, pd.Series]:
    """Step 1: Transform raw macro variables to unified 'tightening = positive' scale.

    Transformations (SRD design rationale):
        WALCL   → -pct_change(20d)   declining reserves = tightening
        RRP     → -pct_change(5d)    buffer drawdown = tightening
        TGA     → +pct_change(20d)   Treasury hoarding = liquidity drain
        FRA-OIS →  level              spread itself is the stress signal

    Args:
        walcl:   Fed Reserve assets (H.4.1), weekly, PiT-aligned.
        rrp:     Overnight RRP outstanding, daily.
        tga:     Treasury General Account, weekly, PiT-aligned.
        fra_ois: FRA-OIS spread in decimal (e.g., 0.002 = 20bps).

    Returns:
        dict with keys 'walcl', 'rrp', 'tga', 'fra_ois' — each a pd.Series.
    """
    return {
        "walcl":   -walcl.pct_change(periods=20),
        "rrp":     -rrp.pct_change(periods=5),
        "tga":     tga.pct_change(periods=20),
        "fra_ois": fra_ois.copy(),
    }


def rolling_percentile_rank(
    signal: pd.Series,
    lookback: int = 504,
) -> pd.Series:
    """Step 2: Rolling empirical CDF percentile rank.

    rank_t = #{s in [t-lookback, t] : signal_s <= signal_t} / lookback

    Output is naturally bounded in [0, 1] with no distribution assumptions.
    The 504-day window (≈ 2 years, aligning with BOCPD R_MAX) ensures the
    rank captures cross-regime comparisons.

    Args:
        signal:   Directionally transformed signal from Step 1.
        lookback: Rolling window in trading days. Default 504.

    Returns:
        pd.Series of ranks in [0, 1], same index as signal.
    """
    def _rank_last(window: np.ndarray) -> float:
        current = window[-1]
        return float(np.sum(window <= current) / len(window))

    ranked = signal.rolling(window=lookback, min_periods=lookback).apply(
        _rank_last, raw=True
    )
    ranked.name = signal.name
    return ranked


def composite_stress(
    ranks: dict[str, pd.Series],
    weights: dict[str, float],
) -> pd.Series:
    """Step 3: Weighted composite of percentile ranks.

    If any variable is fully NaN for a given date, its weight is
    redistributed proportionally to available variables (NaN-safe weighting).

    Args:
        ranks:   Dict of ranked signals (output of rolling_percentile_rank).
        weights: Dict of weights per variable. Must sum to 1.0.

    Returns:
        pd.Series of composite stress in [0, 1].
    """
    # Stack all series into a DataFrame for vectorised NaN-aware averaging
    df = pd.DataFrame(ranks)
    w  = pd.Series(weights)

    # Vectorised weighted mean with NaN redistribution:
    # For each row, compute sum(w_i * x_i) / sum(w_i for non-NaN x_i)
    weighted_sum    = df.multiply(w, axis=1).sum(axis=1, skipna=True)
    available_weight = df.notna().multiply(w, axis=1).sum(axis=1)

    composite = weighted_sum / available_weight.replace(0, np.nan)
    composite.name = "COMPOSITE_STRESS"
    return composite


def map_to_hazard(
    composite: pd.Series,
    lambda_floor: float = 0.002,
    lambda_ceil: float = 0.016,
) -> pd.Series:
    """Step 4: Linear mapping from composite stress [0, 1] to hazard rate.

    lambda_t = lambda_floor + (lambda_ceil - lambda_floor) * composite_t

    Safety property: lambda_ceil(0.016) × g(r=0)(6.0) = 0.096 < 1.0
    This guarantees the hazard probability h[0] never exceeds 1.0
    regardless of the macro environment.

    Args:
        composite:    Output of composite_stress(). Values in [0, 1].
        lambda_floor: Minimum hazard rate (calm). Default 0.002 (≈1 CP/2yr).
        lambda_ceil:  Maximum hazard rate (crisis). Default 0.016 (≈1 CP/qtr).

    Returns:
        pd.Series of hazard rates in [lambda_floor, lambda_ceil].
    """
    lm = lambda_floor + (lambda_ceil - lambda_floor) * composite
    lm.name = "LAMBDA_MACRO"
    return lm
