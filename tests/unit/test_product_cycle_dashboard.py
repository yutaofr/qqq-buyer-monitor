import json
import math

from scripts.product_cycle_dashboard import (
    ACTION_BANDS,
    STAGES,
    TRANSITION_URGENCIES,
    ProductCycleDashboard,
    ProductDashboardInput,
)


def test_daily_output_is_probability_first_and_not_leverage_advice():
    dashboard = ProductCycleDashboard()

    result = dashboard.evaluate(
        ProductDashboardInput(
            date="2026-04-16",
            hazard_score=0.36,
            hazard_percentile=0.72,
            stress_score=0.34,
            breadth_proxy=0.43,
            volatility_percentile=0.61,
            structural_stress=False,
            repair_confirmation=False,
            relapse_flag=False,
            hazard_delta_5d=0.07,
            breadth_delta_10d=-0.06,
            volatility_delta_10d=0.09,
            boundary_pressure=0.01,
            stress_persistence_days=0,
            repair_persistence_days=0,
        )
    )

    assert set(result["stage_probabilities"]) == set(STAGES)
    assert math.isclose(sum(result["stage_probabilities"].values()), 1.0, abs_tol=1e-9)
    assert result["dominant_stage"] == max(
        result["stage_probabilities"], key=result["stage_probabilities"].get
    )
    assert result["secondary_stage"] != result["dominant_stage"]
    assert result["transition_urgency"] in TRANSITION_URGENCIES
    assert result["action_relevance_band"] in ACTION_BANDS
    assert "stage_stability" in result
    assert "evidence_panel" in result
    assert "target_leverage" not in json.dumps(result).lower()
    assert "recommended_leverage" not in json.dumps(result).lower()
    assert "order" not in json.dumps(result["action_relevance_band"]).lower()


def test_transition_urgency_and_action_band_are_separate_from_stage_label():
    dashboard = ProductCycleDashboard()
    base = dict(
        date="2026-04-16",
        hazard_score=0.31,
        hazard_percentile=0.63,
        stress_score=0.30,
        breadth_proxy=0.48,
        volatility_percentile=0.58,
        structural_stress=False,
        repair_confirmation=False,
        relapse_flag=False,
        boundary_pressure=0.0,
        stress_persistence_days=0,
        repair_persistence_days=0,
    )

    calm = dashboard.evaluate(
        ProductDashboardInput(
            **base,
            hazard_delta_5d=0.0,
            breadth_delta_10d=0.0,
            volatility_delta_10d=0.0,
        )
    )
    migrating = dashboard.evaluate(
        ProductDashboardInput(
            **base,
            hazard_delta_5d=0.11,
            breadth_delta_10d=-0.11,
            volatility_delta_10d=0.18,
        )
    )

    assert calm["dominant_stage"] == migrating["dominant_stage"]
    assert calm["transition_urgency"] == "LOW"
    assert migrating["transition_urgency"] in {"HIGH", "UNSTABLE"}
    assert calm["action_relevance_band"] == "NO_ACTION_ZONE"
    assert migrating["action_relevance_band"] in {
        "PREPARE_TO_ADJUST",
        "HIGH_CONVICTION_TRANSITION",
    }


def test_fast_cascade_boundary_is_warning_not_solved_decision():
    dashboard = ProductCycleDashboard()

    result = dashboard.evaluate(
        ProductDashboardInput(
            date="2020-03-16",
            hazard_score=0.71,
            hazard_percentile=0.98,
            stress_score=0.74,
            breadth_proxy=0.18,
            volatility_percentile=0.99,
            structural_stress=True,
            repair_confirmation=False,
            relapse_flag=True,
            hazard_delta_5d=0.18,
            breadth_delta_10d=-0.16,
            volatility_delta_10d=0.25,
            boundary_pressure=0.11,
            stress_persistence_days=9,
            repair_persistence_days=0,
        )
    )

    assert result["dominant_stage"] == "FAST_CASCADE_BOUNDARY"
    assert result["boundary_warning"]["is_active"] is True
    assert "not a solved decision regime" in result["boundary_warning"]["warning_text"]
    assert "Do not infer" in result["boundary_warning"]["not_to_infer"]
    assert "target_leverage" not in json.dumps(result["boundary_warning"]).lower()


def test_product_pipeline_writes_required_reports_and_artifacts(tmp_path):
    result = ProductCycleDashboard(root=tmp_path).run_all()

    assert result["final_verdict"] in {
        "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD",
        "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS",
        "DO_NOT_LAUNCH_PRODUCT_YET",
    }

    required_reports = {
        "product_objective_lock.md",
        "product_engine_audit.md",
        "product_stage_probability_engine_alignment.md",
        "product_feature_engineering_alignment.md",
        "product_probability_calibration_quality.md",
        "product_stage_process_stability_audit.md",
        "product_transition_urgency_action_layer.md",
        "product_boundary_layer.md",
        "product_dashboard_ui_alignment.md",
        "product_documentation_alignment.md",
        "product_historical_probability_validation.md",
        "product_self_iteration_gate.md",
        "product_acceptance_checklist.md",
        "product_final_verdict.md",
    }
    required_artifacts = {
        "objective_lock.json",
        "engine_audit.json",
        "stage_probability_engine_alignment.json",
        "feature_engineering_alignment.json",
        "probability_calibration_quality.json",
        "stage_process_stability_audit.json",
        "transition_urgency_action_layer.json",
        "boundary_layer.json",
        "dashboard_ui_alignment.json",
        "documentation_alignment.json",
        "historical_probability_validation.json",
        "self_iteration_gate.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "product" / filename).exists()

    final = json.loads((tmp_path / "artifacts/product/final_verdict.json").read_text())
    assert final["automatic_leverage_targeting_restored"] is False
    assert final["turning_point_prediction_solved"] is False
    assert "product_acceptance_checklist" in final
    assert all(
        item["resolved"] is True
        for item in final["product_acceptance_checklist"]["one_vote_fail_items"]
    )
    assert all(
        item["passed"] is True
        for item in final["product_acceptance_checklist"]["mandatory_pass_items"]
    )


def test_probability_quality_and_stage_stability_meet_declared_thresholds(tmp_path):
    ProductCycleDashboard(root=tmp_path).run_all()

    quality = json.loads(
        (tmp_path / "artifacts/product/probability_calibration_quality.json").read_text()
    )
    stability = json.loads(
        (tmp_path / "artifacts/product/stage_process_stability_audit.json").read_text()
    )

    assert quality["decision"] in {
        "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD",
        "PROBABILITY_QUALITY_IS_IMPROVABLE_BUT_USABLE",
    }
    assert quality["metrics"]["multiclass_brier_score"] <= quality["thresholds"][
        "acceptable_multiclass_brier"
    ]
    assert quality["metrics"]["multiclass_ece"] <= quality["thresholds"][
        "acceptable_multiclass_ece"
    ]
    assert stability["decision"] in {
        "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE",
        "STAGE_PROCESS_IS_USABLE_WITH_NOISE_CAVEATS",
    }
    assert stability["metrics"]["stage_flapping_rate"] <= stability["thresholds"][
        "max_stage_flapping_rate"
    ]
    assert stability["metrics"]["alert_fatigue_proxy_rate"] <= stability["thresholds"][
        "max_alert_fatigue_proxy_rate"
    ]


def test_historical_validation_uses_required_probability_windows_not_policy_pnl(tmp_path):
    ProductCycleDashboard(root=tmp_path).run_all()

    validation = json.loads(
        (tmp_path / "artifacts/product/historical_probability_validation.json").read_text()
    )
    windows = {row["event_name"] for row in validation["event_validations"]}

    assert {
        "Benign expansion period",
        "2008 crisis",
        "Q4 2018 drawdown",
        "COVID fast cascade",
        "2022 H1 structural stress",
        "2022 relapse / recovery",
        "August 2015 liquidity vacuum",
    }.issubset(windows)
    for row in validation["event_validations"]:
        assert "stage_path_table" in row
        assert "probability_path_table" in row
        assert "urgency_path_table" in row
        assert row["policy_pnl_primary_validation"] is False
        assert row["primary_validation_language"] == "stage_probability_process_quality"


def test_documentation_and_final_verdict_cut_legacy_auto_engine_narrative(tmp_path):
    ProductCycleDashboard(root=tmp_path).run_all()

    docs = json.loads((tmp_path / "artifacts/product/documentation_alignment.json").read_text())
    final = json.loads((tmp_path / "artifacts/product/final_verdict.json").read_text())

    assert docs["decision"] in {
        "DOCUMENTATION_IS_FULLY_ALIGNED",
        "DOCUMENTATION_IS_MOSTLY_ALIGNED_BUT_INCOMPLETE",
    }
    assert docs["required_documentation_rules"]["not_auto_beta_engine"] is True
    assert docs["required_documentation_rules"]["not_turning_point_predictor"] is True
    assert final["final_verdict"] in {
        "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD",
        "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS",
        "DO_NOT_LAUNCH_PRODUCT_YET",
    }
    assert "exact turning-point prediction" in " ".join(final["user_should_not_expect"])
