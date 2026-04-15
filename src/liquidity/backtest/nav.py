"""NAV accumulator — two-step portfolio return computation.

SRD v1.2 Section 8.6: Two-step NAV update.
  Step 1: Signal at t-1 close → target weight for day t.
  Step 2: NAV_t = max(0, NAV_{t-1} × (1 + portfolio_ret_t - slippage_t))

Execution gap (open vs close) is attribution only — not deducted from NAV.
Slippage is deducted ONLY on position changes (transitions), not on HOLD.

Pure functions + stateful accumulator. Side effects (history) are
isolated in NavAccumulator, never inside compute_portfolio_return.
"""

from __future__ import annotations


def compute_portfolio_return(
    weight_qld: float,
    qqq_ret: float,
    qld_ret: float,
) -> float:
    """Compute one-day portfolio return given position weight.

    Args:
        weight_qld: Fraction in QLD ∈ [0, 1]. 0 = QQQ only, 1 = QLD only.
        qqq_ret:    QQQ daily return (e.g., 0.01 = +1%).
        qld_ret:    QLD daily return.

    Returns:
        Blended portfolio return.
    """
    return float(weight_qld * qld_ret + (1.0 - weight_qld) * qqq_ret)


class NavAccumulator:
    """Stateful NAV accumulator with slippage on position changes.

    Args:
        initial_nav:    Starting NAV. Default 1.0.
        slippage_bps:   Basis points charged on position change. Default 3.0.
    """

    def __init__(
        self,
        initial_nav: float = 1.0,
        slippage_bps: float = 3.0,
    ) -> None:
        self._nav          = float(initial_nav)
        self._slippage_bps = float(slippage_bps)
        self._history: list[float] = []
        self._prev_weight: float | None = None

    @property
    def current_nav(self) -> float:
        return self._nav

    @property
    def history(self) -> list[float]:
        return self._history

    def step(
        self,
        weight_qld: float,
        qqq_ret: float,
        qld_ret: float,
        prev_weight: float | None = None,
    ) -> float:
        """Execute one NAV update step.

        Args:
            weight_qld:   Target weight for today.
            qqq_ret:      QQQ return for today.
            qld_ret:      QLD return for today.
            prev_weight:  Previous step weight. If None, uses internally tracked.

        Returns:
            Updated NAV.
        """
        effective_prev = prev_weight if prev_weight is not None else self._prev_weight

        # Slippage on position change
        slippage = 0.0
        if effective_prev is not None and effective_prev != weight_qld:
            slippage = self._slippage_bps * 1e-4

        # Portfolio return
        port_ret = compute_portfolio_return(weight_qld, qqq_ret, qld_ret)

        # NAV update — floor at 0
        self._nav = max(0.0, self._nav * (1.0 + port_ret - slippage))
        self._history.append(self._nav)
        self._prev_weight = weight_qld

        return self._nav
