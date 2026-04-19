"""
Alignment test for the probability-dashboard frontend.
Verifies that status.json produced by the exporter matches index.html expectations.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.models import SignalResult, TargetAllocationState
from src.output.web_exporter import export_web_snapshot


def test_web_frontend_contract_alignment(tmp_path):
    """
    Audits index.html and status.json to ensure the real frontend path reads from the
    probability-dashboard payload instead of legacy execution semantics.
    """
    mock_result = SignalResult(
        date=date(2026, 3, 30),
        price=558.28,
        target_beta=0.80,
        probabilities={"LATE_CYCLE": 0.74, "MID_CYCLE": 0.20, "RECOVERY": 0.06},
        priors={"LATE_CYCLE": 0.50, "MID_CYCLE": 0.30, "RECOVERY": 0.20},
        entropy=0.001,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(0.198, 0.802, 0.0, 0.80),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="v12.0 test",
        metadata={
            "beta_ceiling": 1.20,
            "raw_target_beta": 0.85,
            "feature_values": {
                "hazard_score": 0.38,
                "stress_score": 0.33,
                "breadth_proxy": 0.41,
                "volatility_percentile": 0.77,
            },
        },
    )

    json_path = tmp_path / "status.json"
    export_web_snapshot(mock_result, output_path=json_path)

    html_path = Path("src/web/public/index.html")
    html_content = html_path.read_text(encoding="utf-8")

    required_frontend_markers = [
        "dashboard-shell",
        "stage-distribution",
        "urgency-panel",
        "action-band-panel",
        "evidence-panel",
        "boundary-warning",
        "expectation-list",
        "limits-list",
        "renderDashboard",
        "data.dashboard",
    ]

    for marker in required_frontend_markers:
        assert marker in html_content, f"Frontend misalignment: index.html missing '{marker}'"

    assert "params.get('branch')" in html_content
    assert "staging/" in html_content
    assert "Probability Dashboard" in html_content
    assert "auto-trading engine" in html_content

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    dashboard = data["dashboard"]
    assert dashboard["summary"]["current_stage"] == "LATE_CYCLE"
    assert dashboard["summary"]["secondary_stage"] in dashboard["stage_distribution"]
    assert "LATE_CYCLE" in dashboard["stage_distribution"]
    assert "transition_urgency" in dashboard
    assert "action_band" in dashboard
    assert "boundary_warning" in dashboard
    assert "evidence_panel" in dashboard
    assert "expectations" in dashboard
    assert "limits" in dashboard

    assert "最終執行目標" not in html_content
    assert "共振信號" not in html_content
    assert "QLD 技術權限狀態" not in html_content


if __name__ == "__main__":
    test_web_frontend_contract_alignment()
