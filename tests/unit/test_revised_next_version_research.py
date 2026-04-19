import json

from scripts.revised_next_version_research import RevisedNextVersionResearch


def test_revised_research_generates_required_gate_and_final_artifacts(tmp_path):
    research = RevisedNextVersionResearch(root=tmp_path)

    result = research.run_all()

    assert result["final_verdict"] == "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH"

    restatement = tmp_path / "artifacts" / "post_phase4_2_implementation_restatement.json"
    final_verdict = tmp_path / "artifacts" / "revised_next_version" / "final_verdict.json"
    report = tmp_path / "reports" / "post_phase4_2_implementation_restatement.md"

    assert restatement.exists()
    assert final_verdict.exists()
    assert report.exists()

    data = json.loads(restatement.read_text())
    phase_status = {phase["phase"]: phase["current_inheritance_status"] for phase in data["phases"]}

    assert phase_status["Phase 5"] == "IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST"
    assert phase_status["Phase 5R"] == "IMPLEMENTED_BUT_MUST_BE_REVERIFIED"
    assert phase_status["next_version structural-boundary work"] == "IMPLEMENTED_BUT_MUST_BE_REVERIFIED"
    report_text = report.read_text()
    assert "What the new agent is allowed to assume going forward" in report_text
    assert "{item}" not in report_text


def test_hybrid_reclassification_is_not_primary_gap_candidate(tmp_path):
    research = RevisedNextVersionResearch(root=tmp_path)
    research.run_all()

    data = json.loads(
        (tmp_path / "artifacts" / "revised_next_version" / "hybrid_gain_reclassification.json").read_text()
    )

    assert data["verdict"] == "HYBRID_IS_SECONDARY_NON_GAP_POLICY_CANDIDATE"
    assert data["decomposition"]["aggregate_uplift_attributable_to_non_gap_slices"] > data["decomposition"]["aggregate_uplift_attributable_to_gap_slices"]
    assert data["decision_question_answer"]["survivability_priority"] == "No"


def test_final_verdict_contains_acceptance_checklist_and_loss_weighted_priority(tmp_path):
    research = RevisedNextVersionResearch(root=tmp_path)
    research.run_all()

    verdict = json.loads((tmp_path / "artifacts" / "revised_next_version" / "final_verdict.json").read_text())
    loss = json.loads(
        (tmp_path / "artifacts" / "revised_next_version" / "event_class_loss_contribution.json").read_text()
    )

    assert verdict["final_verdict"] == "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH"
    assert verdict["revised_next_version_acceptance_checklist"]["mandatory_pass_items"]["MP1"] is True
    assert verdict["revised_next_version_acceptance_checklist"]["one_vote_fail_items"]["OVF3"] is False
    assert loss["resource_allocation_conclusion"] == "BALANCED_POLICY_AND_RESIDUAL_RESEARCH_REQUIRED"
    assert loss["improvable_loss_priority_ranking"][0]["event_class"] == "2018-style partially containable drawdowns"


def test_gearbox_is_bounded_by_signal_quality(tmp_path):
    research = RevisedNextVersionResearch(root=tmp_path)
    research.run_all()

    gear = json.loads(
        (tmp_path / "artifacts" / "revised_next_version" / "gear_shift_signal_quality.json").read_text()
    )
    bounded = json.loads((tmp_path / "artifacts" / "revised_next_version" / "bounded_research.json").read_text())

    assert gear["verdict"] == "SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY"
    assert bounded["research_lines"]["discrete_gearbox"]["status"] == "BOUNDED_SECONDARY_STUDY_ONLY"
