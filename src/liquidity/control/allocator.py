"""Control chain orchestrator: AEMA → Deadband → HoldPeriod → Weight.

SRD v1.2 Section 4: Integrates all control modules into a single stateful
step function that the backtest runner calls once per trading day.

Data flow:
    p_cp_raw (BOCPD) → AEMA → s_t → Deadband → signal → HoldPeriod → weight

Output:
    target_weight: 0.0 (QQQ only) | 1.0 (full QLD)
    POC uses binary allocation. Production extension: continuous L ∈ [1,2]
    via leverage mapping (SRD 4.4), omitted from POC scope.

State is encapsulated inside the Allocator instance.
"""

from __future__ import annotations

from src.liquidity.control.aema import update_aema
from src.liquidity.control.deadband import (
    DeadbandSignal,
    DeadbandState,
    update_deadband,
)
from src.liquidity.control.hold_period import HoldPeriodGuard


class Allocator:
    """Stateful control chain executor.

    One instance per backtest segment. Do not share across segments
    (state is not reset between calls).

    Args:
        config: Full parameter dict from load_config().
    """

    def __init__(self, config: dict) -> None:
        aema_cfg    = config["aema"]
        deadband_cfg = config["deadband"]
        hold_cfg    = config["hold_period"]

        self._alpha_up         = aema_cfg["alpha_up"]
        self._alpha_down       = aema_cfg["alpha_down"]
        self._circuit_breaker  = aema_cfg["circuit_breaker"]
        self._deadband_params  = {
            "delta_down":     deadband_cfg["delta_down"],
            "delta_up":       deadband_cfg["delta_up"],
            "recovery_coeff": deadband_cfg["recovery_coeff"],
            "circuit_breaker": aema_cfg["circuit_breaker"],
        }
        self._guard = HoldPeriodGuard(min_hold_days=hold_cfg["min_qld_hold_days"])

        # Mutable state
        self._s_t: float = 0.0
        self._db_state: DeadbandState = DeadbandState(
            in_qld=False,
            exit_threshold=None,
            days_held=0,
        )
        self._weight: float = 0.0

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def step(
        self,
        p_cp_raw: float,
        lambda_macro: float,   # noqa: ARG002 — reserved for future leverage map
    ) -> tuple[float, dict]:
        """Execute one step of the control chain.

        Args:
            p_cp_raw:     Raw changepoint probability from BOCPDEngine.update().
            lambda_macro: Current macro hazard rate (reserved for continuous
                          leverage mapping in production; unused in POC).

        Returns:
            (target_weight, log_dict)
            target_weight: 0.0 or 1.0.
            log_dict: diagnostic fields for backtest attribution.
        """
        # Step 1: AEMA smoothing (with SRD 4.1 circuit breaker bypass)
        self._s_t = update_aema(
            self._s_t, p_cp_raw, self._alpha_up, self._alpha_down,
            circuit_breaker=self._circuit_breaker,
        )

        # Step 2: Circuit breaker check (before deadband)
        circuit_triggered = self._s_t >= self._circuit_breaker

        # Step 3: Deadband transition
        new_db_state, raw_signal = update_deadband(
            self._db_state, self._s_t, self._deadband_params
        )

        # Step 4: Hold period enforcement
        enforced_signal = self._guard.enforce(
            signal=raw_signal,
            days_held=self._db_state.days_held,
            circuit_breaker_triggered=circuit_triggered,
        )

        # Step 5: Apply enforced signal to state and weight
        if enforced_signal == DeadbandSignal.ENTER_QLD:
            self._db_state = new_db_state
            self._weight = 1.0
        elif enforced_signal == DeadbandSignal.EXIT_QLD:
            # Override: guard may have blocked exit → use enforced result
            self._db_state = DeadbandState(
                in_qld=False,
                exit_threshold=new_db_state.exit_threshold,
                days_held=0,
            )
            self._weight = 0.0
        else:  # HOLD
            # Keep in_qld from raw transition (counter increments)
            # but override signal to HOLD
            self._db_state = new_db_state if raw_signal == DeadbandSignal.HOLD \
                else DeadbandState(
                    in_qld=self._db_state.in_qld,
                    exit_threshold=self._db_state.exit_threshold,
                    days_held=self._db_state.days_held + 1 if self._db_state.in_qld else 0,
                )
            # Weight unchanged

        log = {
            "s_t":             self._s_t,
            "signal":          enforced_signal.name,
            "weight":          self._weight,
            "days_held":       self._db_state.days_held,
            "circuit_breaker": circuit_triggered,
        }
        return self._weight, log

    def get_weight(self) -> float:
        """Return the current target position weight."""
        return self._weight

    def get_state(self) -> dict:
        """Return a snapshot of the current allocator state."""
        return {
            "s_t":            self._s_t,
            "in_qld":         self._db_state.in_qld,
            "exit_threshold": self._db_state.exit_threshold,
            "days_held":      self._db_state.days_held,
            "weight":         self._weight,
        }
