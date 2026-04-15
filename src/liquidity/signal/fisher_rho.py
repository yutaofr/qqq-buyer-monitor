"""Fisher-transformed rolling correlation feature.

SRD v1.2 Section 3.1 d3: Fisher(rho) captures the co-movement between
QQQ and TLT (equity-bond correlation). During liquidity crises the
flight-to-quality bid breaks the normal negative correlation, causing
this feature to spike — a complementary signal to ED and spread anomaly.

SRD 3.5 constraint: the rolling window must NOT be reset at changepoints.
This function contains no changepoint-aware logic. Window continuity is
enforced by design (no 'changepoint' or 'reset' parameters).

Pure function — no state, no network calls.
"""

import numpy as np
import pandas as pd

_CLIP_BOUND = 0.9999   # keep rho in (-1, 1) open interval for log safety


def compute_fisher_rho(
    series_a: pd.Series,
    series_b: pd.Series,
    window: int = 20,
) -> pd.Series:
    """Compute Fisher-z transformed rolling Pearson correlation.

    SRD 3.1 d3:
        rho_t    = rolling_corr(a, b, window=20)
        Fisher_t = 0.5 * ln((1 + rho_t) / (1 - rho_t))

    Boundary guard: rho is clipped to (-0.9999, 0.9999) before the
    log transform to prevent ±inf when a == b or a == -b exactly.

    Args:
        series_a: First return series (e.g., QQQ daily returns).
        series_b: Second return series (e.g., TLT daily returns).
        window:   Rolling correlation window in trading days. Default 20.

    Returns:
        pd.Series of Fisher-z values, same index as series_a.
        First (window-1) values are NaN. All subsequent values are finite.
    """
    rho = series_a.rolling(window=window, min_periods=window).corr(series_b)
    rho_clipped = rho.clip(lower=-_CLIP_BOUND, upper=_CLIP_BOUND)
    fisher = 0.5 * np.log((1.0 + rho_clipped) / (1.0 - rho_clipped))
    fisher.name = "FISHER_RHO"
    return fisher
