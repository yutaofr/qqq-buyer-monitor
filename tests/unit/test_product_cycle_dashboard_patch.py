import json

from scripts.product_cycle_dashboard import ProductDashboardInput
from scripts.product_cycle_dashboard_patch import PatchVariant, ProductCycleDashboardPatch


def test_patch_pipeline_writes_required_reports_artifacts_and_allowed_vocab(tmp_path):
    result = ProductCycleDashboardPatch(root=tmp_path).run_all()

    assert result["final_verdict"] in {
        "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD",
        "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS",
        "DO_NOT_LAUNCH_PRODUCT_YET",
    }

    required_reports = {
        "product_patch_launch_claim_lock.md",
        "product_patch_calibration_failure_audit.md",
        "product_patch_recovery_calibration_repair.md",
        "product_patch_stress_liquidity_anchoring_repair.md",
        "product_patch_probability_diffusion_repair.md",
        "product_patch_index_html_ui_alignment.md",
        "product_patch_full_path_integration_audit.md",
        "product_patch_historical_revalidation.md",
        "product_patch_self_iteration_gate.md",
        "product_patch_acceptance_checklist.md",
        "product_patch_final_verdict.md",
    }
    required_artifacts = {
        "launch_claim_lock.json",
        "calibration_failure_audit.json",
        "recovery_calibration_repair.json",
        "stress_liquidity_anchoring_repair.json",
        "probability_diffusion_repair.json",
        "index_html_ui_alignment.json",
        "full_path_integration_audit.json",
        "historical_revalidation.json",
        "self_iteration_gate.json",
        "final_verdict.json",
    }

    for filename in required_reports:
        assert (tmp_path / "reports" / filename).exists()
    for filename in required_artifacts:
        assert (tmp_path / "artifacts" / "product_patch" / filename).exists()

    decisions = {
        "launch_claim_lock": {
            "LAUNCH_CLAIM_DOWNGRADED_PENDING_PATCH",
            "LAUNCH_CLAIM_ALREADY_CONSERVATIVE_ENOUGH",
            "LAUNCH_LANGUAGE_REMAINS_OVERSTATED",
        },
        "calibration_failure_audit": {
            "CALIBRATION_FAILURES_ARE_PRECISELY_LOCALIZED",
            "CALIBRATION_FAILURES_ARE_PARTIALLY_LOCALIZED",
            "CALIBRATION_FAILURES_REMAIN_POORLY_UNDERSTOOD",
        },
        "recovery_calibration_repair": {
            "RECOVERY_CALIBRATION_IS_MATERIALLY_REPAIRED",
            "RECOVERY_CALIBRATION_IS_IMPROVED_BUT_STILL_LIMITED",
            "RECOVERY_CALIBRATION_REMAINS_UNACCEPTABLE",
        },
        "stress_liquidity_anchoring_repair": {
            "ACUTE_LIQUIDITY_EVENTS_ARE_NOW_PROPERLY_ANCHORED",
            "ACUTE_LIQUIDITY_ANCHORING_IS_IMPROVED_BUT_NOT_FULLY_RELIABLE",
            "ACUTE_LIQUIDITY_ANCHORING_REMAINS_BROKEN",
        },
        "probability_diffusion_repair": {
            "PROBABILITY_DIFFUSION_IS_MATERIALLY_REDUCED",
            "PROBABILITY_DIFFUSION_IS_IMPROVED_BUT_STILL_NOTICEABLE",
            "PROBABILITY_DIFFUSION_REMAINS_PRODUCT_BLOCKING",
        },
        "index_html_ui_alignment": {
            "INDEX_HTML_AND_UI_ARE_FULLY_ALIGNED",
            "INDEX_HTML_AND_UI_ARE_PARTIALLY_ALIGNED",
            "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY",
        },
        "full_path_integration_audit": {
            "FULL_PRODUCT_PATH_IS_INTERNALLY_CONSISTENT",
            "FULL_PRODUCT_PATH_IS_MOSTLY_CONSISTENT_BUT_PATCHY",
            "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY",
        },
        "historical_revalidation": {
            "PATCHED_PRODUCT_IS_HISTORICALLY_MEANINGFULLY_BETTER",
            "PATCHED_PRODUCT_IS_IMPROVED_BUT_STILL_LIMITED",
            "PATCHED_PRODUCT_DOES_NOT_IMPROVE_ENOUGH",
        },
        "self_iteration_gate": {
            "SELF_ITERATION_COMPLETED_AND_PATCH_MEETS_STANDARD",
            "SELF_ITERATION_COMPLETED_BUT_PRODUCT_REMAINS_LIMITED",
            "SELF_ITERATION_EXHAUSTED_AND_PRODUCT_SHOULD_NOT_LAUNCH",
        },
    }

    for artifact_name, allowed in decisions.items():
        payload = json.loads(
            (tmp_path / "artifacts" / "product_patch" / f"{artifact_name}.json").read_text()
        )
        assert payload["decision"] in allowed

    final = json.loads((tmp_path / "artifacts/product_patch/final_verdict.json").read_text())
    assert final["final_verdict"] in {
        "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD",
        "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS",
        "DO_NOT_LAUNCH_PRODUCT_YET",
    }
    assert "product_patch_acceptance_checklist" in final


def test_patch_artifacts_include_required_calibration_anchoring_diffusion_and_ui_tables(tmp_path):
    ProductCycleDashboardPatch(root=tmp_path).run_all()

    calibration = json.loads(
        (tmp_path / "artifacts/product_patch/calibration_failure_audit.json").read_text()
    )
    recovery = json.loads(
        (tmp_path / "artifacts/product_patch/recovery_calibration_repair.json").read_text()
    )
    stress = json.loads(
        (tmp_path / "artifacts/product_patch/stress_liquidity_anchoring_repair.json").read_text()
    )
    diffusion = json.loads(
        (tmp_path / "artifacts/product_patch/probability_diffusion_repair.json").read_text()
    )
    ui = json.loads((tmp_path / "artifacts/product_patch/index_html_ui_alignment.json").read_text())
    full_path = json.loads(
        (tmp_path / "artifacts/product_patch/full_path_integration_audit.json").read_text()
    )

    assert {"RECOVERY", "STRESS", "FAST_CASCADE_BOUNDARY", "LATE_CYCLE"}.issubset(
        calibration["stage_metrics"]
    )
    assert "reliability_curve_summary" in calibration["stage_metrics"]["RECOVERY"]
    assert "dominant_label_frequency" in calibration["stage_metrics"]["STRESS"]
    assert "false_declaration_rates" in calibration

    assert "pre_patch" in recovery["comparison"]
    assert "candidate_variants" in recovery["comparison"]
    assert "selected_patch" in recovery["comparison"]
    assert "RECOVERY" in recovery["patch_targets"]

    assert "August 2015 liquidity vacuum" in stress["event_comparison"]
    assert "2020 fast cascade" in stress["event_comparison"]
    assert "ordinary late-cycle deterioration contrast" in stress["event_comparison"]
    august = stress["event_comparison"]["August 2015 liquidity vacuum"]
    assert "pre_patch_dominant_stage_path" in august
    assert "post_patch_dominant_stage_path" in august

    assert "pre_patch" in diffusion["comparison"]
    assert "post_patch" in diffusion["comparison"]
    assert "diffuse_or_unstable_count" in diffusion["comparison"]["pre_patch"]
    assert "average_entropy_by_stage" in diffusion["comparison"]["post_patch"]

    assert ui["entrypoint"] == "src/web/public/index.html"
    assert "alignment_matrix" in ui
    assert "stage_distribution_display" in ui["alignment_matrix"]
    assert "boundary_warning_display" in ui["alignment_matrix"]

    assert "consistency_matrix" in full_path
    assert "engine_output_schema" in full_path["consistency_matrix"]
    assert "dashboard_rendering_schema" in full_path["consistency_matrix"]


def test_patch_final_verdict_remains_probability_dashboard_only_and_lists_trust_boundaries(tmp_path):
    ProductCycleDashboardPatch(root=tmp_path).run_all()

    final = json.loads((tmp_path / "artifacts/product_patch/final_verdict.json").read_text())

    assert final["automatic_beta_control_restored"] is False
    assert final["turning_point_prediction_solved"] is False
    assert final["ui_aligned_with_probability_dashboard"] in {True, False}
    assert final["docs_ui_engine_consistent"] in {True, False}
    assert final["self_iteration_was_needed"] in {True, False}
    assert "RECOVERY" in final["trust_summary"]
    assert "STRESS" in final["trust_summary"]
    assert "acute_liquidity" in final["trust_summary"]
    assert "probability_vectors" in final["trust_summary"]


def test_patch_frame_adds_rolling_recovery_compliance_ratio_features(tmp_path):
    frame = ProductCycleDashboardPatch(root=tmp_path)._build_patch_frame()

    required = {
        "repair_ratio_5d",
        "repair_ratio_10d",
        "stress_below_threshold_ratio",
        "breadth_repair_ratio",
        "recovery_compliance_ratio",
        "insufficient_recovery_compliance",
        "release_while_unresolved",
        "recent_relapse_signal",
    }

    assert required.issubset(frame.columns)
    for column in {
        "repair_ratio_5d",
        "repair_ratio_10d",
        "stress_below_threshold_ratio",
        "breadth_repair_ratio",
        "recovery_compliance_ratio",
    }:
        assert frame[column].between(0.0, 1.0).all(), column


def test_relapse_penalty_is_auditable_and_only_applies_to_recovery_logit(tmp_path):
    patch = ProductCycleDashboardPatch(root=tmp_path)
    variant = PatchVariant(
        name="bounded_patch",
        temperature=0.90,
        smoothing_alpha=0.36,
        boundary_passthrough=0.88,
        recovery_gain=0.18,
        relapse_penalty=0.22,
        stress_gain=0.0,
        boundary_gain=0.0,
        late_cycle_penalty=0.0,
        diffusion_gamma=0.0,
    )
    item = ProductDashboardInput(
        date="2026-04-19",
        hazard_score=0.42,
        hazard_percentile=0.76,
        stress_score=0.36,
        breadth_proxy=0.44,
        volatility_percentile=0.63,
        structural_stress=False,
        repair_confirmation=True,
        relapse_flag=True,
        hazard_delta_5d=0.03,
        breadth_delta_10d=-0.04,
        volatility_delta_10d=0.06,
        boundary_pressure=0.01,
        stress_persistence_days=4,
        repair_persistence_days=5,
    )
    row = {
        "acute_liquidity_score": 0.12,
        "repair_evidence_score": 0.62,
        "repair_ratio_5d": 0.40,
        "repair_ratio_10d": 0.50,
        "stress_below_threshold_ratio": 0.30,
        "breadth_repair_ratio": 0.20,
        "recovery_compliance_ratio": 0.35,
        "release_while_unresolved": 1.0,
        "recent_relapse_signal": 1.0,
        "insufficient_recovery_compliance": 1.0,
    }

    base_logits = patch._stage_logits_variant(item=item, row=row, variant=variant, apply_penalty=False)
    penalized_logits = patch._stage_logits_variant(
        item=item, row=row, variant=variant, apply_penalty=True
    )
    penalty = patch._recovery_logit_relapse_penalty(row=row, variant=variant)

    assert penalty["signals"] == {
        "release_while_unresolved": 1.0,
        "recent_relapse_signal": 1.0,
        "insufficient_recovery_compliance": 1.0,
    }
    assert penalty["penalty"] > 0.0
    assert penalized_logits["RECOVERY"] < base_logits["RECOVERY"]
    for stage in {"EXPANSION", "LATE_CYCLE", "STRESS", "FAST_CASCADE_BOUNDARY"}:
        assert penalized_logits[stage] == base_logits[stage]


def test_final_verdict_includes_required_batch2_validation_checks(tmp_path):
    ProductCycleDashboardPatch(root=tmp_path).run_all()

    final = json.loads((tmp_path / "artifacts/product_patch/final_verdict.json").read_text())
    checks = final["batch2_validation_checks"]

    assert set(checks) == {
        "false_recovery_declaration_rate_improves",
        "recovery_calibration_gap_improves",
        "stress_late_cycle_not_materially_degraded",
        "probability_diffusion_not_replaced_by_fake_confidence",
    }
