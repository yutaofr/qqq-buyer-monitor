"""Asymmetric execution deadband.

SRD v1.2 Section 4.3: Prevents position churn from small oscillations
in the stress signal. Uses different thresholds for entry vs exit.

Architecture:
    - DeadbandState: immutable snapshot of current position state.
    - DeadbandSignal: enum of HOLD | ENTER_QLD | EXIT_QLD.
    - update_deadband(): pure transition function.

Threshold logic:
    When NOT in QLD:
        ENTER_QLD if s_t < entry_threshold
        entry_threshold is derived from the last known exit_threshold:
            entry = exit_threshold - recovery_coeff * delta_up
        If no prior exit_threshold (first time), use delta_down as threshold:
            entry_threshold = delta_down

    When IN QLD:
        EXIT_QLD  if s_t > exit_threshold OR s_t > circuit_breaker
        exit_threshold is set at entry: exit_threshold = s_t + delta_up
        (the band moves with the stress level at entry)
        Else: HOLD

    days_held: incremented each step while in_qld, reset to 0 on exit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class DeadbandSignal(Enum):
    HOLD       = auto()
    ENTER_QLD  = auto()
    EXIT_QLD   = auto()


@dataclass
class DeadbandState:
    in_qld:          bool
    exit_threshold:  float | None   # stress level that triggers exit; set at entry
    days_held:       int            # trading days held in QLD (reset on exit)


def update_deadband(
    state: DeadbandState,
    s_t: float,
    params: dict,
) -> tuple[DeadbandState, DeadbandSignal]:
    """Compute one step of the asymmetric deadband transition.

    Args:
        state:    Current DeadbandState.
        s_t:      Current smoothed stress from AEMA.
        params:   Dict with keys: delta_down, delta_up, recovery_coeff,
                  circuit_breaker.

    Returns:
        (new_state, signal)
    """
    delta_down      = params["delta_down"]
    delta_up        = params["delta_up"]
    recovery_coeff  = params["recovery_coeff"]
    circuit_breaker = params["circuit_breaker"]

    if state.in_qld:
        # ── In QLD: check for exit conditions ──────────────────────────
        is_circuit_break = s_t >= circuit_breaker
        is_normal_exit   = (
            state.exit_threshold is not None and s_t >= state.exit_threshold
        )

        if is_circuit_break or is_normal_exit:
            new_state = DeadbandState(
                in_qld=False,
                exit_threshold=state.exit_threshold,  # remember for re-entry calc
                days_held=0,
            )
            return new_state, DeadbandSignal.EXIT_QLD

        # Still holding — increment counter
        new_state = DeadbandState(
            in_qld=True,
            exit_threshold=state.exit_threshold,
            days_held=state.days_held + 1,
        )
        return new_state, DeadbandSignal.HOLD

    else:
        # ── Not in QLD: check for entry condition ───────────────────────
        if state.exit_threshold is not None:
            # Use recovery-adjusted re-entry threshold (conservative)
            entry_threshold = state.exit_threshold - recovery_coeff * delta_up
        else:
            # First-ever entry: use delta_down as the entry threshold
            entry_threshold = delta_down

        if s_t < entry_threshold:
            # Enter QLD — set the exit threshold dynamically
            new_exit_threshold = s_t + delta_up
            new_state = DeadbandState(
                in_qld=True,
                exit_threshold=new_exit_threshold,
                days_held=1,  # day 1 in QLD
            )
            return new_state, DeadbandSignal.ENTER_QLD

        # Stay out
        new_state = DeadbandState(
            in_qld=False,
            exit_threshold=state.exit_threshold,
            days_held=0,
        )
        return new_state, DeadbandSignal.HOLD
