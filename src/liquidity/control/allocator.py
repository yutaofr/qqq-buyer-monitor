"""Control chain orchestrator: AEMA → Leverage Map → Deadband → HoldPeriod → Allocation.

SRD v1.2 Section 4: Full continuous leverage control chain.

Data flow per step:
    p_cp_raw (BOCPD) → AEMA → s_t
    s_t → compute_leverage → L_target
    L_target → deadband(L_target, L_current) → L_actual
    L_actual → hold_period guard → L_final
    L_final → compute_allocation → (QLD, QQQ, Cash)

State is encapsulated inside the Allocator instance.
"""

from __future__ import annotations

from src.liquidity.control.aema import update_aema
from src.liquidity.control.leverage_map import compute_allocation, compute_leverage


class Allocator:
    """Stateful control chain executor with continuous leverage mapping.

    One instance per backtest segment. Do not share across segments
    (state is not reset between calls).

    Args:
        config: Full parameter dict from load_config().
    """

    def __init__(self, config: dict) -> None:
        aema_cfg     = config["aema"]
        deadband_cfg = config["deadband"]
        hold_cfg     = config["hold_period"]
        map_cfg      = config["mapping"]

        # AEMA params
        self._alpha_up        = aema_cfg["alpha_up"]
        self._alpha_down      = aema_cfg["alpha_down"]
        self._circuit_breaker = aema_cfg["circuit_breaker"]

        # Deadband params (SRD 4.4)
        self._delta_down      = deadband_cfg["delta_down"]
        self._delta_up        = deadband_cfg["delta_up"]
        self._recovery_coeff  = deadband_cfg["recovery_coeff"]

        # Hold period
        self._min_hold        = hold_cfg["min_qld_hold_days"]

        # Leverage map params (SRD 4.2)
        self._sigma_calm      = map_cfg["sigma_calm"]
        self._sigma_stress    = map_cfg["sigma_stress"]
        self._sigma_target    = map_cfg["sigma_target"]

        # ── Mutable state ──────────────────────────────────────
        self._s_t: float           = 0.0
        self._l_current: float     = 0.0    # current effective leverage
        self._days_in_qld: int     = 0      # days with L >= 1 (QLD position)
        self._weight: float        = 0.0    # QLD weight for backward compat

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def step(
        self,
        p_cp_raw: float,
        lambda_macro: float,
    ) -> tuple[float, dict]:
        """Execute one step of the full continuous control chain.

        Args:
            p_cp_raw:     Raw changepoint probability from BOCPDEngine.update().
            lambda_macro: Current macro hazard rate.

        Returns:
            (target_weight, log_dict)
            target_weight: QLD weight ∈ [0, 1] from the Allocation.
            log_dict: diagnostic fields for backtest attribution.
        """
        # Step 1: AEMA smoothing (with circuit breaker bypass)
        self._s_t = update_aema(
            self._s_t, p_cp_raw, self._alpha_up, self._alpha_down,
            circuit_breaker=self._circuit_breaker,
        )

        # Step 2: Leverage mapping (SRD 4.2)
        l_target = compute_leverage(
            self._s_t, self._sigma_calm, self._sigma_stress, self._sigma_target,
        )

        # Step 3: Circuit breaker check
        circuit_triggered = self._s_t >= self._circuit_breaker

        # Step 4: Asymmetric deadband (SRD 4.4 — continuous L)
        l_actual = self._apply_deadband(l_target)

        # Step 5: Hold period enforcement (SRD 4.5)
        l_final = self._enforce_hold_period(l_actual, circuit_triggered)

        # Step 6: Update state tracking
        had_qld = self._l_current >= 1.0
        has_qld = l_final >= 1.0

        if has_qld:
            self._days_in_qld += 1
        else:
            self._days_in_qld = 0

        self._l_current = l_final

        # Step 7: Allocation (SRD 4.3)
        alloc = compute_allocation(l_final)
        self._weight = alloc.qld

        log = {
            "s_t":             self._s_t,
            "l_target":        l_target,
            "l_actual":        l_actual,
            "l_final":         l_final,
            "signal":          self._classify_signal(had_qld, has_qld),
            "weight":          alloc.qld,
            "days_held":       self._days_in_qld,
            "circuit_breaker": circuit_triggered,
            "qld":             alloc.qld,
            "qqq":             alloc.qqq,
            "cash":            alloc.cash,
        }
        return alloc.qld, log

    def get_weight(self) -> float:
        """Return the current QLD position weight."""
        return self._weight

    def get_state(self) -> dict:
        """Return a snapshot of the current allocator state."""
        return {
            "s_t":         self._s_t,
            "l_current":   self._l_current,
            "in_qld":      self._l_current >= 1.0,
            "days_held":   self._days_in_qld,
            "weight":      self._weight,
        }

    # ─────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────

    def _apply_deadband(self, l_target: float) -> float:
        """SRD 4.4: three-branch asymmetric deadband on continuous L.

        Returns:
            Adjusted leverage after deadband filter.
        """
        delta = l_target - self._l_current

        if delta < -self._delta_down:
            # De-lever: immediate full execution (protection priority)
            return l_target
        if delta > self._delta_up:
            # Re-lever: gradual recovery (conservative)
            return self._l_current + self._recovery_coeff * delta
        # Inside deadband: no adjustment
        return self._l_current

    def _enforce_hold_period(
        self,
        l_actual: float,
        circuit_triggered: bool,
    ) -> float:
        """SRD 4.5: block de-lever from QLD before min hold period.

        Only blocks transitions FROM QLD (L >= 1 → L < 1).
        Circuit breaker overrides the hold period.
        """
        currently_in_qld = self._l_current >= 1.0
        would_exit_qld   = l_actual < 1.0

        if currently_in_qld and would_exit_qld:
            if circuit_triggered:
                return l_actual   # emergency exit allowed
            if self._days_in_qld < self._min_hold:
                return self._l_current  # block: hold period not met
        return l_actual

    @staticmethod
    def _classify_signal(had_qld: bool, has_qld: bool) -> str:
        """Classify the transition for logging."""
        if not had_qld and has_qld:
            return "ENTER_QLD"
        if had_qld and not has_qld:
            return "EXIT_QLD"
        return "HOLD"
