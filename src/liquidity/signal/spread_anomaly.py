"""Buy-sell spread anomaly Z-score feature.

SRD v1.2 Section 3.1 d2: Spread anomaly measures how abnormal the current
market-making environment is compared to the historical baseline.

POC uses VIX as a spread proxy (correlation > 0.7 in stress periods).
Production deployment: replace VIX with actual bid-ask spread data.

Pure function — no state, no network calls.
"""

import pandas as pd

_EPS = 1e-8   # guard against zero std in constant series


def compute_spread_anomaly(
    vix: pd.Series,
    lookback: int = 252,
) -> pd.Series:
    """Compute rolling Z-score of VIX as a spread anomaly proxy.

    SRD 3.1 d2:
        Z_t = (VIX_t - mean_{252}) / std_{252}

    min_periods = lookback // 2 to avoid excessively long warm-up while
    still requiring enough history for a meaningful mean and std.

    Division-by-zero guard: when rolling std ≈ 0 (e.g., constant series),
    the result is 0 rather than NaN or inf.

    Args:
        vix:      pd.Series of VIX daily close values (or equivalent proxy).
        lookback: Rolling window in trading days. Default 252 (1 year).

    Returns:
        pd.Series of Z-scores, same index as vix.
    """
    min_p = lookback // 2
    roll = vix.rolling(window=lookback, min_periods=min_p)
    mean = roll.mean()
    std  = roll.std().fillna(0.0)

    # Guard: where std ≈ 0, return 0 (not NaN)
    safe_std = std.where(std > _EPS, other=_EPS)
    z = (vix - mean) / safe_std
    z.name = "SPREAD_ANOMALY"
    return z
