import json

from scripts.frontier_validation import FrontierValidation


def test_frontier_validation_writes_required_reports_and_artifacts(tmp_path):
    result = FrontierValidation(root=tmp_path).run_all()

    assert result["final_verdict"] in FrontierValidation.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "frontier_budget_anchor_suspension_gate.md",
        "frontier_policy_improvable_transferability.md",
        "frontier_blindish_event_family_cross_validation.md",
        "frontier_slower_structural_subtype_transfer_audit.md",
        "frontier_recovery_relapse_transfer_audit.md",
        "frontier_hazard_repositioning_transfer_audit.md",
        "frontier_improvement_driver_attribution.md",
        "frontier_hard_vs_soft_constraint_separation.md",
        "frontier_soft_constraint_frontier_estimation.md",
        "frontier_budget_anchor_reinstatement.md",
        "frontier_final_budget_recommendation.md",
        "frontier_acceptance_checklist.md",
        "frontier_final_verdict.md",
    }
    required_artifacts = {
        "budget_anchor_suspension_gate.json",
        "policy_improvable_transferability.json",
        "blindish_event_family_cross_validation.json",
        "slower_structural_subtype_transfer_audit.json",
        "recovery_relapse_transfer_audit.json",
        "hazard_repositioning_transfer_audit.json",
        "improvement_driver_attribution.json",
        "hard_vs_soft_constraint_separation.json",
        "soft_constraint_frontier_estimation.json",
        "budget_anchor_reinstatement.json",
        "final_budget_recommendation.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts/frontier" / filename).exists()


def test_budget_anchor_is_suspended_until_transferability_succeeds(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    gate = json.loads(
        (tmp_path / "artifacts/frontier/budget_anchor_suspension_gate.json").read_text()
    )
    transfer = json.loads(
        (tmp_path / "artifacts/frontier/policy_improvable_transferability.json").read_text()
    )
    reinstatement = json.loads(
        (tmp_path / "artifacts/frontier/budget_anchor_reinstatement.json").read_text()
    )

    assert gate["decision"] in FrontierValidation.ALLOWED_BUDGET_SUSPENSION_DECISIONS
    assert gate["decision"] == "BUDGET_ANCHOR_SUSPENDED_PENDING_TRANSFERABILITY_VALIDATION"
    assert gate["historical_ranking_status"] == "DESCRIPTIVE_ONLY"
    assert gate["future_budget_anchor_status"] == "SUSPENDED_PENDING_TRANSFERABILITY_VALIDATION"
    assert transfer["decision"] in FrontierValidation.ALLOWED_TRANSFER_DECISIONS
    if transfer["decision"] != "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE":
        assert reinstatement["decision"] != (
            "POLICY_IMPROVABLE_SHARE_MAY_BE_REINSTATED_AS_TRANSFER_ADJUSTED_BUDGET_ANCHOR"
        )


def test_transferability_artifact_contains_holdout_rank_and_sign_stability(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    transfer = json.loads(
        (tmp_path / "artifacts/frontier/policy_improvable_transferability.json").read_text()
    )

    assert {"leave_one_event_family_out", "leave_one_major_window_out", "subtype_holdouts"}.issubset(
        transfer["validation_designs"]
    )
    assert len(transfer["line_rows"]) >= 5
    for row in transfer["line_rows"]:
        assert set(row) >= {
            "research_line",
            "original_policy_improvable_share",
            "held_out_estimated_policy_improvable_share",
            "original_rank",
            "held_out_rank",
            "ranking_stability",
            "sign_stability",
            "top_rank_survives_holdout",
            "path_specificity",
        }
        assert row["ranking_stability"] in {"STABLE", "MATERIAL_CHANGE", "COLLAPSED"}
        assert row["sign_stability"] in {"SIGN_STABLE", "SIGN_UNSTABLE"}


def test_blindish_validation_and_subtype_audit_downgrade_path_fragile_lines(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    blindish = json.loads(
        (tmp_path / "artifacts/frontier/blindish_event_family_cross_validation.json").read_text()
    )
    subtype = json.loads(
        (tmp_path / "artifacts/frontier/slower_structural_subtype_transfer_audit.json").read_text()
    )

    assert blindish["decision"] in FrontierValidation.ALLOWED_BLINDISH_DECISIONS
    candidate_lines = {row["research_line"]: row for row in blindish["candidate_line_rows"]}
    assert {
        "recovery-with-relapse refinement",
        "2008 subtype-specific structural repair",
        "2022 H1 subtype-specific structural repair",
        "hazard as slow-stress timing assistant",
        "2018-style refinement",
    }.issubset(candidate_lines)
    assert any(row["transfer_classification"] != "TRANSFERABLE" for row in candidate_lines.values())
    assert subtype["decision"] in FrontierValidation.ALLOWED_SUBTYPE_DECISIONS
    assert {"2008 financial crisis stress", "2022 H1 structural stress"}.issubset(
        {row["event_name"] for row in subtype["subtype_rows"]}
    )
    assert all("cross_subtype_transfer_result" in row for row in subtype["subtype_rows"])


def test_hazard_transfer_requires_cross_path_evidence_not_2022_only(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    hazard = json.loads(
        (tmp_path / "artifacts/frontier/hazard_repositioning_transfer_audit.json").read_text()
    )

    assert hazard["decision"] in FrontierValidation.ALLOWED_HAZARD_DECISIONS
    assert hazard["validation_basis"] == "CROSS_PATH_NOT_2022_ONLY"
    assert len(hazard["variant_rows"]) >= 3
    for row in hazard["variant_rows"]:
        assert set(row) >= {
            "variant",
            "in_sample_h1_benefit",
            "in_sample_h2_relapse_drag",
            "cross_path_net_effect",
            "transfer_stability",
            "budget_role",
        }
    if hazard["decision"] != "HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE":
        assert hazard["recommended_role"] in {"BOUNDED_AUXILIARY_EXPERIMENT", "MONITORING_ONLY"}


def test_driver_attribution_is_numeric_and_constraints_are_separated(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    driver = json.loads(
        (tmp_path / "artifacts/frontier/improvement_driver_attribution.json").read_text()
    )
    constraints = json.loads(
        (tmp_path / "artifacts/frontier/hard_vs_soft_constraint_separation.json").read_text()
    )
    frontier = json.loads(
        (tmp_path / "artifacts/frontier/soft_constraint_frontier_estimation.json").read_text()
    )

    assert driver["decision"] in FrontierValidation.ALLOWED_DRIVER_DECISIONS
    for row in driver["event_family_rows"]:
        for key in [
            "exit_contribution",
            "hazard_contribution",
            "release_rerisk_contribution",
            "execution_translation_drag",
            "residual_irreducible_share",
        ]:
            assert isinstance(row[key], float)
        assert row["dominant_improvement_driver"]

    assert constraints["decision"] in FrontierValidation.ALLOWED_CONSTRAINT_DECISIONS
    classifications = {row["item"]: row["classification"] for row in constraints["constraint_rows"]}
    assert classifications["one-session execution lag"] == "HARD_CONSTRAINT"
    assert classifications["exit persistence rules"] == "SOFT_CONSTRAINT"
    assert classifications["module aggregation logic"] == "SOFT_CONSTRAINT"

    assert frontier["decision"] in FrontierValidation.ALLOWED_FRONTIER_DECISIONS
    for row in frontier["candidate_rows"]:
        assert set(row) >= {
            "current_policy_improvable_share",
            "soft_constraint_tuning_portion",
            "hard_constraint_blocked_portion",
            "likely_additional_gain_ceiling",
            "frontier_assessment",
        }


def test_final_verdict_embeds_acceptance_checklist_and_blocks_overclaiming(tmp_path):
    FrontierValidation(root=tmp_path).run_all()

    recommendation = json.loads(
        (tmp_path / "artifacts/frontier/final_budget_recommendation.json").read_text()
    )
    verdict = json.loads((tmp_path / "artifacts/frontier/final_verdict.json").read_text())

    assert recommendation["recommendation"] in FrontierValidation.ALLOWED_BUDGET_RECOMMENDATIONS
    assert verdict["final_verdict"] in FrontierValidation.ALLOWED_FINAL_VERDICTS
    assert verdict["candidate_maturity_restored"] is False
    assert verdict["freezeability_restored"] is False
    assert verdict["deployment_readiness_restored"] is False
    assert "frontier_acceptance_checklist" in verdict
    assert all(verdict["frontier_acceptance_checklist"]["mandatory_pass_items"].values())
    assert all(not value for value in verdict["frontier_acceptance_checklist"]["one_vote_fail_items"].values())
    if recommendation["recommendation"] in {
        "BOUNDED_BUDGET_SHOULD_REMAIN_MULTI_LINE_AND_NON_PRIMARY",
        "NO_TRANSFER_VALIDATED_PRIMARY_BUDGET_LINE_EXISTS",
    }:
        assert recommendation["primary_lines"] == []
