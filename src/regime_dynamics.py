"""Helpers for posterior regime probability motion and serialization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from src.regime_topology import ACTIVE_REGIME_ORDER, merge_regime_weights


def _normalized_weights(
    weights: Mapping[str, float] | None,
    *,
    regimes: Iterable[str],
) -> dict[str, float]:
    return merge_regime_weights(
        weights,
        regimes=regimes,
        include_zeros=True,
        normalize=True,
    )


def _trend_label(delta: float, *, tolerance: float = 1e-6) -> str:
    if delta > tolerance:
        return "RISING"
    if delta < -tolerance:
        return "FALLING"
    return "FLAT"


def compute_probability_dynamics(
    current: Mapping[str, float] | None,
    *,
    previous: Mapping[str, float] | None = None,
    previous_previous: Mapping[str, float] | None = None,
    regimes: Iterable[str] = ACTIVE_REGIME_ORDER,
) -> dict[str, dict[str, float | str]]:
    ordered_regimes = tuple(regimes)
    current_weights = _normalized_weights(current, regimes=ordered_regimes)
    previous_weights = _normalized_weights(previous, regimes=ordered_regimes) if previous else None
    previous_previous_weights = (
        _normalized_weights(previous_previous, regimes=ordered_regimes)
        if previous_previous
        else None
    )

    dynamics: dict[str, dict[str, float | str]] = {}
    for regime in ordered_regimes:
        probability = float(round(current_weights.get(regime, 0.0), 10))
        delta = 0.0
        acceleration = 0.0

        if previous_weights is not None:
            delta = float(round(probability - previous_weights.get(regime, 0.0), 10))

        if previous_weights is not None and previous_previous_weights is not None:
            previous_delta = previous_weights.get(regime, 0.0) - previous_previous_weights.get(
                regime, 0.0
            )
            acceleration = float(round(delta - previous_delta, 10))

        dynamics[regime] = {
            "probability": probability,
            "delta_1d": delta,
            "acceleration_1d": acceleration,
            "trend": _trend_label(delta),
        }

    return dynamics


def flatten_probability_dynamics(
    dynamics: Mapping[str, Mapping[str, float | str]] | None,
) -> dict[str, float | str]:
    flat: dict[str, float | str] = {}
    for regime, payload in dict(dynamics or {}).items():
        flat[f"prob_delta_{regime}"] = float(payload.get("delta_1d", 0.0))
        flat[f"prob_acceleration_{regime}"] = float(payload.get("acceleration_1d", 0.0))
        flat[f"prob_trend_{regime}"] = str(payload.get("trend", "FLAT"))
    return flat
