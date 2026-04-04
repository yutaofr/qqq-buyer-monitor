import json
import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from src.engine.v11.core.data_quality import (
    apply_data_quality_penalty,
    normalize_source_marker,
    detect_source_switch,
    assess_data_quality,
    feature_reliability_weights,
)

@pytest.fixture
def snapshot():
    path = Path("tests/fixtures/forensics/snapshot_2026-03-31.json")
    with open(path) as f:
        return json.load(f)

def test_apply_data_quality_penalty_matches_current_conductor_behavior():
    # Conductor formula: 1.0 - ((1.0 - h) * q)
    h = 0.6
    q = 0.5
    expected = 1.0 - ((1.0 - h) * q)
    assert apply_data_quality_penalty(posterior_entropy=h, quality_score=q) == expected

def test_assess_data_quality_returns_expected_reason_for_missing_core_field(snapshot):
    latest_raw = pd.Series(snapshot["raw_t0_data"][0])
    # Core field in v13_4_registry is "credit_spread" (default) or from registry
    # Let's mock a case where credit_spread_bps is NaN
    latest_raw_missing = latest_raw.copy()
    latest_raw_missing["credit_spread_bps"] = np.nan
    
    registry = {
        "feature_weight_matrix": {},
        "quality_transfer_function": {"direct": 1.0},
        "core_fields": ["credit_spread"]
    }
    
    field_specs = {
        "credit_spread": ("credit_spread_bps", "source_credit_spread", None),
    }
    
    result = assess_data_quality(
        latest_raw=latest_raw_missing,
        previous_raw=None,
        registry=registry,
        field_specs=field_specs
    )
    # q_core becomes len(core_qs) / sum(1.0 / (max(0.0, q) + epsilon))
    # q for credit_spread is 0.0 because it's missing.
    # q_core = 1 / (1 / (0 + 0.01)) = 0.01.
    # 0.01 < 0.15 => CORE_SENSOR_FAILURE
    assert result["reason"] == "CORE_SENSOR_FAILURE"
    assert result["quality_score"] < 0.15

def test_feature_reliability_weights_zero_out_missing_raw_features(snapshot):
    latest_raw = pd.Series(snapshot["raw_t0_data"][0])
    latest_raw["credit_spread_bps"] = np.nan
    
    latest_vector = pd.DataFrame(snapshot["feature_vector"])
    # "spread_21d" uses "credit_spread_bps"
    
    field_quality = {
        "credit_spread": 0.0,
        "net_liquidity": 1.0,
        "real_yield": 1.0,
        "treasury_vol": 1.0,
        "copper_gold": 1.0,
        "breakeven": 1.0,
        "core_capex": 1.0,
        "usdjpy": 1.0,
        "erp_ttm": 1.0,
    }
    
    seeder_config = {
        "spread_21d": {"src": "credit_spread_bps"},
        "liquidity_252d": {"src": "net_liquidity_usd_bn"}
    }
    
    weights = feature_reliability_weights(
        latest_vector=latest_vector,
        latest_raw=latest_raw,
        field_quality=field_quality,
        seeder_config=seeder_config
    )
    
    assert weights["spread_21d"] == 0.0
    assert weights["liquidity_252d"] == 1.0

def test_detect_source_switch_flags_build_version_change(snapshot):
    latest_raw = pd.Series(snapshot["raw_t0_data"][0])
    previous_raw = latest_raw.copy()
    previous_raw["build_version"] = "OLD_VERSION"
    latest_raw["build_version"] = "NEW_VERSION"
    
    result = detect_source_switch(latest_raw, previous_raw=previous_raw)
    assert result["detected"] is True
    assert "build_version" in result["changed_fields"]
