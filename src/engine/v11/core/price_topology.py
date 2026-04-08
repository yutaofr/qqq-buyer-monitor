"""PIT-safe QQQ price-topology prior for posterior and beta alignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.engine.v11.core.expectation_surface import clamp_beta
from src.regime_topology import ACTIVE_REGIME_ORDER, merge_regime_weights
from src.research.worldview_benchmark import build_worldview_benchmark


@dataclass(frozen=True)
class PriceTopologyState:
    regime: str
    probabilities: dict[str, float]
    expected_beta: float
    confidence: float
    posterior_blend_weight: float
    beta_anchor_weight: float
    transition_intensity: float = 0.0
    recovery_impulse: float = 0.0
    damage_memory: float = 0.0
    bust_pressure: float = 0.0
    bullish_divergence: float = 0.0
    bearish_divergence: float = 0.0
    recovery_prob_delta: float = 0.0
    recovery_prob_acceleration: float = 0.0
    repair_persistence: float = 0.0

    @property
    def enabled(self) -> bool:
        return self.posterior_blend_weight > 0.0 or self.beta_anchor_weight > 0.0


def infer_price_topology_state(
    context_df: pd.DataFrame,
    *,
    posterior_blend_weight: float = 0.25,
    beta_anchor_weight: float = 0.35,
    confidence_margin: float = 0.25,
) -> PriceTopologyState:
    price_frame = _extract_price_frame(context_df)
    if price_frame is None or price_frame.empty:
        return PriceTopologyState(
            regime="MID_CYCLE",
            probabilities={regime: 1.0 / len(ACTIVE_REGIME_ORDER) for regime in ACTIVE_REGIME_ORDER},
            expected_beta=1.0,
            confidence=0.0,
            posterior_blend_weight=0.0,
            beta_anchor_weight=0.0,
            transition_intensity=0.0,
            recovery_impulse=0.0,
            damage_memory=0.0,
            bust_pressure=0.0,
            bullish_divergence=0.0,
            bearish_divergence=0.0,
            recovery_prob_delta=0.0,
            recovery_prob_acceleration=0.0,
        )

    benchmark = build_worldview_benchmark(price_frame)
    latest = benchmark.iloc[-1]
    probabilities = merge_regime_weights(
        {regime: float(latest[f"benchmark_prob_{regime}"]) for regime in ACTIVE_REGIME_ORDER},
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=True,
        normalize=True,
    )
    ordered = sorted(probabilities.values(), reverse=True)
    margin = float(ordered[0] - ordered[1]) if len(ordered) >= 2 else 0.0
    transition_intensity = float(np.clip(latest.get("benchmark_transition_intensity", 0.0), 0.0, 1.0))
    confidence = float(
        np.clip((margin / max(1e-6, confidence_margin)) * (1.0 - (0.55 * transition_intensity)), 0.0, 1.0)
    )
    edge_multiplier = 1.0 + confidence if str(latest["benchmark_regime"]) in {"BUST", "RECOVERY"} else 1.0
    transition_dampener = 1.0 - (0.35 * transition_intensity)
    recovery_impulse = float(np.clip(latest.get("benchmark_recovery_impulse", 0.0), 0.0, 1.5))
    damage_memory = float(np.clip(latest.get("benchmark_recent_damage", 0.0), 0.0, 1.5))
    bust_pressure = float(np.clip(latest.get("benchmark_bust_pressure", 0.0), 0.0, 1.5))
    bullish_divergence = float(
        np.clip(latest.get("benchmark_bullish_rsi_divergence", 0.0), 0.0, 1.5)
    )
    bearish_divergence = float(
        np.clip(latest.get("benchmark_bearish_rsi_divergence", 0.0), 0.0, 1.5)
    )
    recovery_prob_delta = float(latest.get("benchmark_prob_delta_RECOVERY", 0.0))
    recovery_prob_acceleration = float(latest.get("benchmark_prob_acceleration_RECOVERY", 0.0))
    return PriceTopologyState(
        regime=str(latest["benchmark_regime"]),
        probabilities=probabilities,
        expected_beta=float(latest["benchmark_expected_beta"]),
        confidence=confidence,
        posterior_blend_weight=float(
            np.clip(
                max(0.0, posterior_blend_weight) * confidence * edge_multiplier * transition_dampener,
                0.0,
                1.0,
            )
        ),
        beta_anchor_weight=float(
            np.clip(
                max(0.0, beta_anchor_weight) * confidence * edge_multiplier * transition_dampener,
                0.0,
                1.0,
            )
        ),
        transition_intensity=transition_intensity,
        recovery_impulse=recovery_impulse,
        damage_memory=damage_memory,
        bust_pressure=bust_pressure,
        bullish_divergence=bullish_divergence,
        bearish_divergence=bearish_divergence,
        recovery_prob_delta=recovery_prob_delta,
        recovery_prob_acceleration=recovery_prob_acceleration,
        repair_persistence=_repair_persistence_score(
            recovery_impulse=recovery_impulse,
            damage_memory=damage_memory,
            bust_pressure=bust_pressure,
            bullish_divergence=bullish_divergence,
            bearish_divergence=bearish_divergence,
            recovery_prob_delta=recovery_prob_delta,
            recovery_prob_acceleration=recovery_prob_acceleration,
        ),
    )


def blend_posteriors_with_topology(
    posteriors: dict[str, float],
    topology: PriceTopologyState,
) -> dict[str, float]:
    normalized = merge_regime_weights(
        posteriors,
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=True,
        normalize=True,
    )
    if topology.posterior_blend_weight <= 0.0:
        return normalized

    weight = float(np.clip(topology.posterior_blend_weight, 0.0, 1.0))
    blended = {
        regime: (1.0 - weight) * float(normalized.get(regime, 0.0))
        + weight * float(topology.probabilities.get(regime, 0.0))
        for regime in ACTIVE_REGIME_ORDER
    }
    return merge_regime_weights(
        blended,
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=True,
        normalize=True,
    )


def align_posteriors_with_recovery_process(
    posteriors: dict[str, float],
    topology: PriceTopologyState,
    *,
    max_shift: float = 0.22,
) -> dict[str, float]:
    normalized = merge_regime_weights(
        posteriors,
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=True,
        normalize=True,
    )
    weight = _recovery_process_alignment_weight(topology)
    benchmark_recovery = float(topology.probabilities.get("RECOVERY", 0.0))
    benchmark_bust = float(topology.probabilities.get("BUST", 0.0))
    current_recovery = float(normalized.get("RECOVERY", 0.0))
    current_bust = float(normalized.get("BUST", 0.0))
    current_late = float(normalized.get("LATE_CYCLE", 0.0))
    benchmark_late = float(topology.probabilities.get("LATE_CYCLE", 0.0))
    repair_persistence = _topology_repair_persistence(topology)
    if weight <= 0.0 or benchmark_recovery <= current_recovery + 1e-9:
        return normalized

    desired_uplift = benchmark_recovery - current_recovery
    bust_overhang = max(0.0, current_bust - benchmark_bust)
    late_overhang = max(0.0, current_late - benchmark_late)
    pair_dislocation = bust_overhang + (0.60 * late_overhang)
    adaptive_max_shift = max_shift + (0.06 * repair_persistence) + (0.10 * bust_overhang)
    release_scale = 1.0 + (0.45 * repair_persistence)
    uplift_capacity = max(adaptive_max_shift * weight, pair_dislocation * weight * release_scale)
    uplift = float(min(desired_uplift, uplift_capacity))
    if uplift <= 0.0:
        return normalized

    donor_candidates = {
        regime: max(0.0, float(normalized.get(regime, 0.0)) - float(topology.probabilities.get(regime, 0.0)))
        for regime in ACTIVE_REGIME_ORDER
        if regime != "RECOVERY"
    }
    donor_total = float(sum(donor_candidates.values()))
    if donor_total <= 1e-9:
        donor_candidates = {
            regime: float(normalized.get(regime, 0.0))
            for regime in ACTIVE_REGIME_ORDER
            if regime != "RECOVERY"
        }
        donor_total = float(sum(donor_candidates.values()))
        if donor_total <= 1e-9:
            return normalized

    corrected = dict(normalized)
    corrected["RECOVERY"] = current_recovery + uplift
    for regime, donor_weight in donor_candidates.items():
        corrected[regime] = max(0.0, corrected[regime] - (uplift * (donor_weight / donor_total)))
    return merge_regime_weights(
        corrected,
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=True,
        normalize=True,
    )


def topology_likelihood_penalties(
    topology: PriceTopologyState,
    *,
    floor: float = 0.03,
    exponent: float = 0.75,
) -> dict[str, float]:
    """Convert price-topology conviction into multiplicative likelihood penalties.

    The topology signal is treated as a trailer-risk veto. When the trailer has
    a clear state preference, low-probability macro regimes are explicitly
    down-weighted before posterior normalization instead of being left to a
    late-stage linear blend.
    """
    neutral = {regime: 1.0 for regime in ACTIVE_REGIME_ORDER}
    if topology.confidence <= 0.0:
        return neutral

    max_prob = max(float(prob) for prob in topology.probabilities.values())
    if max_prob <= 0.0:
        return neutral

    confidence_scale = float(np.clip(0.25 + (0.75 * topology.confidence), 0.0, 1.0))
    leader_bonus = (
        1.0 + (0.35 * float(topology.confidence))
        if topology.regime in {"BUST", "RECOVERY"}
        else 1.0
    )
    penalties: dict[str, float] = {}
    for regime in ACTIVE_REGIME_ORDER:
        if regime == topology.regime:
            penalties[regime] = float(leader_bonus)
            continue
        regime_prob = float(topology.probabilities.get(regime, 0.0))
        ratio = float(np.clip(regime_prob / max_prob, 0.0, 1.0))
        shaped = max(float(floor), ratio**float(exponent))
        penalties[regime] = (1.0 - confidence_scale) + (confidence_scale * shaped)
    return penalties


def anchor_beta_with_topology(raw_beta: float, topology: PriceTopologyState) -> float:
    if topology.beta_anchor_weight <= 0.0:
        return clamp_beta(raw_beta)
    weight = float(np.clip(topology.beta_anchor_weight, 0.0, 1.0))
    anchored = (1.0 - weight) * float(raw_beta) + weight * float(topology.expected_beta)
    return clamp_beta(anchored)


def _recovery_process_alignment_weight(topology: PriceTopologyState) -> float:
    if float(topology.recovery_impulse) < 0.15 or float(topology.damage_memory) < 0.20:
        return 0.0
    positive_delta = float(np.clip(topology.recovery_prob_delta / 0.04, 0.0, 1.5))
    positive_accel = float(np.clip(topology.recovery_prob_acceleration / 0.02, 0.0, 1.5))
    repair_persistence = _topology_repair_persistence(topology)
    benchmark_recovery = float(topology.probabilities.get("RECOVERY", 0.0))
    benchmark_bust = float(topology.probabilities.get("BUST", 0.0))
    recovery_edge = max(
        0.0,
        benchmark_recovery
        - max(
            benchmark_bust,
            float(topology.probabilities.get("LATE_CYCLE", 0.0)),
        ),
    )
    pair_gap = float(np.clip((benchmark_recovery - benchmark_bust) / 0.12, 0.0, 1.5))
    repair_score = (
        0.30 * float(topology.recovery_impulse)
        + 0.25 * float(topology.damage_memory)
        + 0.10 * float(topology.bullish_divergence)
        + 0.15 * positive_delta
        + 0.10 * positive_accel
        + 0.10 * recovery_edge
        + 0.20 * pair_gap
        + 0.18 * repair_persistence
        + (0.15 if topology.regime == "RECOVERY" else 0.0)
        + (0.15 if pair_gap > 0.0 else 0.0)
    )
    headwind = (0.15 * float(topology.bust_pressure)) + (0.10 * float(topology.bearish_divergence))
    transition_support = 0.75 + (0.25 * float(topology.transition_intensity))
    return float(np.clip((repair_score - headwind) * transition_support, 0.0, 1.0))


def _topology_repair_persistence(topology: PriceTopologyState) -> float:
    if float(topology.repair_persistence) > 0.0:
        return float(topology.repair_persistence)
    return _repair_persistence_score(
        recovery_impulse=float(topology.recovery_impulse),
        damage_memory=float(topology.damage_memory),
        bust_pressure=float(topology.bust_pressure),
        bullish_divergence=float(topology.bullish_divergence),
        bearish_divergence=float(topology.bearish_divergence),
        recovery_prob_delta=float(topology.recovery_prob_delta),
        recovery_prob_acceleration=float(topology.recovery_prob_acceleration),
    )


def _repair_persistence_score(
    *,
    recovery_impulse: float,
    damage_memory: float,
    bust_pressure: float,
    bullish_divergence: float,
    bearish_divergence: float,
    recovery_prob_delta: float,
    recovery_prob_acceleration: float,
) -> float:
    if recovery_impulse < 0.15 or damage_memory < 0.20:
        return 0.0
    positive_delta = float(np.clip(recovery_prob_delta / 0.03, 0.0, 1.5))
    if recovery_prob_acceleration >= 0.0:
        mild_fade_support = positive_delta
    else:
        fade_window = float(np.clip((0.012 + recovery_prob_acceleration) / 0.012, 0.0, 1.0))
        mild_fade_support = positive_delta * fade_window
    persistence_score = (
        0.38 * float(recovery_impulse)
        + 0.32 * float(damage_memory)
        + 0.12 * float(bullish_divergence)
        + 0.14 * positive_delta
        + 0.12 * mild_fade_support
        - 0.10 * float(bearish_divergence)
        - 0.08 * float(bust_pressure)
    )
    return float(np.clip(persistence_score, 0.0, 1.0))


def _extract_price_frame(context_df: pd.DataFrame) -> pd.DataFrame | None:
    if context_df is None or context_df.empty:
        return None

    frame = context_df.copy()
    if "observation_date" in frame.columns:
        frame = frame.set_index("observation_date")
    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index, errors="coerce")
    if frame.index.isna().all():
        return None

    close_col = next(
        (column for column in ("qqq_close", "Close", "close") if column in frame.columns),
        None,
    )
    if close_col is None:
        return None

    volume_col = next(
        (column for column in ("qqq_volume", "Volume", "volume") if column in frame.columns),
        None,
    )

    price_frame = pd.DataFrame(index=pd.to_datetime(frame.index, errors="coerce"))
    price_frame["Close"] = pd.to_numeric(frame[close_col], errors="coerce")
    if volume_col is not None:
        price_frame["Volume"] = pd.to_numeric(frame[volume_col], errors="coerce")

    price_frame = price_frame[price_frame.index.notna()]
    price_frame = price_frame.dropna(subset=["Close"])
    if price_frame.empty:
        return None
    return price_frame.sort_index()


def price_topology_payload(topology: PriceTopologyState) -> dict[str, Any]:
    return {
        "regime": topology.regime,
        "expected_beta": float(topology.expected_beta),
        "confidence": float(topology.confidence),
        "transition_intensity": float(topology.transition_intensity),
        "recovery_impulse": float(topology.recovery_impulse),
        "damage_memory": float(topology.damage_memory),
        "bust_pressure": float(topology.bust_pressure),
        "bullish_divergence": float(topology.bullish_divergence),
        "bearish_divergence": float(topology.bearish_divergence),
        "recovery_prob_delta": float(topology.recovery_prob_delta),
        "recovery_prob_acceleration": float(topology.recovery_prob_acceleration),
        "repair_persistence": float(_topology_repair_persistence(topology)),
        "recovery_process_weight": float(_recovery_process_alignment_weight(topology)),
        "posterior_blend_weight": float(topology.posterior_blend_weight),
        "beta_anchor_weight": float(topology.beta_anchor_weight),
        "probabilities": {regime: float(topology.probabilities.get(regime, 0.0)) for regime in ACTIVE_REGIME_ORDER},
    }
