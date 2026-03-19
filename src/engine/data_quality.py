"""Feature quality metadata helpers for the live QQQ monitor."""
from __future__ import annotations

from typing import Any

from src.models import MarketData


def assess_feature_quality(
    value: Any,
    *,
    source: str,
    category: str,
    stale_days: int = 0,
) -> dict[str, Any]:
    """Return a normalized metadata record for a single feature."""
    return {
        "value": value,
        "source": source,
        "usable": value is not None,
        "stale_days": max(int(stale_days), 0),
        "category": category,
    }


def _feature_record(
    value: Any,
    *,
    category: str,
    default_source: str,
    feature_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    source = default_source if value is not None else "missing"
    stale_days = 0

    if feature_meta:
        if feature_meta.get("source") is not None:
            source = str(feature_meta["source"])
        if feature_meta.get("stale_days") is not None:
            stale_days = int(feature_meta["stale_days"])

    return assess_feature_quality(
        value,
        source=source,
        category=category,
        stale_days=stale_days,
    )


def build_data_quality(
    data: MarketData,
    feature_meta: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build the feature-quality surface for the current market snapshot."""
    feature_meta = feature_meta or {}
    forward_pe_source = "live"
    if data.pe_source and data.pe_source != "unknown":
        forward_pe_source = f"live:{data.pe_source}"

    return {
        "credit_spread": _feature_record(
            data.credit_spread,
            category="macro",
            default_source="live",
            feature_meta=feature_meta.get("credit_spread"),
        ),
        "forward_pe": _feature_record(
            data.forward_pe,
            category="fundamental",
            default_source=forward_pe_source,
            feature_meta=feature_meta.get("forward_pe"),
        ),
        "real_yield": _feature_record(
            data.real_yield,
            category="macro",
            default_source="live",
            feature_meta=feature_meta.get("real_yield"),
        ),
        "fcf_yield": _feature_record(
            data.fcf_yield,
            category="fundamental",
            default_source="live",
            feature_meta=feature_meta.get("fcf_yield"),
        ),
        "earnings_revisions_breadth": _feature_record(
            data.earnings_revisions_breadth,
            category="fundamental",
            default_source="live",
            feature_meta=feature_meta.get("earnings_revisions_breadth"),
        ),
        "short_vol_ratio": _feature_record(
            data.short_vol_ratio,
            category="flow",
            default_source="live",
            feature_meta=feature_meta.get("short_vol_ratio"),
        ),
    }
