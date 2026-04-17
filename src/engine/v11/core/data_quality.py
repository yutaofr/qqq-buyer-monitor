import numpy as np
import pandas as pd


def apply_data_quality_penalty(*, posterior_entropy: float, quality_score: float) -> float:
    """Calculates effective entropy by penalizing low data quality."""
    h = float(np.clip(posterior_entropy, 0.0, 1.0))
    q = float(np.clip(quality_score, 0.0, 1.0))
    return 1.0 - ((1.0 - h) * q)


def normalize_source_marker(raw_source: object) -> str:
    """Standardizes source provenance string."""
    if raw_source is None or pd.isna(raw_source):
        return "missing:provenance"

    source = str(raw_source).strip()
    if not source or source.lower() in {"nan", "none", "null"}:
        return "missing:provenance"
    return source


def detect_source_switch(
    latest_raw: pd.Series,
    *,
    previous_raw: pd.Series | None = None,
    field_specs: dict[str, tuple[str, str | None, str | None]] | None = None,
) -> dict[str, object]:
    """Detects shifts in data provenance or build versions between runs."""
    if previous_raw is None:
        return {
            "detected": False,
            "changed_fields": [],
            "previous_build_version": None,
            "current_build_version": str(latest_raw.get("build_version", "")) or None,
        }

    # Use field_specs to find source keys if provided, else use defaults
    source_fields = {}
    if field_specs:
        source_fields = {
            field: source_key for field, (_, source_key, _) in field_specs.items() if source_key
        }

    changed_fields: list[str] = []
    for field_name, source_key in source_fields.items():
        previous_source = normalize_source_marker(previous_raw.get(source_key))
        current_source = normalize_source_marker(latest_raw.get(source_key))
        if previous_source and current_source and previous_source != current_source:
            changed_fields.append(field_name)

    previous_build_version = str(previous_raw.get("build_version", "") or "")
    current_build_version = str(latest_raw.get("build_version", "") or "")
    if (
        previous_build_version
        and current_build_version
        and previous_build_version != current_build_version
    ):
        changed_fields.append("build_version")

    return {
        "detected": bool(changed_fields),
        "changed_fields": sorted(set(changed_fields)),
        "previous_build_version": previous_build_version or None,
        "current_build_version": current_build_version or None,
    }


def assess_data_quality(
    latest_raw: pd.Series,
    *,
    previous_raw: pd.Series | None,
    registry: dict[str, object],
    field_specs: dict[str, tuple[str, str | None, str | None]],
) -> dict[str, object]:
    """v13.4 Tiered Quality Scoring: Core Veto + Support Robustness."""

    weights_matrix = registry.get("feature_weight_matrix", {})
    q_transfer = registry.get("quality_transfer_function", {})
    core_fields = set(registry.get("core_fields", ["credit_spread"]))

    fields: dict[str, dict[str, object]] = {}
    quality_values: dict[str, float] = {}
    degraded_present = False
    missing_present = False

    for field_name, (value_key, source_key, _quality_key) in field_specs.items():
        raw_value = latest_raw.get(value_key)
        numeric_value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
        available = bool(pd.notna(numeric_value) and np.isfinite(float(numeric_value)))
        source = normalize_source_marker(latest_raw.get(source_key)) if source_key else "direct"

        if not available:
            field_quality = 0.0
        elif source == "direct":
            field_quality = float(q_transfer.get("direct", 1.0))
        else:
            # Find best matching prefix in q_transfer
            matched_q = 1.0
            found = False
            for prefix, q_val in q_transfer.items():
                if prefix.endswith(":") and source.startswith(prefix):
                    matched_q = float(q_val)
                    found = True
                    break
            if not found:
                matched_q = float(q_transfer.get(source, 1.0))
            field_quality = matched_q

        degraded = field_quality < 1.0 and available
        degraded_present = degraded_present or degraded
        missing_present = missing_present or not available
        quality_values[field_name] = field_quality

        fields[field_name] = {
            "available": available,
            "source": source,
            "degraded": degraded,
            "quality": field_quality,
        }

    # 1. Level 1 (Core) - Smoothed Harmonic Mean
    epsilon = 0.01
    core_qs = [quality_values[f] for f in core_fields if f in quality_values]
    if core_qs:
        q_core = len(core_qs) / sum(1.0 / (max(0.0, q) + epsilon) for q in core_qs)
    else:
        q_core = 1.0

    # 2. Level 2-5 (Support) - Weighted Arithmetic Mean
    support_q_pairs = []
    for f, q in quality_values.items():
        if f not in core_fields:
            w = float(weights_matrix.get(f, 1.0))
            support_q_pairs.append((q, w))

    if support_q_pairs:
        total_w = sum(w for _, w in support_q_pairs)
        q_support = sum(q * w for q, w in support_q_pairs) / total_w
    else:
        q_support = 1.0

    quality_score = float(np.clip(q_core * q_support, 0.0, 1.0))

    source_switch = detect_source_switch(
        latest_raw, previous_raw=previous_raw, field_specs=field_specs
    )
    if source_switch["detected"]:
        reason = "SOURCE_SWITCH"
    elif q_core < 0.15:
        reason = "CORE_SENSOR_FAILURE"
    elif degraded_present:
        reason = "DEGRADED_SOURCE"
    elif missing_present:
        reason = "SENSOR_DEGRADATION"
    else:
        reason = "V13_PROBABILISTIC_OPTIMAL"

    return {
        "quality_score": quality_score,
        "reason": reason,
        "fields": fields,
        "source_switch": source_switch,
        "q_core": q_core,
        "q_support": q_support,
    }


def feature_reliability_weights(
    *,
    latest_vector: pd.DataFrame,
    latest_raw: pd.Series,
    field_quality: dict[str, float],
    seeder_config: dict[str, dict[str, object]],
) -> dict[str, float]:
    """Maps field-level quality to individual feature weights."""

    source_to_field = {
        "credit_spread_bps": "credit_spread",
        "net_liquidity_usd_bn": "net_liquidity",
        "liquidity_roc_pct_4w": "net_liquidity",
        "real_yield_10y_pct": "real_yield",
        "treasury_vol_21d": "treasury_vol",
        "copper_gold_ratio": "copper_gold",
        "breakeven_10y": "breakeven",
        "core_capex_mm": "core_capex",
        "usdjpy": "usdjpy",
        "erp_ttm_pct": "erp_ttm",
    }

    weights: dict[str, float] = {}
    for feature_name in latest_vector.columns:
        src = seeder_config.get(feature_name, {}).get("src")
        raw_value = latest_raw.get(src)
        numeric_value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
        if pd.isna(numeric_value) or not np.isfinite(float(numeric_value)):
            weights[str(feature_name)] = 0.0
            continue

        field_name = source_to_field.get(str(src))
        quality = float(np.clip(field_quality.get(field_name, 1.0), 0.0, 1.0))
        weights[str(feature_name)] = quality

    return weights
