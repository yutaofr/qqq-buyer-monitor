from __future__ import annotations

import json
from pathlib import Path

import pytest

# Since the script is not yet implemented, we mock its existence/output for TDD
REPORT_PATH = Path("artifacts/v13_8_acceptance/calibration_report.json")


def test_calibration_report_schema_compliance():
    """Verify that the generated calibration report contains all mandatory fields."""
    # This test will fail until the script is run and generates the file
    if not REPORT_PATH.exists():
        pytest.fail(
            f"Calibration report missing at {REPORT_PATH}. Run scripts/run_v13_8_calibration_report.py first."
        )

    with open(REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)

    required_fields = [
        "code_revision",
        "evaluation_start",
        "evaluation_end",
        "price_cache_path",
        "parameter_values_hash",
        "holdout_window",
        "summary_metrics",
        "reliability_required",
        "environment",
    ]

    for field in required_fields:
        assert field in report, f"Mandatory field '{field}' missing from calibration report."

    # Validate nested metrics
    metrics = report["summary_metrics"]
    assert "top1_accuracy" in metrics
    assert "mean_entropy" in metrics
    assert "mean_brier" in metrics

    # Validate environment info
    assert "python_version" in report["environment"]
    assert "platform" in report["environment"]
