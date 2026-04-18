from __future__ import annotations

import json

from scripts.pi_stress_phase3_research import PiStressPhase3Research


def test_phase3_research_writes_required_artifacts_and_research_verdict(tmp_path):
    result = PiStressPhase3Research(
        trace_path="artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir=tmp_path / "artifacts" / "pi_stress_phase3",
        report_dir=tmp_path / "reports",
    ).write()

    required_reports = [
        "pi_stress_phase3_regime_taxonomy.md",
        "pi_stress_phase3_representation_experiments.md",
        "pi_stress_phase3_posterior_family_comparison.md",
        "pi_stress_phase3_downstream_beta_compatibility.md",
        "pi_stress_phase3_research_verdict.md",
        "pi_stress_phase3_self_audit.md",
        "pi_stress_phase3_acceptance_checklist.md",
    ]
    for name in required_reports:
        assert (tmp_path / "reports" / name).exists(), name

    required_artifacts = [
        "regime_taxonomy.json",
        "representation_registry.json",
        "posterior_family_registry.json",
        "downstream_beta_registry.json",
        "final_research_verdict.json",
    ]
    for name in required_artifacts:
        assert (tmp_path / "artifacts" / "pi_stress_phase3" / name).exists(), name

    taxonomy = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase3" / "regime_taxonomy.json").read_text(
            encoding="utf-8"
        )
    )
    required_classes = {
        "normal",
        "ordinary_correction",
        "elevated_structural_stress",
        "systemic_crisis",
        "recovery_healing",
    }
    assert required_classes.issubset(taxonomy["classes"])
    assert taxonomy["ambiguity_zones"]["total_ambiguous_rows"] > 0

    representation = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase3" / "representation_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert "C9_baseline" in representation["stacks"]
    assert any(key.startswith("phase3_") for key in representation["stacks"])
    assert representation["direct_comparison"]["baseline"] == "C9_baseline"

    posterior = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase3" / "posterior_family_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(posterior["families"]) >= 3
    assert all("gate_results" in family for family in posterior["families"].values())
    assert all("candidate_ranking_score" in family for family in posterior["families"].values())

    downstream = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase3" / "downstream_beta_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert downstream["ranking_integration"] == "included_in_candidate_ranking"
    assert all(
        "nonstress_high_beta_trigger_rate" in row
        for row in downstream["candidate_metrics"].values()
    )

    verdict = json.loads(
        (tmp_path / "artifacts" / "pi_stress_phase3" / "final_research_verdict.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["verdict"] == verdict["verdict"]
    assert verdict["verdict"] in {
        "PROMISING_FOR_PHASE_4",
        "INCONCLUSIVE_REQUIRES_MORE_RESEARCH",
        "CURRENT_DIRECTION_EXHAUSTED_REQUIRES_NEW_ARCHITECTURE",
    }
    assert "phase3_acceptance_checklist" in verdict
    assert verdict["phase3_acceptance_checklist"]["mandatory_pass_items"]["MP1"]["status"] == "PASS"
    assert verdict["phase3_acceptance_checklist"]["one_vote_fail_items"]["OVF4"]["triggered"] == "NO"

    verdict_report = (tmp_path / "reports" / "pi_stress_phase3_research_verdict.md").read_text(
        encoding="utf-8"
    )
    forbidden = ["deploy", "production candidate", "rollout", "shadow-run", "should be merged"]
    lowered = verdict_report.lower()
    assert all(term not in lowered for term in forbidden)
