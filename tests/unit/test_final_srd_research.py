import json

from scripts.final_srd_research import FinalSrdResearch


def test_final_srd_pipeline_recomputes_core_metrics_from_data(tmp_path):
    research = FinalSrdResearch(root=tmp_path)

    result = research.run_all()

    assert result["final_verdict"] in {
        "CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH",
        "CONTINUE_WITH_TARGETED_RESIDUAL_PROTECTION_RESEARCH",
        "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH",
        "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_HIGHER_COMPLEXITY",
        "COMPUTATIONAL_FOUNDATION_NOT_TRUSTWORTHY_ENOUGH_FOR_PRIORITY_SETTING",
    }

    integrity = json.loads((tmp_path / "artifacts/final_srd/computation_integrity_gate.json").read_text())
    targets = {row["target"]: row for row in integrity["targets"]}

    assert targets["structural non-defendability evidence"]["credibility"] == "COMPUTATIONALLY_TRUSTWORTHY"
    assert targets["event-class loss contribution"]["credibility"] == "COMPUTATIONALLY_TRUSTWORTHY"
    assert targets["hybrid transfer decomposition"]["credibility"] == "COMPUTATIONALLY_TRUSTWORTHY"
    assert targets["gear-shift signal quality"]["credibility"] in {
        "COMPUTATIONALLY_TRUSTWORTHY",
        "PARTIALLY_COMPUTATIONALLY_TRUSTWORTHY",
    }
    assert targets["convex overlay feasibility metrics"]["credibility"] == "ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH"
    assert integrity["downstream_budget_allocation_allowed"] is True


def test_structural_boundary_rebuild_contains_gap_contribution_and_event_classes(tmp_path):
    research = FinalSrdResearch(root=tmp_path)
    research.run_all()

    structural = json.loads((tmp_path / "artifacts/final_srd/structural_boundary_rebuild.json").read_text())
    classes = {row["event_class"]: row["classification"] for row in structural["event_class_boundaries"]}

    assert structural["top_level_verdict"] in {
        "STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS",
        "STRUCTURAL_NON_DEFENDABILITY_PARTIALLY_CONFIRMED",
    }
    assert structural["top_level_computations"]["execution_gap_contribution_share"] > 0
    assert classes["2020-like fast cascades with dominant overnight gaps"] in {
        "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS",
        "RESIDUAL_PROTECTION_LAYER_REQUIRED",
    }


def test_loss_contribution_rebuild_drives_budget_with_recomputed_rankings(tmp_path):
    research = FinalSrdResearch(root=tmp_path)
    research.run_all()

    loss = json.loads((tmp_path / "artifacts/final_srd/event_class_loss_contribution_rebuild.json").read_text())

    assert loss["decision"] in {
        "POLICY_LAYER_RESEARCH_SHOULD_DOMINATE",
        "RESIDUAL_PROTECTION_RESEARCH_SHOULD_DOMINATE",
        "BALANCED_POLICY_AND_RESIDUAL_RESEARCH_REQUIRED",
        "FURTHER_COMPLEXITY_HAS_LOW_EXPECTED_VALUE",
    }
    assert len(loss["frequency_weighted_priority_ranking"]) >= 6
    assert len(loss["severity_weighted_priority_ranking"]) >= 6
    assert len(loss["improvable_loss_priority_ranking"]) >= 6
    assert all("computed_from_price_data" in row["provenance"] for row in loss["event_classes"])


def test_hybrid_and_gear_rebuild_gate_prioritization(tmp_path):
    research = FinalSrdResearch(root=tmp_path)
    research.run_all()

    hybrid = json.loads((tmp_path / "artifacts/final_srd/hybrid_transfer_decomposition_rebuild.json").read_text())
    gear = json.loads((tmp_path / "artifacts/final_srd/gear_shift_signal_quality_rebuild.json").read_text())
    allocation = json.loads((tmp_path / "artifacts/final_srd/research_budget_allocation.json").read_text())

    assert hybrid["decision"] in {
        "HYBRID_IS_GAP_RELEVANT_PRIMARY_CANDIDATE",
        "HYBRID_IS_SECONDARY_NON_GAP_POLICY_CANDIDATE",
        "HYBRID_IS_OVERSTATED_AND_LOW_PRIORITY",
    }
    assert hybrid["decomposition"]["aggregate_uplift_attributable_to_gap_slices"] is not None
    assert hybrid["decomposition"]["aggregate_uplift_attributable_to_non_gap_slices"] is not None
    assert gear["decision"] in {
        "SHIFT_SIGNAL_QUALITY_SUFFICIENT_FOR_GEARBOX_RESEARCH",
        "SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY",
        "SHIFT_SIGNAL_QUALITY_TOO_WEAK_FOR_MEANINGFUL_GEARBOX_RESEARCH",
    }
    if gear["decision"] != "SHIFT_SIGNAL_QUALITY_SUFFICIENT_FOR_GEARBOX_RESEARCH":
        assert allocation["candidate_lines"]["discrete_gearbox"]["budget_status"] != "PRIMARY"


def test_final_verdict_embeds_acceptance_checklist(tmp_path):
    research = FinalSrdResearch(root=tmp_path)
    research.run_all()

    verdict = json.loads((tmp_path / "artifacts/final_srd/final_verdict.json").read_text())

    assert verdict["final_verdict"] in {
        "CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH",
        "CONTINUE_WITH_TARGETED_RESIDUAL_PROTECTION_RESEARCH",
        "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH",
        "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_HIGHER_COMPLEXITY",
        "COMPUTATIONAL_FOUNDATION_NOT_TRUSTWORTHY_ENOUGH_FOR_PRIORITY_SETTING",
    }
    assert "final_srd_acceptance_checklist" in verdict
    assert verdict["final_srd_acceptance_checklist"]["mandatory_pass_items"]["MP1"] is True
    assert verdict["final_srd_acceptance_checklist"]["one_vote_fail_items"]["OVF1"] is False
