"""v7.0 Feature Pipeline — unified data quality and classification layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Class A: production hard-decision data (enters Risk Controller)
_CLASS_A = frozenset({
    "credit_spread",
    "credit_acceleration",
    "net_liquidity",
    "liquidity_roc",
    "real_yield",
    "funding_stress",
    "close",
})

# Class B: production soft-decision data (enters Deployment Controller / overlays)
_CLASS_B = frozenset({
    "vix",
    "breadth",
    "fear_greed",
    "put_wall",
    "call_wall",
    "gamma_flip",
    "tactical_stress_score",
    "capitulation_score",
    "persistence_score",
})

# Everything else: Class C — informational / research placeholder only


def _classify(name: str) -> str:
    if name in _CLASS_A:
        return "A"
    if name in _CLASS_B:
        return "B"
    return "C"


@dataclass(frozen=True)
class FeatureSnapshot:
    """Immutable snapshot of all input features for one market day."""
    market_date: date
    values: dict   # feature_name -> raw value (float | bool | None)
    quality: dict  # feature_name -> {source, stale_days, usable, decision_critical}
    classes: dict  # feature_name -> "A" | "B" | "C"


def build_feature_snapshot(
    market_date: date,
    raw_values: dict,
    raw_quality: dict,
) -> FeatureSnapshot:
    """
    Build a FeatureSnapshot from raw collected values.

    Args:
        market_date: The trading date this snapshot represents.
        raw_values: {feature_name: value}.  None means data unavailable.
        raw_quality: {feature_name: {source, stale_days, ...}} partial quality metadata.

    Returns:
        An immutable FeatureSnapshot with class labels and decision_critical flags.
    """
    classes: dict[str, str] = {}
    quality: dict[str, dict] = {}

    for name, value in raw_values.items():
        feature_class = _classify(name)
        classes[name] = feature_class

        # Start from provided quality metadata, fill in missing fields
        q = dict(raw_quality.get(name, {}))
        q.setdefault("source", "unknown")
        q.setdefault("stale_days", 0)
        q["usable"] = value is not None
        # Only Class A features are decision-critical (SRD AC-5 / §8.1)
        q["decision_critical"] = feature_class == "A"
        quality[name] = q

    return FeatureSnapshot(
        market_date=market_date,
        values=dict(raw_values),
        quality=quality,
        classes=classes,
    )
