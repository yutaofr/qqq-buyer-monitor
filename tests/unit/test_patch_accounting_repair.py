import json

from scripts.patch_accounting_repair import PatchAccountingRepair


def test_patch_accounting_repair_writes_required_outputs(tmp_path):
    result = PatchAccountingRepair(root=tmp_path).run_all()

    assert result["final_verdict"] in PatchAccountingRepair.ALLOWED_FINAL_VERDICTS

    required_reports = {
        "patch_scope_lock.md",
        "patch_event_class_loss_contribution.md",
        "patch_structural_boundary_role_separation.md",
        "patch_false_reentry_exit_split.md",
        "patch_verdict_budget_reconstruction.md",
        "patch_accounting_basis_gate.md",
        "patch_checklist_verdict_rebinding.md",
        "patch_2020_boundary_confirmation.md",
        "patch_acceptance_checklist.md",
        "patch_final_verdict.md",
    }
    required_artifacts = {
        "patch_scope_lock.json",
        "event_class_loss_contribution.json",
        "structural_boundary_role_separation.json",
        "false_reentry_exit_split.json",
        "verdict_budget_reconstruction.json",
        "accounting_basis_gate.json",
        "checklist_verdict_rebinding.json",
        "2020_boundary_confirmation.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "patch" / filename).exists()


def test_scope_lock_classifies_old_mixed_families_and_blocks_drift(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    scope = json.loads((tmp_path / "artifacts/patch/patch_scope_lock.json").read_text())

    required_statements = scope["required_statements"]
    assert required_statements["does_not_optimize_model_modules"] is True
    assert required_statements["does_not_reopen_hybrid_as_primary"] is True
    assert required_statements["does_not_reopen_gearbox_as_primary"] is True
    assert required_statements["does_not_reopen_residual_protection_operationalization"] is True
    assert required_statements["repairs_only_accounting_role_separation_and_gates"] is True
    layers = {row["metric_family"]: row["object_layer"] for row in scope["known_mixed_or_ambiguous_families"]}
    assert layers["event-class loss contribution metrics"] == "data-layer object"
    assert layers["structural non-defendability metrics"] == "boundary-layer object"
    assert layers["false re-entry / false exit metrics"] == "diagnostic object"
    assert layers["budget allocation metrics"] == "verdict-layer object"


def test_event_class_loss_contribution_is_unified_actual_executed_space(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    loss = json.loads((tmp_path / "artifacts/patch/event_class_loss_contribution.json").read_text())

    assert loss["decision"] == "LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN"
    assert loss["accounting_basis"] == "ACTUAL_EXECUTED_ONLY"
    event_classes = {row["event_class"] for row in loss["event_class_rows"]}
    assert {
        "2020-like fast-cascade / dominant overnight gap",
        "2015-style liquidity vacuum / flash impairment",
        "2018-style partially containable drawdown",
        "slower structural stress",
        "recovery-with-relapse",
        "rapid V-shape ordinary correction",
    }.issubset(event_classes)
    for row in loss["event_class_rows"]:
        assert set(row) >= {
            "baseline_cumulative_return_contribution",
            "policy_cumulative_return_contribution",
            "policy_contribution",
            "baseline_tail_loss_contribution",
            "policy_tail_loss_contribution",
            "policy_improvable_share",
            "residual_unrepaired_share",
        }
        assert row["basis_proof"]["baseline_return"] == "baseline_actual_executed_return"
        assert row["basis_proof"]["policy_return"] == "policy_actual_executed_return"


def test_structural_boundary_is_boundary_only_and_not_scored(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    structural = json.loads(
        (tmp_path / "artifacts/patch/structural_boundary_role_separation.json").read_text()
    )

    assert structural["decision"] == "STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY"
    assert structural["basis_classification"] == "MARKET_STRUCTURE_ATTRIBUTION"
    for row in structural["structural_metrics"]:
        assert row["remains_valid_as_market_structure_attribution"] is True
        assert row["removed_from_policy_aggregation"] is True
        assert row["may_enter_policy_value_score"] is False
        assert row["prior_downstream_uses_must_be_downgraded"] is True


def test_false_reentry_exit_count_and_damage_are_split(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    split = json.loads((tmp_path / "artifacts/patch/false_reentry_exit_split.json").read_text())

    assert split["decision"] == "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT"
    assert split["operational_diagnostic_family"]["allowed_downstream_role"] == "DIAGNOSTIC_ONLY"
    assert split["damage_accounting_family"]["accounting_basis"] == "ACTUAL_EXECUTED_ONLY"
    assert split["damage_accounting_family"]["admissible_downstream"] is True
    for row in split["split_metrics"]:
        assert row["old_uses_must_be_invalidated"] is True
        assert row["damage_version_admissible_downstream"] is True


def test_verdict_budget_reconstruction_and_pre_gate_block_mixed_inputs(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    budget = json.loads((tmp_path / "artifacts/patch/verdict_budget_reconstruction.json").read_text())
    gate = json.loads((tmp_path / "artifacts/patch/accounting_basis_gate.json").read_text())

    assert budget["decision"] == "VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN"
    assert budget["policy_value_vector"]["basis"] == "ACTUAL_EXECUTED_ONLY"
    assert budget["structural_constraint_vector"]["basis"] == "MARKET_STRUCTURE_ATTRIBUTION"
    assert budget["structural_constraint_vector"]["used_in_policy_value_score"] is False
    assert gate["decision"] == "ACCOUNTING_BASIS_GATE_IS_OPERATIONAL"
    assert gate["execution_order"] == "PRE_VERDICT"
    blocked = {row["metric_family"]: row for row in gate["family_gate_rows"] if row["blocked"]}
    assert "old mixed-input verdict path" in blocked
    assert blocked["old mixed-input verdict path"]["prior_use_invalid"] is True


def test_rebound_checklist_boundary_and_final_verdict(tmp_path):
    PatchAccountingRepair(root=tmp_path).run_all()

    rebinding = json.loads((tmp_path / "artifacts/patch/checklist_verdict_rebinding.json").read_text())
    boundary = json.loads((tmp_path / "artifacts/patch/2020_boundary_confirmation.json").read_text())
    final = json.loads((tmp_path / "artifacts/patch/final_verdict.json").read_text())

    assert rebinding["decision"] == "CHECKLIST_AND_VERDICT_ARE_NOW_REBOUND_TO_VALID_GATES"
    assert rebinding["patched_checklist"]["blocks_previously_admissible_mixed_path"] is True
    assert rebinding["primary_language_rule"]["primary_means_only"] == "bounded budget priority"
    assert boundary["decision"] == "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS"
    assert final["final_verdict"] == "PATCH_SUCCEEDED_AND_CONVERGENCE_WORK_MAY_RESUME_UNDER_PATCHED_GATES"
    assert final["required_final_questions"]["event_class_loss_contribution_accounting_clean"] is True
    assert final["required_final_questions"]["2020_like_remains_boundary_disclosure"] is True
    assert "patch_acceptance_checklist" in final
    assert all(not value for value in final["patch_acceptance_checklist"]["one_vote_fail_items"].values())
