import json

from scripts.phase_next_research import PhaseNextResearch


def test_phase_next_pipeline_writes_required_artifacts_and_reports(tmp_path):
    research = PhaseNextResearch(root=tmp_path)

    result = research.run_all()

    assert result["final_verdict"] in {
        "CONTINUE_WITH_PRIMARY_FOCUS_ON_SLOWER_STRUCTURAL_STRESS_AND_HYBRID_RELEASE_REDESIGN",
        "CONTINUE_WITH_PRIMARY_FOCUS_ON_EXOGENOUS_HAZARD_RESEARCH",
        "CONTINUE_WITH_COMBINED_POLICY_REPAIR_AND_PRE_GAP_HAZARD_RESEARCH",
        "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_ADDITIONAL_COMPLEXITY",
    }

    required_reports = {
        "phase_next_cleanroom_baseline_rebuild.md",
        "phase_next_slower_structural_stress_exit_repair.md",
        "phase_next_hybrid_cap_release_redesign.md",
        "phase_next_exogenous_hazard_module.md",
        "phase_next_event_slice_validation.md",
        "phase_next_gearbox_boundary.md",
        "phase_next_residual_protection_boundary.md",
        "phase_next_acceptance_checklist.md",
        "phase_next_final_verdict.md",
    }
    required_artifacts = {
        "cleanroom_baseline_rebuild.json",
        "slower_structural_stress_exit_repair.json",
        "hybrid_cap_release_redesign.json",
        "exogenous_hazard_module.json",
        "event_slice_validation.json",
        "gearbox_boundary.json",
        "residual_protection_boundary.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "phase_next" / filename).exists()


def test_cleanroom_baseline_rebuild_uses_traceable_inputs_and_slice_metrics(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    baseline = json.loads(
        (tmp_path / "artifacts/phase_next/cleanroom_baseline_rebuild.json").read_text()
    )

    assert baseline["source_policy"]["legacy_artifacts_used_as_numeric_truth"] is False
    assert baseline["source_policy"]["primary_price_source"] == "data/qqq_history_cache.csv"
    assert "data/macro_historical_dump.csv" in baseline["source_policy"]["macro_liquidity_sources"]
    assert len(baseline["event_windows"]) >= 6
    for row in baseline["event_window_metrics"]:
        assert row["event_slice"] in research.REQUIRED_SLICE_ORDER
        assert "gap_adjusted_loss_contribution" in row
        assert "policy_trigger_timing" in row
        assert "cap_on_duration_days" in row
        assert row["provenance"] == "clean_room_recomputed_from_traceable_inputs"


def test_exit_repair_separates_detection_from_recovery_confirmation(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    repair = json.loads(
        (tmp_path / "artifacts/phase_next/slower_structural_stress_exit_repair.json").read_text()
    )

    assert repair["design"]["regime_detection_signal"]["role"] == "stress_presence_detection"
    assert repair["design"]["recovery_confirmation_signal"]["role"] == "stress_exit_confirmation"
    assert set(repair["design"]["recovery_confirmation_signal"]["components"]) == {
        "breadth_recovery_amplitude",
        "realized_volatility_decay",
        "price_repair_fraction",
        "persistence_days",
    }
    assert repair["experiment"]["old_exit_logic"]["description"] == "posterior_decline_only"
    assert repair["experiment"]["new_exit_logic"]["description"] == "composite_repair_confirmation"
    assert repair["decision"] in {
        "REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING",
        "REPAIR_CONFIRMATION_SIGNAL_IMPROVES_SOME_METRICS_BUT_NOT_ENOUGH",
        "REPAIR_CONFIRMATION_SIGNAL_DOES_NOT_JUSTIFY_REPLACEMENT",
    }
    assert (
        repair["summary_metrics"]["new"]["false_upshift_frequency"]
        <= repair["summary_metrics"]["old"]["false_upshift_frequency"]
    )


def test_hybrid_release_reports_recovery_miss_and_net_policy_value(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    hybrid = json.loads(
        (tmp_path / "artifacts/phase_next/hybrid_cap_release_redesign.json").read_text()
    )

    assert hybrid["design"]["enter_cap_logic"] != hybrid["design"]["release_cap_logic"]
    assert set(hybrid["policies_compared"]) >= {
        "symmetric_cap_release",
        "faster_recovery_sensitive_cap_release",
        "staged_cap_release",
    }
    for policy in hybrid["policy_metrics"]:
        assert "gap_day_loss_reduction" in policy
        assert "post_gap_recovery_miss_cost" in policy
        assert "net_contribution_after_recovery_miss" in policy
        assert policy["judged_by_aggregate_gain_only"] is False
    assert hybrid["decision"] in {
        "HYBRID_RELEASE_REDESIGN_RECOVERS_NET_POLICY_VALUE",
        "HYBRID_RELEASE_REDESIGN_HELPS_BUT_REMAINS_SECONDARY",
        "HYBRID_RELEASE_REDESIGN_DOES_NOT_FIX_THE_CORE_PROBLEM",
    }


def test_hazard_module_is_modular_and_bounded_not_survivability_claim(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    hazard = json.loads(
        (tmp_path / "artifacts/phase_next/exogenous_hazard_module.json").read_text()
    )

    assert hazard["architecture"]["module_type"] == "bounded_exogenous_hazard_function"
    assert hazard["architecture"]["implemented_as_top_level_orchestrator_gate"] is False
    assert "FRA_OIS_acceleration_proxy" in hazard["candidate_signals"]
    assert "repo_or_funding_stress_proxy" in hazard["candidate_signals"]
    assert hazard["structural_humility"]["solves_2020_like_survivability"] is False
    assert hazard["decision"] in {
        "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
        "EXOGENOUS_HAZARD_MODULE_HAS_LIMITED_OR_UNSTABLE_VALUE",
        "EXOGENOUS_HAZARD_MODULE_DOES_NOT_JUSTIFY_ADDITION",
    }
    assert "days_of_earlier_warning" in hazard["summary_metrics"]
    assert "false_hazard_activation_frequency" in hazard["summary_metrics"]


def test_event_slice_validation_is_slice_first_and_not_aggregate_only(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    validation = json.loads(
        (tmp_path / "artifacts/phase_next/event_slice_validation.json").read_text()
    )

    assert validation["reporting_order"][:6] == research.REQUIRED_SLICE_ORDER
    assert validation["aggregate_reported_last"] is True
    assert validation["pooled_score_optimization_used"] is False
    assert [row["event_slice"] for row in validation["slice_results"][:6]] == research.REQUIRED_SLICE_ORDER
    for row in validation["slice_results"]:
        assert "drawdown_contribution" in row
        assert "false_exit_or_false_reentry" in row
        assert "recovery_miss" in row
        assert "pre_gap_exposure_reduction" in row
        assert "non_gap_drag" in row
        assert "policy_turnover" in row


def test_boundaries_and_final_acceptance_enforce_program_constraints(tmp_path):
    research = PhaseNextResearch(root=tmp_path)
    research.run_all()

    gearbox = json.loads((tmp_path / "artifacts/phase_next/gearbox_boundary.json").read_text())
    residual = json.loads(
        (tmp_path / "artifacts/phase_next/residual_protection_boundary.json").read_text()
    )
    verdict = json.loads((tmp_path / "artifacts/phase_next/final_verdict.json").read_text())

    assert gearbox["budget_status"] != "PRIMARY"
    assert residual["budget_status"] != "PRIMARY"
    assert residual["spot_only_no_derivatives_assumption"] is True
    assert verdict["final_verdict"] in {
        "CONTINUE_WITH_PRIMARY_FOCUS_ON_SLOWER_STRUCTURAL_STRESS_AND_HYBRID_RELEASE_REDESIGN",
        "CONTINUE_WITH_PRIMARY_FOCUS_ON_EXOGENOUS_HAZARD_RESEARCH",
        "CONTINUE_WITH_COMBINED_POLICY_REPAIR_AND_PRE_GAP_HAZARD_RESEARCH",
        "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_ADDITIONAL_COMPLEXITY",
    }
    checklist = verdict["phase_next_acceptance_checklist"]
    assert all(value is False for value in checklist["one_vote_fail_items"].values())
    assert all(value is True for value in checklist["mandatory_pass_items"].values())
    assert verdict["structural_humility"]["candidate_safety_restored"] is False
    assert verdict["structural_humility"]["execution_safety_restored"] is False
    assert verdict["structural_humility"]["2020_like_survivability_solved"] is False
