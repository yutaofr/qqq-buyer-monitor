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
from src.liquidity.control.regime_vol_guard import RegimeVolatilityFloor
from src.liquidity.engine.regime_severity import (
    load_regime_severity_thresholds,
    normalize_regime_severity,
)


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
        severity_cfg = config.get("regime_severity", {})

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

        # Regime water-level risk, kept orthogonal to changepoint probability.
        self._severity_enabled = severity_cfg.get("enabled", False)
        self._severity_alpha_up = severity_cfg.get("alpha_up", self._alpha_up)
        self._severity_alpha_down = severity_cfg.get("alpha_down", self._alpha_down)
        self._severity_combine = severity_cfg.get("combine", "max")
        self._severity_floor = 0.0
        self._severity_ceil = 1.0
        if self._severity_enabled:
            thresholds = load_regime_severity_thresholds(config)
            self._severity_floor = float(thresholds["floor"])
            self._severity_ceil = float(thresholds["ceil"])

        # Volatility Guard (Zero-order level detector for crisis depth)
        vol_guard_cfg = config.get("regime_vol_guard", {})
        self._vol_guard_enabled = vol_guard_cfg.get("enabled", False)
        if self._vol_guard_enabled:
            spread_prior = config.get("nig_priors", {}).get("spread_anomaly", {})
            try:
                b0 = float(spread_prior.get("beta_0", 1.5))
                a0 = float(spread_prior.get("alpha_0", 2.5))
                abs_floor = b0 / (a0 - 1.0) if a0 > 1.0 else 0.0
            except ZeroDivisionError:
                abs_floor = 0.0

            self._vol_guard = RegimeVolatilityFloor(
                window=vol_guard_cfg.get("window", 252),
                quantile=vol_guard_cfg.get("quantile", 0.95),
                stress_max_leverage=vol_guard_cfg.get("stress_max_leverage", 0.50),
                min_obs=vol_guard_cfg.get("min_obs", 63),
                floor_alpha_down=vol_guard_cfg.get("floor_alpha_down", 0.02),
                abs_floor_variance=abs_floor,
            )
        else:
            self._vol_guard = None


        # ── Mutable state ──────────────────────────────────────
        self._s_cp_t: float        = 0.0
        self._s_level_t: float     = 0.0
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
        regime_severity_raw: float = 0.0,
        regime_sigma2_spread: float | None = None,
        qqq_price: float | None = None,
        qqq_sma200: float | None = None,
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
        # Step 1: AEMA smoothing (with circuit breaker bypass) for p_cp.
        self._s_cp_t = update_aema(
            self._s_cp_t, p_cp_raw, self._alpha_up, self._alpha_down,
            circuit_breaker=self._circuit_breaker,
        )
        regime_severity_norm = 0.0
        if self._severity_enabled:
            regime_severity_norm = normalize_regime_severity(
                regime_severity_raw,
                floor=self._severity_floor,
                ceil=self._severity_ceil,
            )
            self._s_level_t = update_aema(
                self._s_level_t,
                regime_severity_norm,
                self._severity_alpha_up,
                self._severity_alpha_down,
                circuit_breaker=self._circuit_breaker,
            )
        else:
            self._s_level_t = 0.0

        if self._severity_combine == "max":
            self._s_t = max(self._s_cp_t, self._s_level_t)
        else:
            raise ValueError(f"Unsupported regime_severity.combine={self._severity_combine!r}")

        # Step 2: Leverage mapping (SRD 4.2)
        l_target = compute_leverage(
            self._s_t, self._sigma_calm, self._sigma_stress, self._sigma_target,
        )

        vol_guard_cap = 2.0
        if self._vol_guard_enabled and regime_sigma2_spread is not None:
            vol_guard_cap = self._vol_guard.update(regime_sigma2_spread)
            l_target = min(l_target, vol_guard_cap)

        # Step 2b: Momentum Lockout (SMA-200) - SRD 4.2.1
        momentum_lockout = False
        if qqq_price is not None and qqq_sma200 is not None and qqq_sma200 > 0:
            if qqq_price < qqq_sma200:
                momentum_lockout = True
                l_target = min(l_target, 1.0)

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
            "s_cp_t":          self._s_cp_t,
            "s_level_t":       self._s_level_t,
            "regime_severity_raw": regime_severity_raw,
            "regime_severity_norm": regime_severity_norm,
            "regime_severity_floor": self._severity_floor,
            "regime_severity_ceil": self._severity_ceil,
            "vol_guard_cap":   vol_guard_cap,
            "l_target":        l_target,
            "l_actual":        l_actual,
            "l_final":         l_final,
            "signal":          self._classify_signal(had_qld, has_qld),
            "weight":          alloc.qld,
            "days_held":       self._days_in_qld,
            "circuit_breaker": circuit_triggered,
            "momentum_lockout": momentum_lockout,
            "qld":             alloc.qld,
            "qqq":             alloc.qqq,
            "cash":            alloc.cash,
        }
        return alloc.qld, log

    @property
    def current_leverage(self) -> float:
        """Get the current requested target leverage L_target."""
        return getattr(self, "_l_current", 0.0)

    def dump_state(self) -> dict:
        state = {
            "s_cp_t": self._s_cp_t,
            "s_level_t": self._s_level_t,
            "s_t": self._s_t,
            "l_current": self._l_current,
            "days_in_qld": self._days_in_qld,
            "weight": self._weight,
        }
        if self._vol_guard_enabled:
            state["vol_guard"] = self._vol_guard.dump_state()
        return state

    def load_state(self, state_dict: dict) -> None:
        self._s_cp_t = state_dict["s_cp_t"]
        self._s_level_t = state_dict["s_level_t"]
        self._s_t = state_dict["s_t"]
        self._l_current = state_dict["l_current"]
        self._days_in_qld = state_dict["days_in_qld"]
        self._weight = state_dict["weight"]
        if self._vol_guard_enabled and "vol_guard" in state_dict:
            self._vol_guard.load_state(state_dict["vol_guard"])

    def get_weight(self) -> float:
        """Return the current QLD position weight."""
        return self._weight

    def get_state(self) -> dict:
        """Return a snapshot of the current allocator state."""
        return {
            "s_t":         self._s_t,
            "s_cp_t":      self._s_cp_t,
            "s_level_t":   self._s_level_t,
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
        import numpy as np
        delta = l_target - self._l_current

        if delta < -self._delta_down:
            # De-lever: immediate full execution (protection priority)
            return l_target

        if delta > 0:
            # Mathematics for AEMA compatibility: use a relative remaining gap
            # instead of absolute delta so Zeno's paradox won't trap the recovery.
            # We use dynamic ceiling (1.0 for defense phase, 2.0 for aggro phase)
            ceiling = float(np.ceil(l_target))
            if ceiling < 1.0:
                ceiling = 1.0

            relative_gap = delta / (ceiling - self._l_current + 1e-6)

            if relative_gap > self._delta_up:
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
