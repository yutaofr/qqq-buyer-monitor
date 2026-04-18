from __future__ import annotations

import json

from scripts.pi_stress_phase4_research import PiStressPhase4Research


def test_phase4_research_runs_workstream0_before_constrained_phase4_outputs(tmp_path):
    result = PiStressPhase4Research(
        trace_path="artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir=tmp_path / "artifacts" / "pi_stress_phase4",
        report_dir=tmp_path / "reports",
    ).write()

    required_reports = [
        "pi_stress_phase4_identification_feasibility.md",
        "pi_stress_phase4_architecture_spec.md",
        "pi_stress_phase4_data_state_expansion.md",
        "pi_stress_phase4_taxonomy_denoising.md",
        "pi_stress_phase4_mainline_training.md",
        "pi_stress_phase4_mainline_vs_challenger.md",
        "pi_stress_phase4_downstream_beta_screen.md",
        "pi_stress_phase4_self_audit.md",
        "pi_stress_phase4_acceptance_checklist.md",
        "pi_stress_phase4_final_verdict.md",
    ]
    for name in required_reports:
        assert (tmp_path / "reports" / name).exists(), name

    required_artifacts = [
        "identification_feasibility.json",
        "architecture_spec.json",
        "data_state_inventory.json",
        "state_family_information_gain.json",
        "taxonomy_denoising_registry.json",
        "mainline_training_registry.json",
        "challenger_registry.json",
        "downstream_beta_screen_registry.json",
        "final_verdict.json",
    ]
    for name in required_artifacts:
        assert (tmp_path / "artifacts" / "pi_stress_phase4" / name).exists(), name

    feasibility = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "identification_feasibility.json").read_text(
            encoding="utf-8"
        )
    )
    assert feasibility["decision"] in {
        "FEASIBLE_AS_SPECIFIED",
        "FEASIBLE_ONLY_WITH_CLASS_MERGE_OR_COMPLEXITY_REDUCTION",
        "NOT_FEASIBLE_UNDER_CURRENT_TAXONOMY_AND_DATA",
    }
    assert feasibility["completed_before_mainline_training"] is True
    assert set(feasibility["class_support"]) >= {
        "normal",
        "ordinary_correction",
        "elevated_structural_stress",
        "systemic_crisis",
        "recovery_healing",
        "transition_onset",
    }
    for support in feasibility["class_support"].values():
        assert "raw_row_count" in support
        assert "confidence_weighted_row_count" in support
        assert "contiguous_episode_count" in support
        assert "usable_support_for_independent_modeling" in support
    assert "stage_coupling_proxy_overlap_audit" in feasibility
    assert "incremental_value_audit" in feasibility

    architecture = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "architecture_spec.json").read_text(
            encoding="utf-8"
        )
    )
    assert architecture["mainline"] == "two_stage_anomaly_severity"
    assert architecture["challenger"] == "hierarchical_stress_posterior"
    assert architecture["reference_baseline"] == "C9_baseline_reference"
    assert architecture["conductor_rule"] == "abstract_stage_outputs_only"
    if feasibility["decision"] != "FEASIBLE_AS_SPECIFIED":
        assert architecture["constraint_policy"]["full_six_class_independent_modeling"] == "DISALLOWED"

    data_inventory = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "data_state_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(data_inventory["state_families"]) == {
        "cross_sectional_stress_state",
        "volatility_surface_panic_structure_state",
        "credit_liquidity_regime_state",
        "cross_asset_divergence_state",
    }

    training = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "mainline_training_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert "phase4_two_stage_mainline" in training["candidates"]
    assert "phase3_two_stage_winner" in training["candidates"]
    assert "C9_baseline_reference" in training["candidates"]
    assert training["candidate_roles"]["mainline"] == "phase4_two_stage_mainline"
    assert training["candidate_roles"]["reference_only"] == "C9_baseline_reference"

    challenger = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "challenger_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert challenger["formal_challenger"] == "hierarchical_stress_posterior"
    assert "phase4_hierarchical_challenger" in challenger["candidates"]

    verdict = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase4" / "final_verdict.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["verdict"] == verdict["verdict"]
    assert verdict["verdict"] in {
        "READY_FOR_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH",
        "PROMISING_BUT_NEEDS_MORE_PHASE_4_WORK",
        "MAINLINE_NOT_SUPERIOR_KEEP_RESEARCH_OPEN",
        "CURRENT_EXPANSION_DIRECTION_EXHAUSTED",
    }
    assert "phase4_acceptance_checklist" in verdict
    assert verdict["phase4_acceptance_checklist"]["mandatory_pass_items"]["MP1"]["status"] == "PASS"

    lowered = (tmp_path / "reports" / "pi_stress_phase4_final_verdict.md").read_text(
        encoding="utf-8"
    ).lower()
    forbidden = ["deployable", "rollout", "production candidate", "go-live"]
    assert all(term not in lowered for term in forbidden)
