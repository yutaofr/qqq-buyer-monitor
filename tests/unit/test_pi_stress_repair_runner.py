from __future__ import annotations

import json

import numpy as np
import pandas as pd

from experiments.pi_stress_governance_package import PiStressGovernancePackage
from experiments.pi_stress_repair_runner import PiStressRepairRunner
from src.engine.v11.stress.models.threshold_policy import DeploymentPolicySpec


def test_pi_stress_repair_runner_writes_registry_and_reports(tmp_path):
    dates = pd.bdate_range("2020-01-01", periods=260)
    drawdown = np.r_[np.linspace(0.0, -0.28, 70), np.linspace(-0.28, -0.02, 70), np.zeros(120)]
    frame = pd.DataFrame(
        {
            "date": dates,
            "close": 100.0 * (1.0 + drawdown + np.linspace(0.0, 0.2, len(dates))),
            "S_price": np.clip(-drawdown * 3.0, 0.0, 1.0),
            "S_market": np.clip(-drawdown * 2.4, 0.0, 1.0),
            "S_macro_anom": np.clip(-drawdown * 1.8, 0.0, 1.0),
            "S_persist": np.clip(pd.Series(-drawdown).rolling(10, min_periods=1).mean() * 3.0, 0.0, 1.0),
            "legacy_pi_stress": np.clip(-drawdown * 4.0, 0.0, 1.0),
            "raw_target_beta": 1.0 - np.clip(-drawdown * 1.2, 0.0, 0.5),
            "expected_target_beta": np.where(drawdown < -0.12, 0.5, 1.0),
        }
    )

    runner = PiStressRepairRunner(output_dir=tmp_path / "artifacts", report_dir=tmp_path / "reports")
    result = runner.run_component_frame(frame, max_candidates=3)

    registry_path = tmp_path / "artifacts" / "experiment_registry.json"
    assert registry_path.exists()
    registry = json.loads(registry_path.read_text())
    assert len(registry["candidates"]) >= 3
    assert result["selected_candidate_id"] in {candidate["candidate_id"] for candidate in registry["candidates"]}
    assert "threshold_policy" in registry["candidates"][0]
    assert registry["candidates"][0]["threshold_policy"]["threshold_curve"]
    assert "separation" in registry["candidates"][0]["metrics"]
    assert (tmp_path / "reports" / "pi_stress_repair_baseline_report.md").exists()
    assert (tmp_path / "reports" / "pi_stress_repair_experiment_summary.md").exists()
    assert (tmp_path / "reports" / "pi_stress_repair_final_recommendation.md").exists()


def test_deployment_policy_spec_exposes_governed_modes_and_hysteresis():
    legacy = DeploymentPolicySpec.legacy_fixed_0_50()
    proposed = DeploymentPolicySpec.threshold_policy_with_hysteresis()

    assert legacy.mode == "legacy_fixed_0_50"
    assert legacy.primary_threshold == 0.50
    assert proposed.mode == "threshold_policy_with_hysteresis"
    assert proposed.primary_threshold == 0.25
    assert proposed.conservative_threshold == 0.35
    assert proposed.hysteresis["enter_after_days"] >= 2
    assert "posterior_drift" in proposed.monitoring_hooks
    assert "legacy_fixed_0_50" in DeploymentPolicySpec.supported_modes()


def test_governance_package_writes_layered_decision_reports(tmp_path):
    registry = {
        "selected_candidate_id": "C9_structural_confirmation_isotonic",
        "baseline": {
            "candidate_id": "baseline_legacy",
            "metrics": {
                "all": {
                    "brier": 0.0971,
                    "ece": 0.0870,
                    "crisis_recall_at_0_50": 0.5338,
                    "false_positive_average": 0.1576,
                },
                "oos": {
                    "false_positive_average": 0.1536,
                    "crisis_recall_at_0_50": 0.5429,
                },
                "separation": {
                    "rank_auc": 0.90,
                    "mean_gap": 0.35,
                },
                "windows": {
                    "false_positive_2023_jul_oct": {
                        "average_pi_stress": 0.3205,
                        "fraction_above_0_50": 0.1529,
                    },
                    "prolonged_stress_2022_h1": {
                        "average_pi_stress": 0.5464,
                        "crisis_recall_at_0_50": 0.6813,
                    },
                    "systemic_crisis_2020_covid": {"crisis_recall_at_0_50": 0.0},
                    "ordinary_correction_2018_q1": {"average_pi_stress": 0.2},
                    "recovery_2020_q2_q3": {"average_pi_stress": 0.3},
                },
            },
            "threshold_policy": {
                "threshold_curve": [
                    {
                        "threshold": 0.5,
                        "precision": 0.8,
                        "recall": 0.53,
                        "f1": 0.63,
                        "false_positive_rate": 0.05,
                        "predicted_positive_rate": 0.12,
                        "episode_capture_rate": 0.30,
                    }
                ]
            },
        },
        "candidates": [
            {
                "candidate_id": "C9_structural_confirmation_isotonic",
                "metrics": {
                    "all": {
                        "brier": 0.0709,
                        "ece": 0.0253,
                        "crisis_recall_at_0_50": 0.5907,
                        "false_positive_average": 0.1137,
                    },
                    "oos": {
                        "false_positive_average": 0.1263,
                        "crisis_recall_at_0_50": 0.5714,
                    },
                    "separation": {
                        "rank_auc": 0.9413,
                        "mean_gap": 0.6111,
                    },
                    "windows": {
                        "false_positive_2023_jul_oct": {
                            "average_pi_stress": 0.1369,
                            "fraction_above_0_50": 0.0,
                        },
                        "prolonged_stress_2022_h1": {
                            "average_pi_stress": 0.6071,
                            "crisis_recall_at_0_50": 0.4396,
                        },
                        "systemic_crisis_2020_covid": {"crisis_recall_at_0_50": 0.5366},
                        "ordinary_correction_2018_q1": {"average_pi_stress": 0.19},
                        "recovery_2020_q2_q3": {"average_pi_stress": 0.24},
                    },
                },
                "threshold_policy": {
                    "threshold_curve": [
                        {
                            "threshold": 0.25,
                            "precision": 0.66,
                            "recall": 0.86,
                            "f1": 0.75,
                            "false_positive_rate": 0.13,
                            "predicted_positive_rate": 0.30,
                            "episode_capture_rate": 0.81,
                        },
                        {
                            "threshold": 0.35,
                            "precision": 0.68,
                            "recall": 0.83,
                            "f1": 0.75,
                            "false_positive_rate": 0.11,
                            "predicted_positive_rate": 0.28,
                            "episode_capture_rate": 0.75,
                        },
                        {
                            "threshold": 0.5,
                            "precision": 0.97,
                            "recall": 0.59,
                            "f1": 0.73,
                            "false_positive_rate": 0.006,
                            "predicted_positive_rate": 0.14,
                            "episode_capture_rate": 0.29,
                        },
                    ]
                },
            }
        ],
    }
    registry_path = tmp_path / "experiment_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    package = PiStressGovernancePackage(
        registry_path=registry_path,
        output_dir=tmp_path / "artifacts",
        report_dir=tmp_path / "reports",
    )
    outputs = package.write()

    final_text = (tmp_path / "reports" / "pi_stress_repair_final_recommendation.md").read_text()
    assert "Acceptance status: `PASS`" not in final_text
    assert "Posterior Model Acceptance: `PASS`" in final_text
    assert "Legacy Fixed-Threshold Policy Acceptance: `FAIL`" in final_text
    assert "Production Merge Recommendation: `CONDITIONAL PRODUCTION REVIEW`" in final_text
    assert "2022 H1" in final_text

    policy = json.loads((tmp_path / "artifacts" / "policy_matrix.json").read_text())
    assert policy["recommended_policy"]["mode"] == "threshold_policy_with_hysteresis"
    assert policy["decision_taxonomy"]["legacy_fixed_threshold_policy_acceptance"] == "FAIL"
    assert outputs["decision_taxonomy"]["deployment_policy_acceptance"] == "CONDITIONAL PASS"

    for report_name in [
        "pi_stress_governance_decision_matrix.md",
        "pi_stress_calibration_appendix.md",
        "pi_stress_deployment_policy.md",
        "pi_stress_rollout_monitoring_plan.md",
    ]:
        text = (tmp_path / "reports" / report_name).read_text()
        assert "legacy 0.50" in text or "Legacy 0.50" in text
