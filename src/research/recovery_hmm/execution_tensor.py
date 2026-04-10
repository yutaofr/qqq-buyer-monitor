"""Hardcoded shadow execution tensor for the recovery HMM research track."""

from __future__ import annotations

BASE_WEIGHTS = {
    "RECOVERY": 1.0,
    "MID_CYCLE": 1.0,
    "LATE_CYCLE": 0.5,
    "BUST": 0.3,
}


def _entropy_multiplier(
    entropy: float,
    *,
    threshold: float = 0.65,
    slope: float = 2.5,
    floor: float = 0.3,
) -> float:
    if entropy <= threshold:
        return 1.0
    return max(float(floor), 1.0 - (float(slope) * (float(entropy) - float(threshold))))


def compute_shadow_weight(
    *,
    state: str,
    entropy: float,
    fdas_triggered: bool,
    preserve_production_floor: bool = True,
    production_floor: float = 0.5,
    base_weights: dict[str, float] | None = None,
    entropy_threshold: float = 0.65,
    entropy_slope: float = 2.5,
    entropy_floor: float = 0.3,
    fdas_multiplier: float = 0.15,
) -> dict[str, float]:
    effective_base_weights = BASE_WEIGHTS if base_weights is None else base_weights
    w_base = float(effective_base_weights[state])
    m_entropy = float(
        _entropy_multiplier(
            entropy,
            threshold=entropy_threshold,
            slope=entropy_slope,
            floor=entropy_floor,
        )
    )
    m_fdas = float(fdas_multiplier) if fdas_triggered else 1.0
    w_final_raw = w_base * m_entropy * m_fdas
    w_final = (
        max(float(production_floor), w_final_raw) if preserve_production_floor else w_final_raw
    )
    return {
        "w_base": w_base,
        "m_entropy": m_entropy,
        "m_fdas": float(m_fdas),
        "w_final_raw": float(w_final_raw),
        "w_final": float(w_final),
    }
