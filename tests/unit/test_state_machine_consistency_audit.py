import json

from scripts.state_machine_consistency_audit import StateMachineConsistencyAudit


def test_state_machine_consistency_audit_writes_required_outputs(tmp_path):
    result = StateMachineConsistencyAudit(root=tmp_path).run_all()

    assert result["final_verdict"] in StateMachineConsistencyAudit.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "state_machine_consistency_vocabulary_lock.md",
        "state_machine_translation_path_reconstruction.md",
        "state_machine_divergence_window_enumeration.md",
        "state_machine_divergence_classification.md",
        "state_machine_metric_accounting_basis_audit.md",
        "state_machine_actual_leverage_recalculation.md",
        "state_machine_checklist_validity_reassessment.md",
        "state_machine_2020_boundary_reclassification.md",
        "state_machine_consistency_acceptance_checklist.md",
        "state_machine_consistency_final_verdict.md",
    }
    required_artifacts = {
        "vocabulary_lock.json",
        "translation_path_reconstruction.json",
        "divergence_window_enumeration.json",
        "divergence_classification.json",
        "metric_accounting_basis_audit.json",
        "actual_leverage_recalculation.json",
        "checklist_validity_reassessment.json",
        "2020_boundary_reclassification.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "state_machine_consistency" / filename).exists()


def test_vocabulary_and_translation_path_lock_accounting_terms(tmp_path):
    StateMachineConsistencyAudit(root=tmp_path).run_all()

    vocab = json.loads(
        (tmp_path / "artifacts/state_machine_consistency/vocabulary_lock.json").read_text()
    )
    path = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/translation_path_reconstruction.json"
        ).read_text()
    )

    required_terms = {
        "signal_state",
        "policy_state",
        "theoretical_target_leverage",
        "execution_state",
        "actual_executed_leverage",
        "accounting_basis",
        "designed_execution_delay",
        "state_translation_mismatch",
        "unexplained_inconsistency",
    }
    assert required_terms == set(vocab["terms"])
    assert path["chain"][0]["stage"] == "hazard output"
    assert path["chain"][-1]["stage"] == "metric accounting layer"
    assert any(step["delay_rule"] != "none" for step in path["chain"])
    assert "next-session executable leverage" in json.dumps(path)


def test_divergence_enumeration_and_classification_cover_required_windows(tmp_path):
    StateMachineConsistencyAudit(root=tmp_path).run_all()

    divergence = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/divergence_window_enumeration.json"
        ).read_text()
    )
    classification = json.loads(
        (
            tmp_path / "artifacts/state_machine_consistency/divergence_classification.json"
        ).read_text()
    )

    names = {row["event_name"] for row in divergence["divergence_windows"]}
    assert {
        "COVID fast cascade",
        "August 2015 liquidity vacuum",
        "Q4 2018 drawdown",
        "2022 H1 structural stress",
        "2008 financial crisis stress",
        "2022 bear rally relapse",
    }.issubset(names)
    assert divergence["summary_statistics"]["total_number_of_divergence_windows"] >= 6
    assert divergence["summary_statistics"]["worst_divergence_magnitude"] > 0
    for row in divergence["divergence_windows"]:
        assert row["duration_trading_days"] > 0
        assert row["maximum_absolute_divergence"] >= 0
        assert row["theoretical_target_leverage_path"]
        assert row["actual_executed_leverage_path"]
    assert {row["classification"] for row in classification["classified_windows"]} <= {
        "DESIGNED_EXECUTION_DELAY",
        "STATE_TRANSLATION_MISMATCH",
        "UNEXPLAINED_INCONSISTENCY",
    }


def test_metric_basis_recalculation_and_checklist_gate_are_skeptical(tmp_path):
    StateMachineConsistencyAudit(root=tmp_path).run_all()

    metric = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/metric_accounting_basis_audit.json"
        ).read_text()
    )
    recalculation = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/actual_leverage_recalculation.json"
        ).read_text()
    )
    checklist = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/checklist_validity_reassessment.json"
        ).read_text()
    )

    allowed_basis = {"ACTUAL_EXECUTED_ONLY", "THEORETICAL_ONLY", "MIXED_OR_AMBIGUOUS"}
    assert {row["accounting_basis"] for row in metric["metric_families"]} <= allowed_basis
    assert metric["mandatory_recomputation_required"] is True
    assert any(row["accounting_basis"] == "MIXED_OR_AMBIGUOUS" for row in metric["metric_families"])
    assert recalculation["required_windows_covered"] is True
    assert any(row["absolute_delta"] > 0 for row in recalculation["comparison_rows"])
    assert {
        row["survival_label"] for row in recalculation["published_claim_survival"]
    } & {
        "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING",
        "FAILS_UNDER_ACTUAL_ACCOUNTING",
    }
    assert checklist["checklist_validity_result"] in {
        "CHECKLIST_WAS_INVALID_AND_IS_NOW_REPAIRED",
        "CHECKLIST_IS_STILL_NOT_STRONG_ENOUGH",
    }
    assert checklist["revised_logic"]["convergence_positive_verdict_allowed"] is False
    assert checklist["revised_logic"]["freezeability"] == "NOT_FREEZEABLE"


def test_boundary_reclassification_and_final_verdict_are_downgraded(tmp_path):
    StateMachineConsistencyAudit(root=tmp_path).run_all()

    boundary = json.loads(
        (
            tmp_path
            / "artifacts/state_machine_consistency/2020_boundary_reclassification.json"
        ).read_text()
    )
    final = json.loads(
        (tmp_path / "artifacts/state_machine_consistency/final_verdict.json").read_text()
    )

    assert boundary["required_output"] in {
        "COVID_STYLE_EVENTS_REMAIN_PRIMARY_RESEARCH_TARGETS",
        "COVID_STYLE_EVENTS_ARE_BOUNDED_PRE_GAP_REDUCTION_TARGETS_ONLY",
        "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS",
    }
    assert boundary["required_output"] != "COVID_STYLE_EVENTS_REMAIN_PRIMARY_RESEARCH_TARGETS"
    assert final["final_verdict"] in StateMachineConsistencyAudit.ALLOWED_FINAL_VERDICTS
    assert final["final_verdict"] != (
        "STATE_MACHINE_IS_CONSISTENT_ENOUGH_FOR_CONTINUED_CONVERGENCE_RESEARCH"
    )
    assert "state_machine_consistency_acceptance_checklist" in final
    assert final["required_final_questions"]["checklist_logic_still_valid"] is False
