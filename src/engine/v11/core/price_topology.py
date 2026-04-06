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
    confidence = float(np.clip(margin / max(1e-6, confidence_margin), 0.0, 1.0))
    return PriceTopologyState(
        regime=str(latest["benchmark_regime"]),
        probabilities=probabilities,
        expected_beta=float(latest["benchmark_expected_beta"]),
        confidence=confidence,
        posterior_blend_weight=float(max(0.0, posterior_blend_weight) * confidence),
        beta_anchor_weight=float(max(0.0, beta_anchor_weight) * confidence),
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
    penalties: dict[str, float] = {}
    for regime in ACTIVE_REGIME_ORDER:
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
        "posterior_blend_weight": float(topology.posterior_blend_weight),
        "beta_anchor_weight": float(topology.beta_anchor_weight),
        "probabilities": {regime: float(topology.probabilities.get(regime, 0.0)) for regime in ACTIVE_REGIME_ORDER},
    }
