"""Hazard function precomputation for BOCPD.

SRD v1.2 Chapter 2: Two-dimensional orthogonal prior structure.
  h(r, t) = lambda_macro(t) × g(r)

g(r) is the run-length modulation function — a time-invariant structural
prior that encodes how likely a changepoint is given the current regime's age.
It is precomputed once at engine initialization.

All functions are pure (no side effects, no state).
"""

import numpy as np


def precompute_g_r(
    r_max: int = 504,
    r_stable: int = 63,
    kappa: int = 5,
) -> np.ndarray:
    """Precompute the run-length modulation function g(r).

    SRD 2.2:
        g(r) = 1 + kappa/(r+1)   for r < r_stable  (convergence zone)
        g(r) = 1                  for r >= r_stable  (stable zone)

    Vectorized via boolean mask multiplication — no Python loops, no branches.

    Args:
        r_max: Maximum run length before hard truncation. Default 504 (2 years).
        r_stable: Onset of the stable zone. Default 63 (1 quarter).
        kappa: Hazard boost strength in convergence zone. Default 5.

    Returns:
        np.ndarray of shape (r_max + 1,) with dtype float64.
    """
    r = np.arange(r_max + 1, dtype=np.float64)
    g_r = 1.0 + kappa / (r + 1.0) * (r < r_stable)
    return g_r


def compute_hazard(
    g_r: np.ndarray,
    lambda_macro: float,
    r_max: int = 504,
) -> np.ndarray:
    """Compute the hazard vector h(r) for a given macro hazard rate.

    SRD 2.1:
        h(r, t) = clip(lambda_macro(t) × g(r), 0, 1)

    SRD 2.3 — Hard truncation:
        h[R_MAX] = 1.0   (forces all probability mass back to r=0)

    Args:
        g_r: Precomputed modulation function, shape (R_MAX + 1,).
        lambda_macro: Scalar macro hazard rate for time t. Must be >= 0.
        r_max: Maximum run length. Default 504.

    Returns:
        np.ndarray of shape (R_MAX + 1,) with values in [0, 1].
    """
    h = np.clip(lambda_macro * g_r, 0.0, 1.0)
    h[r_max] = 1.0  # SRD 2.3: forced truncation — ghost regime killer
    return h
