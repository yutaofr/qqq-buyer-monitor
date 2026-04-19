from scripts.pi_stress_phase4_6_research import Phase46Research


def test_phase4_6_research_generates_artifacts(tmp_path):
    # Setup paths
    reports_dir = tmp_path / "reports"
    artifacts_dir = tmp_path / "artifacts" / "pi_stress_phase4_6"

    research = Phase46Research(
        reports_dir=str(reports_dir),
        artifacts_dir=str(artifacts_dir)
    )

    research.run_all()

    # Verify JSON artifacts
    assert (artifacts_dir / "boundary_failure_characterization.json").exists()
    assert (artifacts_dir / "veto_vs_persistence_registry.json").exists()
    assert (artifacts_dir / "signal_role_registry.json").exists()
    assert (artifacts_dir / "reduced_candidate_spec.json").exists()
    assert (artifacts_dir / "governed_boundary_comparison_registry.json").exists()
    assert (artifacts_dir / "final_verdict.json").exists()

    # Verify MD reports
    assert (reports_dir / "pi_stress_phase4_6_boundary_failure_characterization.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_veto_vs_persistence_study.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_signal_role_reclassification.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_reduced_candidate_spec.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_governed_boundary_comparison.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_process_complexity_budget.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_acceptance_checklist.md").exists()
    assert (reports_dir / "pi_stress_phase4_6_final_verdict.md").exists()

def test_phase4_6_logic():
    research = Phase46Research()

    # 0. Boundary Failure Characterization
    failures = research.run_boundary_failure_characterization()
    assert "rapid_v_shape_pullbacks" in failures["failure_buckets"]

    # 1. Veto vs Persistence Discovery Study
    veto_study = research.run_veto_vs_persistence_study()
    assert veto_study["primary_mechanism"] in [
        "PERSISTENCE_PRIMARY",
        "VETO_PRIMARY",
        "COMBINED_PERSISTENCE_AND_VETO",
        "NO_RELIABLE_BOUNDARY_MECHANISM_FOUND"
    ]

    # 2. Signal-Role Reclassification
    roles = research.run_signal_role_reclassification()
    assert "high_yield_spread" in roles["signals"]

    # 3. Reduced Candidate Spec
    spec = research.construct_reduced_candidate_spec(veto_study["primary_mechanism"])
    assert spec["candidate_name"].startswith("reduced_candidate")

    # 4. Governed Boundary Comparison
    comparison = research.run_governed_boundary_comparison(spec)
    assert comparison["reference_points"]["phase3_two_stage_winner"]["total_score"] > 0
    assert "gates" in comparison["reduced_candidate_evaluation"]

    # 5. Final Verdict
    verdict = research.determine_final_verdict(comparison)
    assert verdict["verdict"] in [
        "ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH",
        "REMAIN_IN_PHASE_4_6_BOUNDARY_MODELING_WORK",
        "KEEP_PHASE4_5_CONSTRAINED_MAINLINE_AND_LIMIT_SCOPE",
        "BOUNDARY_PROBLEM_NOT_RESOLVABLE_WITH_CURRENT_DATA"
    ]
    assert "phase4_6_acceptance_checklist" in verdict
