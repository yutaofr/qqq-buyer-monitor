from __future__ import annotations

import json
from datetime import date

from scripts.final_product_patch import FinalProductPatch, build_runtime_dashboard_payload
from src.models import SignalResult, TargetAllocationState


def _signal_result(
    *,
    probabilities: dict[str, float],
    stable_regime: str,
    metadata: dict | None = None,
) -> SignalResult:
    return SignalResult(
        date=date(2026, 4, 19),
        price=545.0,
        target_beta=0.74,
        probabilities=probabilities,
        priors={stage: 0.25 for stage in ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]},
        entropy=0.62,
        stable_regime=stable_regime,
        target_allocation=TargetAllocationState(0.26, 0.74, 0.0, 0.74),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="final product patch test fixture",
        metadata=metadata or {},
    )


def test_runtime_payload_exposes_relapse_pressure_and_recovery_caution():
    result = _signal_result(
        probabilities={"MID_CYCLE": 0.10, "LATE_CYCLE": 0.14, "BUST": 0.18, "RECOVERY": 0.58},
        stable_regime="RECOVERY",
        metadata={
            "feature_values": {
                "hazard_score": 0.58,
                "stress_score": 0.49,
                "breadth_proxy": 0.44,
                "volatility_percentile": 0.72,
                "hazard_delta_5d": 0.08,
                "breadth_delta_10d": -0.07,
                "volatility_delta_10d": 0.12,
                "stress_delta_5d": 0.09,
                "stress_acceleration_5d": 0.07,
                "repair_confirmation": True,
                "relapse_flag": True,
            },
            "probability_dynamics": {
                "RECOVERY": {"delta_1d": 0.04, "acceleration_1d": 0.01},
                "BUST": {"delta_1d": 0.05, "acceleration_1d": 0.02},
            },
        },
    )

    payload = build_runtime_dashboard_payload(result)

    assert payload["summary"]["current_stage"] == "RECOVERY"
    assert payload["relapse_pressure"]["level"] in {"ELEVATED", "HIGH"}
    assert payload["relapse_pressure"]["visible"] is True
    assert payload["recovery_caution"]["is_active"] is True
    assert "Recovery signal is present" in payload["recovery_caution"]["banner_text"]
    assert payload["export_fields"]["relapse_pressure"] == payload["relapse_pressure"]["level"]


def test_runtime_payload_reframes_diffuse_late_cycle_as_transition_zone():
    result = _signal_result(
        probabilities={"MID_CYCLE": 0.31, "LATE_CYCLE": 0.34, "BUST": 0.23, "RECOVERY": 0.12},
        stable_regime="LATE_CYCLE",
        metadata={
            "feature_values": {
                "hazard_score": 0.43,
                "stress_score": 0.39,
                "breadth_proxy": 0.42,
                "volatility_percentile": 0.68,
                "hazard_delta_5d": 0.06,
                "breadth_delta_10d": -0.05,
                "volatility_delta_10d": 0.08,
                "stress_delta_5d": 0.07,
                "stress_acceleration_5d": 0.04,
            },
            "probability_dynamics": {
                "LATE_CYCLE": {"delta_1d": 0.01, "acceleration_1d": 0.00},
                "BUST": {"delta_1d": 0.04, "acceleration_1d": 0.02},
                "MID_CYCLE": {"delta_1d": -0.03, "acceleration_1d": -0.01},
            },
        },
    )

    payload = build_runtime_dashboard_payload(result)

    assert payload["summary"]["current_stage"] == "LATE_CYCLE"
    assert payload["late_cycle_transition"]["is_transition_zone"] is True
    assert payload["late_cycle_transition"]["display_label"] == "Transition Zone"
    assert payload["late_cycle_transition"]["direction"] in {
        "DRIFTING_TOWARD_STRESS",
        "UNRESOLVED_MIXED",
    }
    assert "mixed evidence" in payload["late_cycle_transition"]["badge_text"].lower()
    assert payload["export_fields"]["late_cycle_transition_label"] == "Transition Zone"


def test_final_product_patch_writes_required_launch_files(tmp_path):
    verdict = FinalProductPatch(root=tmp_path).run_all()

    assert verdict["final_verdict"] in {
        "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD",
        "LAUNCH_AS_LIMITED_DASHBOARD_WITH_EXPLICIT_CAUTION",
        "DO_NOT_LAUNCH_PRODUCT_YET",
    }

    required_reports = {
        "final_product_recovery_relapse_pressure.md",
        "final_product_late_cycle_ui_redesign.md",
        "final_product_forward_oos_monitoring.md",
        "final_product_launch_note.md",
        "final_product_user_guide.md",
        "final_product_risk_disclosure.md",
        "final_product_real_ui_patch.md",
        "final_product_consistency_reaudit.md",
        "final_product_final_verdict.md",
    }
    required_artifacts = {
        "recovery_relapse_pressure.json",
        "late_cycle_ui_redesign.json",
        "forward_oos_monitoring.json",
        "launch_package.json",
        "real_ui_patch.json",
        "consistency_reaudit.json",
        "final_verdict.json",
        "forward_oos_monitoring_log.jsonl",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "final_product" / filename).exists()

    final_verdict = json.loads(
        (tmp_path / "artifacts" / "final_product" / "final_verdict.json").read_text(
            encoding="utf-8"
        )
    )
    forward_schema = json.loads(
        (tmp_path / "artifacts" / "final_product" / "forward_oos_monitoring.json").read_text(
            encoding="utf-8"
        )
    )
    assert final_verdict["final_verdict"] == verdict["final_verdict"]
    assert final_verdict["oos_monitoring_log_in_place"] is True
    assert final_verdict["relapse_pressure_clearly_exposed"] is True
    assert final_verdict["late_cycle_honesty_patch_complete"] is True
    assert forward_schema["outcome_contract"]["recovery_relapsed"]["definition_status"] == "FROZEN"
    assert forward_schema["outcome_contract"]["recovery_relapsed"]["window_trading_days"] == 10
    assert set(forward_schema["outcome_contract"]["recovery_relapsed"]["or_triggers"]) == {
        "dominant_stage returns to STRESS",
        "FAST_CASCADE_BOUNDARY is triggered",
        "relapse_pressure == HIGH and secondary_stage == STRESS for at least 2 consecutive trading days",
    }
