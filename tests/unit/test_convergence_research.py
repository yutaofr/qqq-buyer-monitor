import json

from scripts.convergence_research import ConvergenceResearch


def test_convergence_pipeline_writes_required_reports_and_artifacts(tmp_path):
    research = ConvergenceResearch(root=tmp_path)

    result = research.run_all()

    assert result["final_verdict"] in ConvergenceResearch.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "convergence_cleanroom_continuity_audit.md",
        "convergence_structural_boundary_consolidation.md",
        "convergence_exit_system_structural_stress.md",
        "convergence_hybrid_system_rederivation.md",
        "convergence_hazard_system_2020_like.md",
        "convergence_integrated_interaction_validation.md",
        "convergence_state_contamination_audit.md",
        "convergence_loss_contribution_reconciliation.md",
        "convergence_policy_architecture_competition.md",
        "convergence_execution_boundary.md",
        "convergence_residual_protection_boundary.md",
        "convergence_decision_framework.md",
        "convergence_acceptance_checklist.md",
        "convergence_final_verdict.md",
    }
    required_artifacts = {
        "cleanroom_continuity_audit.json",
        "structural_boundary_consolidation.json",
        "exit_system_structural_stress.json",
        "hybrid_system_rederivation.json",
        "hazard_system_2020_like.json",
        "integrated_interaction_validation.json",
        "state_contamination_audit.json",
        "loss_contribution_reconciliation.json",
        "policy_architecture_competition.json",
        "execution_boundary.json",
        "residual_protection_boundary.json",
        "decision_framework.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "convergence" / filename).exists()


def test_cleanroom_audit_and_structural_boundary_are_decision_grade(tmp_path):
    ConvergenceResearch(root=tmp_path).run_all()

    audit = json.loads((tmp_path / "artifacts/convergence/cleanroom_continuity_audit.json").read_text())
    structural = json.loads(
        (tmp_path / "artifacts/convergence/structural_boundary_consolidation.json").read_text()
    )

    families = {row["metric_family"]: row["classification"] for row in audit["metric_families"]}
    assert families["baseline event-window metrics"] == "CLEANROOM_COMPUTATION_CONFIRMED"
    assert families["interaction validation metrics"] == "CLEANROOM_COMPUTATION_CONFIRMED"
    assert audit["legacy_artifacts_used_as_numeric_truth"] is False
    assert audit["final_budget_allocation_allowed_by_audit"] is True

    classes = {row["event_class"]: row for row in structural["event_classes"]}
    assert classes["2020-like fast-cascade / dominant overnight gap"]["dominant_category"] == (
        "STRUCTURALLY_NON_DEFENDABLE_CORE"
    )
    assert classes["slower structural stress"]["dominant_category"] in {
        "POLICY_IMPROVABLE_PRIMARY",
        "MODEL_AND_POLICY_MIXED",
    }
    for row in structural["event_classes"]:
        assert row["structural_non_defendability_share"] >= 0.0
        assert row["account_constraint_dependency"]["spot_only_no_derivatives"] is True


def test_exit_system_discloses_subtype_sample_budget_and_limits_claim_strength(tmp_path):
    ConvergenceResearch(root=tmp_path).run_all()

    exit_system = json.loads(
        (tmp_path / "artifacts/convergence/exit_system_structural_stress.json").read_text()
    )
    report = (tmp_path / "reports/convergence_exit_system_structural_stress.md").read_text()

    assert exit_system["decision"] in {
        "EXIT_SYSTEM_IS_PRIMARY_AND_GENERALIZABLE_WITHIN_STRUCTURAL_STRESS",
        "EXIT_SYSTEM_IS_VALUABLE_BUT_MAINLY_MULTI_WAVE_SPECIFIC",
        "EXIT_SYSTEM_IS_TOO_NARROW_TO_JUSTIFY_PRIMARY_STATUS",
    }
    assert exit_system["design"]["regime_detection_signal"]["role"] == "stress_presence_detection"
    assert exit_system["design"]["recovery_confirmation_signal"]["role"] == "stress_exit_confirmation"
    assert set(exit_system["variants_compared"]) >= {
        "posterior_decline_only",
        "current_repair_confirmer",
        "stricter_repair_confirmer",
        "faster_repair_confirmer",
    }
    subtypes = {row["subtype"]: row for row in exit_system["subtype_sample_budget"]}
    assert set(subtypes) >= {
        "multi-wave structural stress",
        "monotonic structural stress",
        "structural stress with recovery-relapse behavior",
    }
    for row in subtypes.values():
        assert row["independent_episodes"] >= 1
        assert row["total_rows"] > 0
        assert row["claim_strength_label"] in {
            "DESCRIPTIVE_ONLY",
            "DIRECTIONALLY_INFORMATIVE_BUT_NOT_DECISION_GRADE",
            "DECISION_GRADE_WITH_SUFFICIENT_SUPPORT",
        }
    assert exit_system["monotonic_stress_real_improvement"]["receives_real_improvement"] in {True, False}
    assert "strongly" not in report.lower()
    assert "significantly" not in report.lower()
    assert "robustly" not in report.lower()
    assert "reliably" not in report.lower()


def test_hazard_timing_uses_first_material_damage_date_not_only_largest_gap(tmp_path):
    ConvergenceResearch(root=tmp_path).run_all()

    hazard = json.loads((tmp_path / "artifacts/convergence/hazard_system_2020_like.json").read_text())

    assert hazard["first_material_damage_rule"]["rule"] == (
        "first close-to-prior-local-peak drawdown greater than 5 percent"
    )
    assert hazard["architecture"]["implemented_as_top_level_hard_gate"] is False
    assert hazard["structural_humility"]["solves_2020_like_survivability"] is False
    assert "FRA-OIS acceleration proxy" in hazard["candidate_signals"]
    assert "repo/funding stress proxy" in hazard["candidate_signals"]
    assert "treasury vol acceleration" in hazard["candidate_signals"]
    assert "stress VIX acceleration" in hazard["candidate_signals"]
    for row in hazard["tested_windows"]:
        assert row["first_material_damage_date"] is not None
        assert "warning_lead_vs_first_material_damage_date" in row
        assert "warning_lead_vs_largest_gap_date" in row
        assert "actual_effective_leverage_reduction" in row
        assert "pre_gap_cumulative_loss_reduction_account_terms" in row


def test_integrated_interaction_and_state_contamination_audit_cover_full_stack(tmp_path):
    ConvergenceResearch(root=tmp_path).run_all()

    interaction = json.loads(
        (tmp_path / "artifacts/convergence/integrated_interaction_validation.json").read_text()
    )
    contamination = json.loads(
        (tmp_path / "artifacts/convergence/state_contamination_audit.json").read_text()
    )

    assert set(interaction["stacks_compared"]) >= {
        "baseline stack",
        "exit repair only",
        "hazard only",
        "hybrid redesign only",
        "exit repair + hazard",
        "exit repair + hybrid",
        "hazard + hybrid",
        "full stack: exit repair + hazard + hybrid",
    }
    assert interaction["decision"] in {
        "FULL_STACK_INTERACTION_IS_STABLE_ENOUGH_TO_CONTINUE",
        "FULL_STACK_INTERACTION_HAS_ONE_OR_MORE_CRITICAL_COLLISIONS",
        "FULL_STACK_INTERACTION_INVALIDATES_CURRENT_ARCHITECTURE",
    }
    assert "2020-like fast cascade path" in interaction["critical_path_studies"]
    assert "2015-style liquidity vacuum path" in interaction["critical_path_studies"]
    assert contamination["audit_window_rule"]
    assert len(contamination["daily_rows"]) > 0
    required_keys = {
        "date",
        "event_name",
        "hazard_state",
        "cap_state",
        "repair_confirmation_state",
        "breadth_repair_condition_satisfied",
        "vol_decay_condition_satisfied",
        "price_repair_condition_satisfied",
        "persistence_condition_satisfied",
        "cap_release_condition_triggered",
        "release_later_judged_false",
        "causal_label",
        "theoretical_target_leverage",
        "actual_executed_leverage",
    }
    assert required_keys.issubset(contamination["daily_rows"][0])


def test_policy_decision_final_verdict_and_acceptance_constraints_are_synchronized(tmp_path):
    ConvergenceResearch(root=tmp_path).run_all()

    hybrid = json.loads((tmp_path / "artifacts/convergence/hybrid_system_rederivation.json").read_text())
    policy = json.loads(
        (tmp_path / "artifacts/convergence/policy_architecture_competition.json").read_text()
    )
    execution = json.loads((tmp_path / "artifacts/convergence/execution_boundary.json").read_text())
    residual = json.loads(
        (tmp_path / "artifacts/convergence/residual_protection_boundary.json").read_text()
    )
    decision = json.loads((tmp_path / "artifacts/convergence/decision_framework.json").read_text())
    verdict = json.loads((tmp_path / "artifacts/convergence/final_verdict.json").read_text())

    assert hybrid["decision"] in {
        "HYBRID_IS_SYSTEM_LEVEL_PRIMARY_POLICY_COMPONENT",
        "HYBRID_IS_SECONDARY_SUPPORTING_COMPONENT",
        "HYBRID_IS_NOT_WORTH_CONTINUED_PRIORITY",
    }
    if hybrid["best_policy"]["net_system_contribution_after_recovery_miss_and_interaction_effects"] < 0:
        assert hybrid["decision"] != "HYBRID_IS_SYSTEM_LEVEL_PRIMARY_POLICY_COMPONENT"
    assert policy["constraints"]["spot_only"] is True
    assert policy["decision"] in {
        "POLICY_ARCHITECTURE_HAS_A_CLEAR_PRIMARY_CANDIDATE",
        "POLICY_ARCHITECTURE_HAS_TWO_BOUNDED_CONTENDERS",
        "POLICY_ARCHITECTURE_IS_NOT_CONVERGED_ENOUGH",
    }
    assert execution["decision"] in {
        "CURRENT_EXECUTION_ASSUMPTIONS_ARE_SUFFICIENT_FOR_POLICY_RESEARCH",
        "EXECUTION_RESEARCH_GATE_IS_REQUIRED_NEXT",
        "CURRENT_RESULTS_ARE_TOO_EXECUTION_SENSITIVE",
    }
    assert residual["decision"] == "RESIDUAL_PROTECTION_REMAINS_BOUNDARY_ONLY"
    assert decision["freezeability_status"] == "NOT_FREEZEABLE"
    assert verdict["convergence_dependency_reference"] == decision["convergence_status"]
    assert verdict["final_verdict"] in ConvergenceResearch.ALLOWED_FINAL_VERDICTS
    checklist = verdict["convergence_acceptance_checklist"]
    assert all(value is False for value in checklist["one_vote_fail_items"].values())
    assert all(value is True for value in checklist["mandatory_pass_items"].values())
    assert verdict["structural_humility"]["production_freeze_ready"] is False
    assert verdict["structural_humility"]["2020_like_survivability_solved"] is False
