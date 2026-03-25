"""TDD: Feature pipeline — Class A/B/C classification + decision_critical guard."""
from datetime import date

from src.engine.feature_pipeline import build_feature_snapshot


# ── Task 3 ────────────────────────────────────────────────────────────────────

def test_feature_pipeline_marks_class_a_data():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": 350.0},
        raw_quality={"credit_spread": {"source": "live"}},
    )
    assert snapshot.classes["credit_spread"] == "A"
    assert snapshot.quality["credit_spread"]["source"] == "live"
    assert snapshot.quality["credit_spread"]["decision_critical"] is True


def test_feature_pipeline_marks_class_b_data():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"fear_greed": 20},
        raw_quality={},
    )
    assert snapshot.classes["fear_greed"] == "B"
    assert snapshot.quality["fear_greed"]["decision_critical"] is False


def test_feature_pipeline_marks_missing_as_class_c():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"sector_rotation": None},
        raw_quality={},
    )
    assert snapshot.classes["sector_rotation"] == "C"
    assert snapshot.quality["sector_rotation"]["usable"] is False


def test_feature_pipeline_multi_class():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={
            "credit_spread": 350.0,
            "fear_greed": 20,
            "sector_rotation": None,
        },
        raw_quality={"credit_spread": {"source": "live"}, "fear_greed": {"source": "live"}},
    )
    assert snapshot.classes["credit_spread"] == "A"
    assert snapshot.classes["fear_greed"] == "B"
    assert snapshot.classes["sector_rotation"] == "C"


def test_feature_snapshot_is_immutable():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": 350.0},
        raw_quality={},
    )
    import pytest
    with pytest.raises((TypeError, AttributeError)):
        snapshot.market_date = date(2025, 1, 1)  # type: ignore


# ── Task 4 ────────────────────────────────────────────────────────────────────

def test_class_c_feature_is_non_decision_critical():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"sector_rotation": 1.0},
        raw_quality={},
    )
    assert snapshot.quality["sector_rotation"]["decision_critical"] is False


def test_class_a_feature_is_decision_critical():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"net_liquidity": 500.0},
        raw_quality={},
    )
    assert snapshot.quality["net_liquidity"]["decision_critical"] is True


def test_removing_class_c_does_not_affect_class_a_quality():
    """Confirms SRD AC-6: Class C removal must not change Class A data classification."""
    snap_with_c = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": 350.0, "sector_rotation": 1.0},
        raw_quality={},
    )
    snap_without_c = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": 350.0},
        raw_quality={},
    )
    assert snap_with_c.classes["credit_spread"] == snap_without_c.classes["credit_spread"]
    assert snap_with_c.quality["credit_spread"]["decision_critical"] == snap_without_c.quality["credit_spread"]["decision_critical"]


def test_all_class_a_features_are_decision_critical():
    class_a_features = ["credit_spread", "credit_acceleration", "net_liquidity",
                        "liquidity_roc", "real_yield", "funding_stress", "close"]
    raw_values = {f: 1.0 for f in class_a_features}
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values=raw_values,
        raw_quality={},
    )
    for feat in class_a_features:
        assert snapshot.quality[feat]["decision_critical"] is True, f"{feat} should be decision_critical"


def test_usable_flag_false_when_value_is_none():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": None},
        raw_quality={},
    )
    assert snapshot.quality["credit_spread"]["usable"] is False


def test_usable_flag_true_when_value_present():
    snapshot = build_feature_snapshot(
        market_date=date(2026, 3, 24),
        raw_values={"credit_spread": 350.0},
        raw_quality={},
    )
    assert snapshot.quality["credit_spread"]["usable"] is True
