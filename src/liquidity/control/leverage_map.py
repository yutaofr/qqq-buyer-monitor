"""Dual-decision leverage mapping.

SRD v1.2 Section 4.2:
    L_target = (1 - P̄) × σ_target / σ̂_t

Where:
    P̄         = AEMA smoothed stress (s_t)
    σ̂_t       = (1 - P̄) × σ_calm + P̄ × σ_stress
    σ_target  = 36% = 2 × σ_calm

Key reference points:
    P̄ = 0.0 → σ̂ = 0.18 → L = 1.0 × 0.36/0.18 = 2.0  (full QLD)
    P̄ = 0.5 → σ̂ = 0.315 → L = 0.5 × 0.36/0.315 ≈ 0.571
    P̄ = 1.0 → σ̂ = 0.45  → L = 0.0 × 0.36/0.45 = 0.0  (full Cash)

SRD v1.2 Section 4.3: Three-way allocation from leverage:
    L >= 1  → QLD = L-1,  QQQ = 2-L,  Cash = 0
    L <  1  → QLD = 0,    QQQ = L,    Cash = 1-L

Pure functions — no state, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.liquidity.backtest.slippage import compute_sigma_hat


@dataclass(frozen=True)
class Allocation:
    """Immutable three-way portfolio allocation."""

    qld:  float    # [0, 1]
    qqq:  float    # [0, 1]
    cash: float    # [0, 1]
    leverage: float  # L ∈ [0, 2]

    def __post_init__(self) -> None:
        total = self.qld + self.qqq + self.cash
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Allocation does not sum to 1.0: "
                f"QLD={self.qld:.4f} QQQ={self.qqq:.4f} Cash={self.cash:.4f} "
                f"Sum={total:.4f}"
            )


def compute_leverage(
    s_t: float,
    sigma_calm: float = 0.18,
    sigma_stress: float = 0.45,
    sigma_target: float = 0.36,
) -> float:
    """Compute target leverage from AEMA stress level.

    SRD 4.2: L_target = (1 - s_t) × σ_target / σ̂_t's

    Args:
        s_t:          AEMA smoothed stress in [0, 1].
        sigma_calm:   Calm-regime annualised vol. Default 0.18.
        sigma_stress: Stress-regime annualised vol. Default 0.45.
        sigma_target: Target portfolio vol. Default 0.36.

    Returns:
        Target leverage L ∈ [0, 2], clamped.
    """
    sigma_hat = compute_sigma_hat(s_t, sigma_calm, sigma_stress)
    if sigma_hat <= 0:
        return 0.0
    l_raw = (1.0 - s_t) * sigma_target / sigma_hat
    return float(max(0.0, min(2.0, l_raw)))


def compute_allocation(leverage: float) -> Allocation:
    """Map continuous leverage to three-way portfolio weights.

    SRD 4.3:
        L >= 1 → QLD = L-1,  QQQ = 2-L,  Cash = 0
        L <  1 → QLD = 0,    QQQ = L,    Cash = 1-L

    Args:
        leverage: Target leverage L ∈ [0, 2].

    Returns:
        Allocation dataclass (qld, qqq, cash, leverage).
    """
    lev = max(0.0, min(2.0, leverage))

    if lev >= 1.0:
        return Allocation(qld=lev - 1.0, qqq=2.0 - lev, cash=0.0, leverage=lev)
    return Allocation(qld=0.0, qqq=lev, cash=1.0 - lev, leverage=lev)
