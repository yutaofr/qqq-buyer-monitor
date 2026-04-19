from __future__ import annotations

import json

from scripts.final_product_patch import (
    FinalProductPatch,
    append_forward_oos_log_entry,
    materialize_recovery_relapsed_outcomes,
)


def _forward_row(
    day: int,
    *,
    dominant_stage: str = "LATE_CYCLE",
    secondary_stage: str = "EXPANSION",
    relapse_pressure: str = "LOW",
    boundary_flag: bool = False,
) -> dict:
    return {
        "timestamp": f"2026-04-{day:02d}T21:00:00Z",
        "market_date": f"2026-04-{day:02d}",
        "dominant_stage": dominant_stage,
        "secondary_stage": secondary_stage,
        "stage_probabilities": {
            "EXPANSION": 0.2,
            "LATE_CYCLE": 0.3,
            "STRESS": 0.2,
            "RECOVERY": 0.2,
            "FAST_CASCADE_BOUNDARY": 0.1,
        },
        "urgency": "ROUTINE",
        "action_relevance_band": "MONITOR",
        "relapse_pressure": relapse_pressure,
        "hazard_score": 0.4,
        "hazard_percentile": 0.7,
        "breadth_status": "mixed",
        "vol_status": "normal",
        "boundary_flag": boundary_flag,
        "rationale_summary": "test row",
        "product_version": "final-product-v1",
        "calibration_version": "balanced_product_patch",
        "ui_version": "daily-probability-dashboard-v2",
        "next_5d_return": None,
        "next_10d_return": None,
        "realized_drawdown_5d": None,
        "realized_drawdown_10d": None,
        "realized_stage_persistence_days": None,
        "recovery_relapsed": None,
    }


def test_forward_oos_monitoring_log_is_append_only_and_evaluation_ready(tmp_path):
    patch = FinalProductPatch(root=tmp_path)
    first = patch.build_monitoring_entry_from_dashboard(
        {
            "summary": {
                "date": "2026-04-19",
                "current_stage": "RECOVERY",
                "secondary_stage": "LATE_CYCLE",
                "short_rationale": "Recovery signal is present, but relapse pressure remains elevated.",
            },
            "stage_distribution": {
                "EXPANSION": 0.14,
                "LATE_CYCLE": 0.24,
                "STRESS": 0.18,
                "RECOVERY": 0.38,
                "FAST_CASCADE_BOUNDARY": 0.06,
            },
            "transition_urgency": "RISING",
            "action_band": "WATCH_CLOSELY",
            "relapse_pressure": {"level": "ELEVATED", "visible": True},
            "boundary_warning": {"is_active": False},
            "evidence_panel": {
                "hazard_score": 0.41,
                "hazard_percentile_context": {"percentile": 0.79},
                "breadth_health_status": {"status": "weak"},
                "volatility_regime_status": {"status": "elevated"},
            },
            "export_fields": {
                "boundary_flag": False,
                "rationale_summary": "Recovery signal is present, but relapse pressure remains elevated.",
            },
            "versions": {
                "product_version": "final-product-v1",
                "calibration_version": "balanced_product_patch",
                "ui_version": "daily-probability-dashboard-v2",
            },
        }
    )
    second = patch.build_monitoring_entry_from_dashboard(
        {
            "summary": {
                "date": "2026-04-20",
                "current_stage": "LATE_CYCLE",
                "secondary_stage": "STRESS",
                "short_rationale": "Transition zone with drift toward stress.",
            },
            "stage_distribution": {
                "EXPANSION": 0.17,
                "LATE_CYCLE": 0.33,
                "STRESS": 0.29,
                "RECOVERY": 0.11,
                "FAST_CASCADE_BOUNDARY": 0.10,
            },
            "transition_urgency": "HIGH",
            "action_band": "PREPARE_TO_ADJUST",
            "relapse_pressure": {"level": "LOW", "visible": False},
            "boundary_warning": {"is_active": False},
            "evidence_panel": {
                "hazard_score": 0.48,
                "hazard_percentile_context": {"percentile": 0.83},
                "breadth_health_status": {"status": "impaired"},
                "volatility_regime_status": {"status": "elevated"},
            },
            "export_fields": {
                "boundary_flag": False,
                "rationale_summary": "Transition zone with drift toward stress.",
            },
            "versions": {
                "product_version": "final-product-v1",
                "calibration_version": "balanced_product_patch",
                "ui_version": "daily-probability-dashboard-v2",
            },
        }
    )

    log_path = tmp_path / "artifacts" / "final_product" / "forward_oos_monitoring_log.jsonl"
    append_forward_oos_log_entry(first, log_path)
    append_forward_oos_log_entry(second, log_path)

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["market_date"] == "2026-04-19"
    assert rows[1]["market_date"] == "2026-04-20"
    assert rows[0]["relapse_pressure"] == "ELEVATED"
    assert rows[1]["dominant_stage"] == "LATE_CYCLE"
    assert rows[0]["next_5d_return"] is None
    assert rows[0]["next_10d_return"] is None
    assert rows[0]["realized_drawdown_5d"] is None
    assert rows[0]["recovery_relapsed"] is None


def test_forward_oos_monitoring_prevents_same_schema_duplicate_market_date(tmp_path):
    log_path = tmp_path / "artifacts" / "final_product" / "forward_oos_monitoring_log.jsonl"
    first = _forward_row(19, dominant_stage="RECOVERY", relapse_pressure="ELEVATED")
    rerun = dict(first)
    rerun["timestamp"] = "2026-04-19T22:15:00Z"
    rerun["rationale_summary"] = "rerun row with same schema identity"

    append_forward_oos_log_entry(first, log_path)
    append_forward_oos_log_entry(rerun, log_path)

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-04-19T21:00:00Z"
    assert rows[0]["rationale_summary"] == "test row"


def test_forward_oos_monitoring_allows_same_day_versioned_row(tmp_path):
    log_path = tmp_path / "artifacts" / "final_product" / "forward_oos_monitoring_log.jsonl"
    first = _forward_row(19, dominant_stage="RECOVERY")
    versioned = dict(first)
    versioned["timestamp"] = "2026-04-19T22:15:00Z"
    versioned["calibration_version"] = "balanced_product_patch_v2"

    append_forward_oos_log_entry(first, log_path)
    append_forward_oos_log_entry(versioned, log_path)

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["market_date"] == rows[1]["market_date"]
    assert rows[0]["calibration_version"] != rows[1]["calibration_version"]


def test_recovery_relapsed_stays_null_until_10_trading_day_window_complete():
    rows = [_forward_row(1, dominant_stage="RECOVERY")]
    rows.extend(_forward_row(day) for day in range(2, 11))

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is None


def test_recovery_relapsed_true_when_stress_returns_within_completed_window():
    rows = [_forward_row(1, dominant_stage="RECOVERY")]
    rows.extend(_forward_row(day) for day in range(2, 12))
    rows[4]["dominant_stage"] = "STRESS"

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is True


def test_recovery_relapsed_true_when_fast_cascade_boundary_triggers_within_window():
    rows = [_forward_row(1, dominant_stage="RECOVERY")]
    rows.extend(_forward_row(day) for day in range(2, 12))
    rows[6]["boundary_flag"] = True

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is True


def test_recovery_relapsed_true_after_two_consecutive_high_stress_secondary_days():
    rows = [_forward_row(1, dominant_stage="RECOVERY")]
    rows.extend(_forward_row(day) for day in range(2, 12))
    rows[3]["relapse_pressure"] = "HIGH"
    rows[3]["secondary_stage"] = "STRESS"
    rows[4]["relapse_pressure"] = "HIGH"
    rows[4]["secondary_stage"] = "STRESS"

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is True


def test_recovery_relapsed_false_when_no_or_trigger_occurs_by_window_end():
    rows = [_forward_row(1, dominant_stage="RECOVERY")]
    rows.extend(_forward_row(day) for day in range(2, 12))

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is False


def test_recovery_relapsed_only_materializes_for_recovery_anchors():
    rows = [_forward_row(1, dominant_stage="LATE_CYCLE")]
    rows.extend(_forward_row(day, dominant_stage="STRESS") for day in range(2, 12))

    materialized = materialize_recovery_relapsed_outcomes(rows)

    assert materialized[0]["recovery_relapsed"] is None
