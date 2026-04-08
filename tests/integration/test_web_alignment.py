"""
Ultimate Alignment Test for V12.0 Web Frontend.
Verifies that status.json produced by engine matches index.html expectations.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.models import SignalResult, TargetAllocationState
from src.output.web_exporter import export_web_snapshot


def test_web_frontend_contract_alignment():
    """
    Surgically audits index.html JS to ensure it matches the keys in web_exporter.
    """
    # 1. Generate a sample snapshot
    mock_result = SignalResult(
        date=date(2026, 3, 30),
        price=558.28,
        target_beta=0.80,
        probabilities={"LATE_CYCLE": 0.9998, "MID_CYCLE": 0.0001},
        priors={"LATE_CYCLE": 0.80, "MID_CYCLE": 0.20},
        entropy=0.001,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(0.198, 0.802, 0.0, 0.80),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="v12.0 test",
        metadata={"beta_ceiling": 1.20, "raw_target_beta": 0.85},
    )

    json_path = Path("src/web/public/status.json")
    export_web_snapshot(mock_result, output_path=json_path)

    # 2. Load the generated JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # 3. Load the index.html and audit JS logic
    html_path = Path("src/web/public/index.html")
    html_content = html_path.read_text(encoding="utf-8")

    # Verified Keys in V12.0 status.json
    required_json_keys = [
        "data.signal.entropy",
        "data.signal.probabilities",
        "data.signal.priors",
        "data.signal.target_beta",
        "data.signal.protected_beta",
        "data.signal.overlay_beta",
        "data.signal.overlay_mode",
        "data.signal.beta_overlay_multiplier",
        "data.signal.deployment_overlay_multiplier",
        "data.signal.beta_ceiling",
        "data.signal.raw_target_beta",
        "data.signal.raw_target_beta_pre_floor",
        "data.signal.is_floor_active",
        "data.signal.hydration_anchor",
        "data.signal.resonance",
        "data.signal.price_topology",
        "data.signal.lock_active",
        "data.meta.calculated_at_utc",
        "data.evidence.logic_trace",
        "data.evidence.feature_values",
        "data.evidence.execution_overlay",
        "data.evidence.bayesian_diagnostics",
        "data.evidence.price_topology",
    ]

    print("\n--- Frontend Alignment Audit ---")
    for key in required_json_keys:
        # Check if the JS code in index.html references this specific data path
        # Using a simple string search since it's a static template
        assert key in html_content, (
            f"Frontend misalignment: index.html is missing reference to '{key}'"
        )
        print(f"Key Found: {key} -> ALIGNED")

    # 4. Check specific V11 fields
    assert data["signal"]["entropy"] == 0.001
    assert "LATE_CYCLE" in data["signal"]["probabilities"]
    assert "LATE_CYCLE" in data["signal"]["priors"]
    assert data["signal"]["lock_active"] is False
    assert "logic-trace-container" in html_content
    assert "feature-values-container" in html_content

    print("\nWeb Alignment: SUCCESS. V12.0 Engine and Frontend are in sync.")


if __name__ == "__main__":
    test_web_frontend_contract_alignment()
