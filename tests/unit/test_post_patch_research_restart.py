import json

from scripts.post_patch_research_restart import PostPatchResearchRestart


def test_post_patch_restart_writes_required_reports_and_artifacts(tmp_path):
    result = PostPatchResearchRestart(root=tmp_path).run_all()

    assert result["final_verdict"] in PostPatchResearchRestart.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "post_patch_priority_logic_reset.md",
        "post_patch_policy_improvable_reranking.md",
        "post_patch_slower_structural_internal_decomposition.md",
        "post_patch_recovery_relapse_priority_validation.md",
        "post_patch_hazard_repositioning_2022_stress_test.md",
        "post_patch_false_reentry_monitoring_framework.md",
        "post_patch_bounded_budget_allocation.md",
        "post_patch_research_line_admissibility_gate.md",
        "post_patch_final_budget_recommendation.md",
        "post_patch_acceptance_checklist.md",
        "post_patch_final_verdict.md",
    }
    required_artifacts = {
        "priority_logic_reset.json",
        "policy_improvable_reranking.json",
        "slower_structural_internal_decomposition.json",
        "recovery_relapse_priority_validation.json",
        "hazard_repositioning_2022_stress_test.json",
        "false_reentry_monitoring_framework.json",
        "bounded_budget_allocation.json",
        "research_line_admissibility_gate.json",
        "final_budget_recommendation.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "post_patch" / filename).exists()


def test_priority_logic_uses_improvable_share_not_residual_loss(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    reset = json.loads(
        (tmp_path / "artifacts/post_patch/priority_logic_reset.json").read_text()
    )
    reranking = json.loads(
        (tmp_path / "artifacts/post_patch/policy_improvable_reranking.json").read_text()
    )

    assert reset["decision"] == "PRIORITY_LOGIC_RESET_SUCCEEDED"
    assert reset["required_statement"] == (
        "residual_unrepaired_share may describe pain, but may not by itself justify primary budget priority."
    )
    assert reset["research_priority_score"]["primary_anchor"] == "policy_improvable_share"
    assert reset["research_priority_score"]["residual_unrepaired_share_role"] == "secondary_descriptive_only"
    assert reranking["ranking_rule"][0] == "positive_or_non_catastrophic_actual_executed_policy_contribution"
    assert reranking["primary_budget_anchor"] == "policy_improvable_share"
    for row in reranking["event_family_rows"]:
        assert "residual_unrepaired_share" in row
        if "2020-like" in row["event_family"] or "2015-style" in row["event_family"]:
            assert row["admissible_for_primary_bounded_research"] is False
            assert row["status"] in {"BOUNDARY_DISCLOSURE_ONLY", "EXECUTION_DOMINATED_DISCLOSURE_ONLY"}


def test_slower_structural_decomposition_forces_subtype_split_when_heterogeneous(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    decomposition = json.loads(
        (tmp_path / "artifacts/post_patch/slower_structural_internal_decomposition.json").read_text()
    )

    events = {row["event_name"]: row for row in decomposition["subtype_rows"]}
    assert {"2008 financial crisis stress", "2022 H1 structural stress"}.issubset(events)
    for row in events.values():
        assert set(row) >= {
            "policy_contribution",
            "policy_improvable_share",
            "residual_unrepaired_share",
            "exit_system_contribution",
            "hazard_contribution",
            "re_risk_release_diagnostics",
        }
    assert decomposition["heterogeneity_test"]["family_level_score_dominated_by_one_event"] is True
    assert decomposition["heterogeneity_test"]["unified_research_objective_would_be_misleading"] is True
    assert decomposition["claim_strength_label"] == "FAMILY_LEVEL_PRIORITY_REQUIRES_SUBTYPE_SPLIT"


def test_recovery_relapse_is_elevated_from_policy_improvable_share(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    recovery = json.loads(
        (tmp_path / "artifacts/post_patch/recovery_relapse_priority_validation.json").read_text()
    )

    assert recovery["decision"] in {
        "RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS",
        "RECOVERY_WITH_RELAPSE_DESERVES_ELEVATED_SECONDARY_STATUS",
    }
    assert recovery["recovery_with_relapse"]["policy_contribution"] > 0
    assert recovery["recovery_with_relapse"]["policy_improvable_share"] > 0
    assert recovery["explicit_elevation_justification"]
    compared = {row["event_family"] for row in recovery["direct_comparison"]}
    assert {"slower structural stress", "2018-style partially containable drawdown"}.issubset(compared)


def test_hazard_repositioning_requires_net_non_negative_2022_full_year(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    hazard = json.loads(
        (tmp_path / "artifacts/post_patch/hazard_repositioning_2022_stress_test.json").read_text()
    )

    assert hazard["decision"] in {
        "HAZARD_REPOSITIONING_IS_VALID_FOR_SLOW_STRESS_ASSIST",
        "HAZARD_REPOSITIONING_HAS_LOCAL_BENEFIT_BUT_NET_2022_COST",
        "HAZARD_REPOSITIONING_SHOULD_NOT_BE_REDEPLOYED_THIS_WAY",
    }
    assert {"baseline_repaired_exit_without_hazard", "hazard_assist_unchanged_release"}.issubset(
        {row["variant"] for row in hazard["variant_rows"]}
    )
    for row in hazard["variant_rows"]:
        assert set(row) >= {
            "h1_contribution_change",
            "h2_relapse_contribution_change",
            "net_2022_full_year_contribution",
            "premature_re_risk_episodes",
            "recovery_miss_change",
            "false_release_diagnostics",
        }
    if hazard["formal_repositioning_allowed"] is True:
        unchanged = next(
            row for row in hazard["variant_rows"] if row["variant"] == "hazard_assist_unchanged_release"
        )
        assert unchanged["net_2022_full_year_contribution"] >= 0


def test_false_reentry_monitoring_splits_count_from_damage(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    monitoring = json.loads(
        (tmp_path / "artifacts/post_patch/false_reentry_monitoring_framework.json").read_text()
    )

    assert monitoring["decision"] == "FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY"
    assert monitoring["interpretation_rule"] == (
        "low historical false_reentry_damage does NOT imply the issue is solved."
    )
    assert monitoring["false_reentry_count_metric"]["downstream_role"] == "MONITORING_ONLY"
    assert monitoring["false_reentry_damage_metric"]["accounting_basis"] == "ACTUAL_EXECUTED_ONLY"
    for row in monitoring["event_family_thresholds"]:
        assert row["nonzero_count_low_damage_governance_attention"] is True


def test_budget_admissibility_and_final_verdict_obey_gates(tmp_path):
    PostPatchResearchRestart(root=tmp_path).run_all()

    budget = json.loads(
        (tmp_path / "artifacts/post_patch/bounded_budget_allocation.json").read_text()
    )
    gate = json.loads(
        (tmp_path / "artifacts/post_patch/research_line_admissibility_gate.json").read_text()
    )
    recommendation = json.loads(
        (tmp_path / "artifacts/post_patch/final_budget_recommendation.json").read_text()
    )
    verdict = json.loads((tmp_path / "artifacts/post_patch/final_verdict.json").read_text())

    assert budget["decision"] in {
        "BOUNDED_BUDGET_ALLOCATION_IS_NOW_DECISION_READY",
        "BOUNDED_BUDGET_ALLOCATION_IS_DIRECTIONALLY_READY_BUT_NOT_FINAL",
    }
    admissibility = {row["research_line"]: row["admissibility"] for row in gate["line_rows"]}
    assert admissibility["2020-like bounded observation only"] == "BOUNDARY_DISCLOSURE_ONLY"
    assert admissibility["2015-style bounded observation only"] == "BOUNDARY_DISCLOSURE_ONLY"
    assert admissibility["false re-entry monitoring"] == "MONITORING_ONLY"
    assert "survivability repair" not in " ".join(
        line for line, status in admissibility.items() if status in {"PRIMARY_ADMISSIBLE", "CO_PRIMARY_ADMISSIBLE"}
    )
    assert recommendation["recommendation"] in PostPatchResearchRestart.ALLOWED_RECOMMENDATIONS
    assert verdict["final_verdict"] in PostPatchResearchRestart.ALLOWED_FINAL_VERDICTS
    assert verdict["deployment_readiness_restored"] is False
    assert verdict["candidate_maturity_restored"] is False
    assert verdict["freezeability_restored"] is False
    assert "post_patch_acceptance_checklist" in verdict
    assert all(not value for value in verdict["post_patch_acceptance_checklist"]["one_vote_fail_items"].values())
