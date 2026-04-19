import json
from pathlib import Path


def test_phase5r_artifacts_generation():
    from scripts.pi_stress_phase5r_research import generate_phase5r_artifacts

    generate_phase5r_artifacts()

    artifacts_dir = Path("artifacts/pi_stress_phase5r")
    reports_dir = Path("reports")

    expected_artifacts = [
        "governance_split.json",
        "legacy_claim_triage.json",
        "entry_lag_vs_gap_attribution.json",
        "historical_blindish_feasibility.json",
        "structural_rework_candidates.json",
        "independent_verification.json",
        "governance_reconciliation.json",
        "final_verdict.json"
    ]

    expected_reports = [
        "pi_stress_phase5r_governance_split.md",
        "pi_stress_phase5r_legacy_claim_triage.md",
        "pi_stress_phase5r_entry_lag_vs_gap_attribution.md",
        "pi_stress_phase5r_historical_blindish_feasibility.md",
        "pi_stress_phase5r_structural_rework_candidates.md",
        "pi_stress_phase5r_independent_verification.md",
        "pi_stress_phase5r_governance_reconciliation.md",
        "pi_stress_phase5r_final_verdict.md",
        "pi_stress_phase5r_acceptance_checklist.md"
    ]

    for artifact in expected_artifacts:
        assert (artifacts_dir / artifact).exists(), f"Missing artifact: {artifact}"
        with open(artifacts_dir / artifact) as f:
            data = json.load(f)
            assert data is not None

    for report in expected_reports:
        assert (reports_dir / report).exists(), f"Missing report: {report}"
        with open(reports_dir / report) as f:
            content = f.read()
            assert len(content) > 0
