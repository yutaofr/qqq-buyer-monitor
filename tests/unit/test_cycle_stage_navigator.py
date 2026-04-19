import json

from scripts.cycle_stage_navigator import CycleStageInput, CycleStageNavigator


def test_stage_translation_outputs_human_stage_not_target_leverage():
    navigator = CycleStageNavigator()

    result = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.34,
            stress_score=0.31,
            breadth_proxy=0.43,
            volatility_percentile=0.61,
            repair_active=False,
            structural_stress=False,
            repair_confirmation=False,
            relapse_flag=False,
            hazard_delta=0.08,
            breadth_delta=-0.06,
            volatility_delta=0.10,
        )
    )

    assert result["current_stage_label"] == "LATE_CYCLE"
    assert result["transition_urgency"] == "RISING"
    assert "stage_confidence" in result
    assert "evidence_panel" in result
    assert "target_leverage" not in result
    assert "recommended_leverage" not in json.dumps(result).lower()
    assert result["human_guidance_layer"]["hard_leverage_number"] is None


def test_stage_taxonomy_distinguishes_stress_recovery_and_boundary():
    navigator = CycleStageNavigator()

    stress = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.48,
            stress_score=0.63,
            breadth_proxy=0.28,
            volatility_percentile=0.88,
            repair_active=True,
            structural_stress=True,
            repair_confirmation=False,
            relapse_flag=False,
            hazard_delta=0.03,
            breadth_delta=-0.02,
            volatility_delta=0.04,
            stress_persistence_days=14,
        )
    )
    recovery = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.22,
            stress_score=0.36,
            breadth_proxy=0.51,
            volatility_percentile=0.52,
            repair_active=False,
            structural_stress=False,
            repair_confirmation=True,
            relapse_flag=False,
            hazard_delta=-0.04,
            breadth_delta=0.07,
            volatility_delta=-0.18,
            repair_persistence_days=5,
        )
    )
    boundary = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.66,
            stress_score=0.58,
            breadth_proxy=0.24,
            volatility_percentile=0.99,
            repair_active=True,
            structural_stress=True,
            repair_confirmation=False,
            relapse_flag=True,
            gap_pressure=0.09,
            hazard_delta=0.18,
            breadth_delta=-0.12,
            volatility_delta=0.22,
        )
    )

    assert stress["current_stage_label"] == "STRESS"
    assert recovery["current_stage_label"] == "RECOVERY"
    assert boundary["current_stage_label"] == "FAST_CASCADE_BOUNDARY"
    assert boundary["boundary_warning"]["is_boundary_warning"] is True
    assert boundary["boundary_warning"]["not_to_infer"] == "Do not infer a solved execution or leverage regime."


def test_transition_urgency_is_separate_from_stage_confidence():
    navigator = CycleStageNavigator()

    stable = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.30,
            stress_score=0.30,
            breadth_proxy=0.47,
            volatility_percentile=0.50,
            repair_active=False,
            structural_stress=False,
            repair_confirmation=False,
            relapse_flag=False,
            hazard_delta=0.00,
            breadth_delta=0.00,
            volatility_delta=0.00,
        )
    )
    unstable = navigator.evaluate(
        CycleStageInput(
            hazard_score=0.30,
            stress_score=0.30,
            breadth_proxy=0.47,
            volatility_percentile=0.50,
            repair_active=False,
            structural_stress=False,
            repair_confirmation=False,
            relapse_flag=True,
            hazard_delta=0.15,
            breadth_delta=-0.12,
            volatility_delta=0.20,
        )
    )

    assert stable["current_stage_label"] == unstable["current_stage_label"]
    assert stable["transition_urgency"] == "LOW"
    assert unstable["transition_urgency"] == "UNSTABLE"
    assert stable["stage_confidence"] == unstable["stage_confidence"]


def test_cycle_stage_pipeline_writes_required_reports_and_artifacts(tmp_path):
    result = CycleStageNavigator(root=tmp_path).run_all()

    assert result["final_verdict"] in {
        "RELAUNCH_AS_HUMAN_CYCLE_STAGE_NAVIGATOR",
        "RELAUNCH_AS_LIMITED_CYCLE_STAGE_MONITOR",
        "DO_NOT_RELAUNCH_EVEN_AS_NAVIGATOR",
    }

    required_reports = {
        "cycle_stage_mission_reposition_lock.md",
        "cycle_stage_taxonomy_finalization.md",
        "cycle_stage_signal_mapping.md",
        "cycle_stage_stack_to_stage_translation.md",
        "cycle_stage_transition_urgency_model.md",
        "cycle_stage_stability_false_alarm_audit.md",
        "cycle_stage_boundary_state_handling.md",
        "cycle_stage_dashboard_spec.md",
        "cycle_stage_historical_validation.md",
        "cycle_stage_human_decision_support_evaluation.md",
        "cycle_stage_acceptance_checklist.md",
        "cycle_stage_final_verdict.md",
    }
    required_artifacts = {
        "mission_reposition_lock.json",
        "taxonomy_finalization.json",
        "signal_mapping.json",
        "stack_to_stage_translation.json",
        "transition_urgency_model.json",
        "stability_false_alarm_audit.json",
        "boundary_state_handling.json",
        "dashboard_spec.json",
        "historical_validation.json",
        "human_decision_support_evaluation.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "cycle_stage" / filename).exists()

    verdict = json.loads((tmp_path / "artifacts/cycle_stage/final_verdict.json").read_text())
    assert "cycle_stage_acceptance_checklist" in verdict
    assert all(value is False for value in verdict["cycle_stage_acceptance_checklist"]["one_vote_fail_items"].values())
    assert all(value is True for value in verdict["cycle_stage_acceptance_checklist"]["mandatory_pass_items"].values())
    assert verdict["automatic_execution_restored"] is False


def test_historical_validation_is_stage_first_not_policy_pnl(tmp_path):
    CycleStageNavigator(root=tmp_path).run_all()

    validation = json.loads((tmp_path / "artifacts/cycle_stage/historical_validation.json").read_text())
    events = {row["event_name"] for row in validation["event_validations"]}

    assert {
        "Benign expansion / normal period",
        "2008 financial crisis stress",
        "Q4 2018 drawdown",
        "COVID fast cascade",
        "2022 H1 structural stress",
        "2022 bear rally relapse",
        "August 2015 liquidity vacuum",
    }.issubset(events)
    for row in validation["event_validations"]:
        assert "stage_path_table" in row
        assert "confidence_path_table" in row
        assert "urgency_path_table" in row
        assert "policy_pnl_primary_validation" not in row
        assert row["primary_validation_language"] == "stage_usefulness_not_policy_pnl"


def test_dashboard_spec_is_fast_to_read_and_exposes_uncertainty(tmp_path):
    CycleStageNavigator(root=tmp_path).run_all()

    dashboard = json.loads((tmp_path / "artifacts/cycle_stage/dashboard_spec.json").read_text())

    assert dashboard["decision"] == "DASHBOARD_SPEC_IS_READY_FOR_IMPLEMENTATION"
    assert dashboard["human_interpretability_test"]["target_read_time_seconds"] <= 60
    assert "what_the_system_does_not_know" in dashboard
    assert "hard leverage number" in dashboard["forbidden_dashboard_outputs"]
