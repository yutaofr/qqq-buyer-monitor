from __future__ import annotations

import json

from scripts.pi_stress_final_go_no_go import PiStressFinalGoNoGo
from tests.unit.pi_stress_test_fixtures import (
    make_pi_stress_registry_json,
    make_pi_stress_trace_csv,
)


def test_final_go_no_go_writes_binary_decision_and_red_flag_gate(tmp_path):
    trace_path = make_pi_stress_trace_csv(tmp_path)
    registry_path = make_pi_stress_registry_json(tmp_path, trace_path)

    result = PiStressFinalGoNoGo(
        registry_path=registry_path,
        trace_path=trace_path,
        output_dir=tmp_path / "artifacts",
        report_dir=tmp_path / "reports",
    ).write()

    decision_path = tmp_path / "artifacts" / "final_decision.json"
    assert decision_path.exists()
    decision = json.loads(decision_path.read_text(encoding="utf-8"))

    assert decision["outcome"] in {"DEPLOYABLE", "DO_NOT_DEPLOY"}
    assert decision["outcome"] == result["outcome"]
    assert "red_flag_self_audit" in decision
    assert any(
        item["triggered"] == "YES" and item["blocks_deployability"] == "YES"
        for item in decision["red_flag_self_audit"].values()
    )
    assert decision["outcome"] == "DO_NOT_DEPLOY"

    recommendation = (tmp_path / "reports" / "pi_stress_final_go_no_go_recommendation.md").read_text(
        encoding="utf-8"
    )
    forbidden = [
        "conditional production review",
        "shadow",
        "parallel run",
        "deploy with caveats",
    ]
    lowered = recommendation.lower()
    assert all(term not in lowered for term in forbidden)
    assert recommendation.rstrip().endswith("DO NOT DEPLOY")
