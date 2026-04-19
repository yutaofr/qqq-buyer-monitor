import json

from scripts.final_decision import FinalDecision


def test_final_decision_writes_required_reports_and_artifacts(tmp_path):
    result = FinalDecision(root=tmp_path).run_all()

    assert result["final_verdict"] in FinalDecision.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "final_decision_scope_compression_lock.md",
        "final_decision_2008_exit_persistence_micro_refinement.md",
        "final_decision_2008_narrow_transfer_check.md",
        "final_decision_execution_feasibility_audit.md",
        "final_decision_practical_value_comparison.md",
        "final_decision_demotion_freeze_rules.md",
        "final_decision_gate.md",
        "final_decision_acceptance_checklist.md",
        "final_decision_final_verdict.md",
    }
    required_artifacts = {
        "scope_compression_lock.json",
        "2008_exit_persistence_micro_refinement.json",
        "2008_narrow_transfer_check.json",
        "execution_feasibility_audit.json",
        "practical_value_comparison.json",
        "demotion_freeze_rules.json",
        "final_decision_gate.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts/final_decision" / filename).exists()


def test_scope_lock_is_two_track_only_and_explicitly_excludes_demoted_lines(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    scope = json.loads(
        (tmp_path / "artifacts/final_decision/scope_compression_lock.json").read_text()
    )

    assert scope["decision"] == "SCOPE_IS_PROPERLY_COMPRESSED"
    assert scope["included_tracks"] == [
        "2008-type monotonic structural stress exit persistence micro-refinement",
        "execution feasibility audit",
        "final go / no-go judgment on continued development value",
    ]
    assert scope["phase_valid"] is True
    assert set(scope["required_exclusions"]) == {
        "hazard primary line",
        "recovery-with-relapse primary line",
        "2022 H1 subtype primary line",
        "hybrid",
        "gearbox",
        "residual protection operationalization",
        "new model family",
        "broad multi-line optimization",
    }


def test_2008_micro_refinement_contains_required_variants_and_metrics(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    micro = json.loads(
        (
            tmp_path
            / "artifacts/final_decision/2008_exit_persistence_micro_refinement.json"
        ).read_text()
    )

    assert micro["decision"] in FinalDecision.ALLOWED_MICRO_REFINEMENT_DECISIONS
    assert {
        "current baseline persistence rule",
        "slightly earlier persistence lock variant",
        "slightly stricter recovery confirmation variant",
        "conservative balanced variant",
    }.issubset({row["variant"] for row in micro["variant_rows"]})
    for row in micro["variant_rows"]:
        assert set(row) >= {
            "variant",
            "actual_executed_policy_contribution",
            "incremental_gain_vs_baseline",
            "recovery_miss",
            "time_in_defensive_state",
            "false_early_release_count",
            "residual_unrepaired_share",
            "likely_additional_gain_ceiling",
            "execution_translation_drag_interaction",
        }
        assert row["event_name"] == "2008 financial crisis stress"
    assert micro["admissible_gain_requires_actual_executed_bounded_non_overfit"] is True


def test_narrow_transfer_check_can_close_track_a_if_2008_refinement_collapses(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    transfer = json.loads(
        (tmp_path / "artifacts/final_decision/2008_narrow_transfer_check.json").read_text()
    )

    assert transfer["decision"] in FinalDecision.ALLOWED_TRANSFER_DECISIONS
    assert {"2022 H1 structural stress", "Q4 2018 drawdown"}.issubset(
        {row["event_name"] for row in transfer["heldout_rows"]}
    )
    assert set(transfer) >= {
        "selected_variant",
        "in_sample_gain",
        "held_out_gain",
        "transfer_ratio",
        "sign_flips",
        "neighboring_path_damage_increases",
        "refinement_admissibility",
    }
    if transfer["decision"] == "2008_REFINEMENT_FAILS_TRANSFER_CHECK":
        assert transfer["track_a_status"] == "CLOSED"
    else:
        assert transfer["track_a_status"] in {"OPEN_BOUNDED", "WEAK_BUT_USEFUL"}


def test_execution_feasibility_is_grounded_and_classified_item_by_item(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    audit = json.loads(
        (tmp_path / "artifacts/final_decision/execution_feasibility_audit.json").read_text()
    )

    assert audit["decision"] in FinalDecision.ALLOWED_EXECUTION_DECISIONS
    assert audit["account_assumptions"] == FinalDecision.ACCOUNT_ASSUMPTIONS
    assert len(audit["audit_rows"]) == 6
    for row in audit["audit_rows"]:
        assert row["classification"] in FinalDecision.EXECUTION_CLASSIFICATIONS
        assert set(row) >= {
            "item",
            "classification",
            "operational_complexity",
            "data_requirements",
            "meaningfully_reduces_execution_translation_drag",
            "meaningfully_reduces_gap_adjacent_exposure",
            "testable_without_full_rebuild",
            "grounding",
        }
    if audit["decision"] == "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST":
        assert not audit["material_drag_reduction_available"]


def test_practical_value_gate_and_verdict_are_conservative_under_failed_tracks(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    comparison = json.loads(
        (tmp_path / "artifacts/final_decision/practical_value_comparison.json").read_text()
    )
    gate = json.loads(
        (tmp_path / "artifacts/final_decision/final_decision_gate.json").read_text()
    )
    verdict = json.loads((tmp_path / "artifacts/final_decision/final_verdict.json").read_text())

    assert comparison["decision"] in FinalDecision.ALLOWED_COMPARISON_DECISIONS
    assert gate["decision"] in FinalDecision.ALLOWED_GATE_DECISIONS
    assert verdict["final_verdict"] in FinalDecision.ALLOWED_FINAL_VERDICTS
    assert verdict["candidate_maturity_restored"] is False
    assert verdict["freezeability_restored"] is False
    assert verdict["deployment_readiness_restored"] is False
    assert verdict["future_primary_budget_line_expected"] is False
    assert "final_decision_acceptance_checklist" in verdict
    assert all(verdict["final_decision_acceptance_checklist"]["mandatory_pass_items"].values())
    assert all(not value for value in verdict["final_decision_acceptance_checklist"]["one_vote_fail_items"].values())
    if gate["decision"] == "ACTIVE_DEVELOPMENT_SHOULD_STOP_AND_SYSTEM_SHOULD_BE_REPOSITIONED":
        assert verdict["final_verdict"] in {
            "STOP_ACTIVE_DEVELOPMENT_AND_KEEP_AS_RISK_FRAMEWORK",
            "STOP_ACTIVE_DEVELOPMENT_AND_ARCHIVE",
        }


def test_all_non_selected_lines_are_demoted_and_cannot_reenter_as_near_primary(tmp_path):
    FinalDecision(root=tmp_path).run_all()

    demotion = json.loads(
        (tmp_path / "artifacts/final_decision/demotion_freeze_rules.json").read_text()
    )
    verdict = json.loads((tmp_path / "artifacts/final_decision/final_verdict.json").read_text())

    expected_lines = {
        "recovery-with-relapse refinement",
        "2022 H1 subtype refinement",
        "hazard repositioning",
        "2018-style refinement",
        "hybrid",
        "gearbox",
        "residual protection",
        "2020-like repair",
        "2015-style repair",
    }
    rows = {row["line"]: row for row in demotion["line_rows"]}
    assert expected_lines == set(rows)
    for row in rows.values():
        assert row["classification"] in FinalDecision.DEMOTION_CLASSIFICATIONS
        assert row["near_primary_allowed"] is False
    assert verdict["non_selected_line_classifications"] == {
        line: rows[line]["classification"] for line in expected_lines
    }
