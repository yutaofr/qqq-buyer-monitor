"""Canonical regime topology helpers for the active v12 runtime contract."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

ACTIVE_REGIME_ORDER: tuple[str, ...] = (
    "MID_CYCLE",
    "LATE_CYCLE",
    "BUST",
    "RECOVERY",
)
ACTIVE_REGIME_SET = frozenset(ACTIVE_REGIME_ORDER)
LEGACY_REGIME_ALIASES: dict[str, str] = {
    "CAPITULATION": "RECOVERY",
}

REGIME_DISPLAY_MAP: dict[str, dict[str, str]] = {
    "MID_CYCLE": {
        "label": "中期平稳 (MID_CYCLE)",
        "desc": "周期中性平稳期，穿越波动的基准轨道。",
    },
    "LATE_CYCLE": {
        "label": "末端 (LATE_CYCLE)",
        "desc": "周期动能衰减，结构性风险增加，审慎缩减。",
    },
    "BUST": {
        "label": "休克 (BUST)",
        "desc": "信贷断裂引发流动性休克，强制避险。",
    },
    "RECOVERY": {
        "label": "修复 (RECOVERY)",
        "desc": "最差阶段已过，动能开始共振回归。",
    },
}

REGIME_HEX_COLORS: dict[str, str] = {
    "MID_CYCLE": "#3498db",
    "LATE_CYCLE": "#9b59b6",
    "BUST": "#e74c3c",
    "RECOVERY": "#2ecc71",
}


def canonicalize_regime_name(regime: object) -> str | None:
    """Map legacy aliases onto the supported active topology."""
    if regime is None:
        return None
    name = str(regime)
    if not name or name.lower() == "nan":
        return None
    return LEGACY_REGIME_ALIASES.get(name, name)


def canonicalize_regime_sequence(
    regimes: Iterable[object] | None,
    *,
    include_all: bool = False,
) -> list[str]:
    """Preserve input order while dropping unsupported legacy-only states."""
    ordered: list[str] = []
    seen: set[str] = set()
    for regime in regimes or ():
        canonical = canonicalize_regime_name(regime)
        if canonical not in ACTIVE_REGIME_SET or canonical in seen:
            continue
        ordered.append(canonical)
        seen.add(canonical)

    if include_all:
        for regime in ACTIVE_REGIME_ORDER:
            if regime not in seen:
                ordered.append(regime)
    return ordered


def merge_regime_weights(
    weights: Mapping[object, object] | None,
    *,
    regimes: Iterable[object],
    include_zeros: bool = False,
    normalize: bool = False,
) -> dict[str, float]:
    """Aggregate legacy weights onto the canonical active regime topology."""
    regime_order = tuple(canonicalize_regime_sequence(regimes, include_all=False))
    merged = {regime: 0.0 for regime in regime_order} if include_zeros else {}
    if weights:
        for regime, value in weights.items():
            canonical = canonicalize_regime_name(regime)
            if canonical not in regime_order:
                continue
            merged[canonical] = merged.get(canonical, 0.0) + _coerce_finite_float(value)

    if include_zeros:
        for regime in regime_order:
            merged.setdefault(regime, 0.0)

    if normalize:
        total = float(sum(max(0.0, value) for value in merged.values()))
        if total <= 0.0:
            if not merged:
                return {}
            uniform = 1.0 / len(merged)
            return {regime: uniform for regime in merged}
        return {regime: max(0.0, value) / total for regime, value in merged.items()}
    return merged


def merge_transition_matrix(
    transition_counts: Mapping[object, object] | None,
    *,
    regimes: Iterable[object],
) -> dict[str, dict[str, float]]:
    """Aggregate a transition matrix onto the canonical active regime topology."""
    regime_order = tuple(canonicalize_regime_sequence(regimes, include_all=False))
    merged = {source: {} for source in regime_order}
    if not transition_counts:
        return merged

    for source, row in transition_counts.items():
        canonical_source = canonicalize_regime_name(source)
        if canonical_source not in merged or not isinstance(row, Mapping):
            continue
        for target, value in row.items():
            canonical_target = canonicalize_regime_name(target)
            if canonical_target not in regime_order:
                continue
            merged[canonical_source][canonical_target] = merged[canonical_source].get(
                canonical_target, 0.0
            ) + _coerce_finite_float(value)
    return merged


def _coerce_finite_float(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(numeric):
        return 0.0
    return numeric
