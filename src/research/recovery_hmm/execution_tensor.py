"""Hardcoded shadow execution tensor for the recovery HMM research track."""

from __future__ import annotations


BASE_WEIGHTS = {
    "RECOVERY": 1.0,
    "MID_CYCLE": 1.0,
    "LATE_CYCLE": 0.5,
    "BUST": 0.3,
}


def _entropy_multiplier(entropy: float) -> float:
    if entropy <= 0.65:
        return 1.0
    return max(0.3, 1.0 - 2.5 * (float(entropy) - 0.65))


def compute_shadow_weight(
    *,
    state: str,
    entropy: float,
    fdas_triggered: bool,
    preserve_production_floor: bool = True,
    production_floor: float = 0.5,
) -> dict[str, float]:
    w_base = float(BASE_WEIGHTS[state])
    m_entropy = float(_entropy_multiplier(entropy))
    m_fdas = 0.15 if fdas_triggered else 1.0
    w_final_raw = w_base * m_entropy * m_fdas
    w_final = max(float(production_floor), w_final_raw) if preserve_production_floor else w_final_raw
    return {
        "w_base": w_base,
        "m_entropy": m_entropy,
        "m_fdas": float(m_fdas),
        "w_final_raw": float(w_final_raw),
        "w_final": float(w_final),
    }
