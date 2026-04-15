"""Dynamic slippage model.

SRD v1.2 Section 6.2:
    Slippage(t) = s0 + s1 × σ̂_t / σ_normal

Where:
    s0         = 3 bps  (base execution cost)
    s1         = 2 bps  (volatility-sensitive component)
    σ_normal   = 18%    (annualised calm-regime vol)
    σ̂_t        = AEMA-weighted volatility estimate

In high-vol environments (σ̂=45%), slippage = 3 + 2*(45/18) = 8 bps.
In calm environments (σ̂=18%), slippage = 3 + 2*(18/18) = 5 bps.

This replaces the fixed 3bps used in the original POC NavAccumulator.

Pure function — no state, no I/O.
"""


def compute_slippage(
    sigma_hat: float,
    s0_bps: float = 3.0,
    s1_bps: float = 2.0,
    sigma_normal: float = 0.18,
) -> float:
    """Compute dynamic slippage cost in basis points.

    Args:
        sigma_hat:    Current estimated annualised volatility.
        s0_bps:       Base cost in bps. Default 3.0.
        s1_bps:       Vol-sensitive cost in bps. Default 2.0.
        sigma_normal: Reference calm-regime vol. Default 0.18 (18%).

    Returns:
        Total slippage in basis points (e.g., 5.0 = 5bps).
    """
    if sigma_normal <= 0:
        return float(s0_bps)
    return float(s0_bps + s1_bps * sigma_hat / sigma_normal)


def compute_sigma_hat(
    s_t: float,
    sigma_calm: float = 0.18,
    sigma_stress: float = 0.45,
) -> float:
    """Compute AEMA-blended volatility estimate.

    SRD 4.2: σ̂_t = (1 - s_t) × σ_calm + s_t × σ_stress

    Args:
        s_t:          Current AEMA smoothed stress in [0, 1].
        sigma_calm:   Calm-regime annualised vol. Default 0.18.
        sigma_stress: Stress-regime annualised vol. Default 0.45.

    Returns:
        Blended vol estimate.
    """
    return float((1.0 - s_t) * sigma_calm + s_t * sigma_stress)
