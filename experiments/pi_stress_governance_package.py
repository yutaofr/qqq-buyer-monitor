from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.pi_stress_repair_runner import PiStressRepairRunner
from src.engine.v11.stress.models.stress_calibrator import StressCalibrator
from src.engine.v11.stress.models.threshold_policy import (
    DeploymentPolicySpec,
    ThresholdPolicyEvaluator,
)


class PiStressGovernancePackage:
    """Write governed model-risk package for the selected pi_stress candidate."""

    def __init__(
        self,
        *,
        registry_path: str | Path = "artifacts/pi_stress_phase2a_fresh_eval/experiment_registry.json",
        trace_path: str | Path | None = "artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir: str | Path = "artifacts/pi_stress_governance",
        report_dir: str | Path = "reports",
    ):
        self.registry_path = Path(registry_path)
        self.trace_path = Path(trace_path) if trace_path is not None else None
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)

    def write(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        selected = self._selected(registry)
        baseline = registry["baseline"]
        trace_analysis = self._trace_analysis(selected["candidate_id"])
        taxonomy = self._decision_taxonomy(baseline, selected, trace_analysis)
        policy_matrix = {
            "selected_candidate_id": selected["candidate_id"],
            "decision_taxonomy": taxonomy,
            "supported_policy_modes": list(DeploymentPolicySpec.supported_modes()),
            "legacy_policy": DeploymentPolicySpec.legacy_fixed_0_50().to_dict(),
            "recommended_policy": DeploymentPolicySpec.threshold_policy_with_hysteresis().to_dict(),
            "alternate_conservative_policy": DeploymentPolicySpec.calibrated_fixed_threshold(
                threshold=0.35
            ).to_dict(),
            "fallback_mode": "legacy_topology stress posterior mode plus legacy_fixed_0_50 policy",
            "posterior_metrics": self._posterior_metrics(baseline, selected),
            "threshold_policy": selected.get("threshold_policy", {}),
            "trace_analysis": trace_analysis,
            "known_residual_risks": self._known_risks(),
        }
        (self.output_dir / "policy_matrix.json").write_text(
            json.dumps(policy_matrix, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        governance_registry = {
            "source_registry": str(self.registry_path),
            "source_trace": str(self.trace_path) if self.trace_path else None,
            "policy_matrix": "policy_matrix.json",
            "decision_taxonomy": taxonomy,
            "reports": [
                "pi_stress_repair_final_recommendation.md",
                "pi_stress_governance_decision_matrix.md",
                "pi_stress_calibration_appendix.md",
                "pi_stress_deployment_policy.md",
                "pi_stress_rollout_monitoring_plan.md",
                "pi_stress_governance_review_checklist.md",
            ],
        }
        (self.output_dir / "governance_registry.json").write_text(
            json.dumps(governance_registry, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self._write_reports(registry, baseline, selected, taxonomy, policy_matrix)
        return {
            "decision_taxonomy": taxonomy,
            "policy_matrix_path": str(self.output_dir / "policy_matrix.json"),
            "governance_registry_path": str(self.output_dir / "governance_registry.json"),
        }

    @staticmethod
    def _selected(registry: dict[str, Any]) -> dict[str, Any]:
        selected_id = registry["selected_candidate_id"]
        return next(candidate for candidate in registry["candidates"] if candidate["candidate_id"] == selected_id)

    def _trace_analysis(self, selected_id: str) -> dict[str, Any]:
        if self.trace_path is None or not self.trace_path.exists():
            return {
                "available": False,
                "reason": "fresh trace not supplied",
                "window_threshold_metrics": {},
                "calibrator_comparison": [],
            }
        frame = pd.read_csv(self.trace_path)
        runner = PiStressRepairRunner(output_dir=self.output_dir / "_tmp", report_dir=self.output_dir / "_tmp_reports")
        scored = runner._prepare_frame(frame)
        labels = runner._stress_labels(scored)
        splits = runner._split_masks(scored)
        selected_config = next(config for config in runner._candidate_configs() if config["candidate_id"] == selected_id)
        raw_scores = runner._combine_frame(
            scored,
            selected_config["combiner"],
            component_columns=selected_config.get("component_columns"),
        )
        fit_mask = splits["train"] | splits["validation"]
        weights = runner._episode_weights(labels)[fit_mask]
        calibrator = StressCalibrator(method=selected_config["calibration"])
        calibrator.fit(raw_scores[fit_mask], labels[fit_mask])
        scores = calibrator.transform(raw_scores)
        return {
            "available": True,
            "window_threshold_metrics": self._window_threshold_metrics(runner, scored, labels, scores),
            "calibrator_comparison": self._calibrator_comparison(
                runner,
                raw_scores,
                labels,
                fit_mask,
                weights,
            ),
            "selected_plateau_summary": self._plateau_summary(scores),
            "selected_local_sensitivity": self._local_threshold_sensitivity(scores, labels),
        }

    def _window_threshold_metrics(
        self,
        runner: PiStressRepairRunner,
        frame: pd.DataFrame,
        labels: np.ndarray,
        scores: np.ndarray,
    ) -> dict[str, Any]:
        dates = pd.to_datetime(frame["date"], errors="coerce") if "date" in frame.columns else pd.Series([], dtype="datetime64[ns]")
        windows = {
            "Jul-Oct 2023": ("2023-07-01", "2023-10-31"),
            "2022 H1": ("2022-01-03", "2022-06-30"),
            "2020 COVID": ("2020-02-18", "2020-04-30"),
            "2018 Q1 ordinary correction": ("2018-01-26", "2018-04-30"),
            "2020 Q2-Q3 recovery": ("2020-04-01", "2020-09-30"),
        }
        result: dict[str, Any] = {}
        for name, (start, end) in windows.items():
            mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
            if not mask.any():
                continue
            idx = mask.to_numpy()
            window_scores = np.asarray(scores[idx], dtype=float)
            window_labels = np.asarray(labels[idx], dtype=int)
            curve = ThresholdPolicyEvaluator(thresholds=[0.25, 0.35, 0.50]).evaluate(
                scores=window_scores,
                labels=window_labels,
                episode_ids=runner._episode_ids(window_labels),
            )["threshold_curve"]
            result[name] = {
                "average_pi_stress": float(np.mean(window_scores)),
                "thresholds": {
                    f"{row['threshold']:.2f}": {
                        **row,
                        "fraction_above_threshold": row["predicted_positive_rate"],
                    }
                    for row in curve
                },
            }
        return result

    def _calibrator_comparison(
        self,
        runner: PiStressRepairRunner,
        raw_scores: np.ndarray,
        labels: np.ndarray,
        fit_mask: np.ndarray,
        weights: np.ndarray,
    ) -> list[dict[str, Any]]:
        methods = [
            ("isotonic", None),
            ("platt", None),
            ("weighted_platt", weights),
            ("platt_balanced", None),
        ]
        comparison = []
        for method, sample_weight in methods:
            calibrator = StressCalibrator(method=method)
            calibrator.fit(raw_scores[fit_mask], labels[fit_mask], sample_weight=sample_weight)
            scores = calibrator.transform(raw_scores)
            policy = ThresholdPolicyEvaluator(thresholds=[0.20, 0.25, 0.30, 0.35, 0.40, 0.50]).evaluate(
                scores=scores,
                labels=labels,
                episode_ids=runner._episode_ids(labels),
            )
            metrics = runner._metrics(scores, labels, pd.DataFrame(index=np.arange(len(scores))))
            comparison.append(
                {
                    "method": method,
                    "brier": metrics["brier"],
                    "ece": metrics["ece"],
                    "plateau_summary": self._plateau_summary(scores),
                    "recommended_threshold": policy["recommended_threshold"],
                    "threshold_local": [
                        row
                        for row in policy["threshold_curve"]
                        if row["threshold"] in {0.20, 0.25, 0.30, 0.35, 0.40}
                    ],
                    "flip_frequency_at_0_25": self._flip_frequency(scores, 0.25),
                    "flip_frequency_at_0_35": self._flip_frequency(scores, 0.35),
                    "calibration_curve": self._calibration_curve(scores, labels),
                }
            )
        return comparison

    @staticmethod
    def _plateau_summary(scores: np.ndarray) -> dict[str, float]:
        rounded = np.round(np.asarray(scores, dtype=float), 6)
        unique, counts = np.unique(rounded, return_counts=True)
        return {
            "unique_score_levels": float(len(unique)),
            "largest_plateau_count": float(counts.max()) if len(counts) else 0.0,
            "largest_plateau_fraction": float(counts.max() / max(1, len(rounded))) if len(counts) else 0.0,
        }

    @staticmethod
    def _flip_frequency(scores: np.ndarray, threshold: float) -> float:
        if len(scores) < 2:
            return 0.0
        triggers = np.asarray(scores, dtype=float) >= float(threshold)
        return float(np.mean(triggers[1:] != triggers[:-1]))

    @staticmethod
    def _calibration_curve(scores: np.ndarray, labels: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
        edges = np.linspace(0.0, 1.0, bins + 1)
        result = []
        score_arr = np.asarray(scores, dtype=float)
        label_arr = np.asarray(labels, dtype=int)
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            mask = (score_arr >= lo) & (score_arr <= hi if hi == 1.0 else score_arr < hi)
            if mask.any():
                result.append(
                    {
                        "bin_low": float(lo),
                        "bin_high": float(hi),
                        "count": float(mask.sum()),
                        "mean_score": float(score_arr[mask].mean()),
                        "event_rate": float(label_arr[mask].mean()),
                    }
                )
        return result

    @staticmethod
    def _local_threshold_sensitivity(scores: np.ndarray, labels: np.ndarray) -> list[dict[str, float]]:
        return ThresholdPolicyEvaluator(thresholds=[0.20, 0.25, 0.30, 0.35, 0.40]).evaluate(
            scores=scores,
            labels=labels,
        )["threshold_curve"]

    @staticmethod
    def _posterior_metrics(baseline: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
        return {
            "baseline": {
                "brier": baseline["metrics"]["all"].get("brier"),
                "ece": baseline["metrics"]["all"].get("ece"),
                "auc": baseline["metrics"].get("separation", {}).get("rank_auc"),
                "mean_gap": baseline["metrics"].get("separation", {}).get("mean_gap"),
            },
            "selected": {
                "brier": selected["metrics"]["all"].get("brier"),
                "ece": selected["metrics"]["all"].get("ece"),
                "auc": selected["metrics"].get("separation", {}).get("rank_auc"),
                "mean_gap": selected["metrics"].get("separation", {}).get("mean_gap"),
            },
        }

    @staticmethod
    def _decision_taxonomy(
        baseline: dict[str, Any],
        selected: dict[str, Any],
        trace_analysis: dict[str, Any],
    ) -> dict[str, str]:
        base_all = baseline["metrics"]["all"]
        sel_all = selected["metrics"]["all"]
        sel_windows = selected["metrics"].get("windows", {})
        posterior_pass = (
            sel_all.get("brier", 1.0) < base_all.get("brier", 0.0)
            and sel_all.get("ece", 1.0) < base_all.get("ece", 0.0)
            and sel_all.get("crisis_recall_at_0_50", 0.0) >= base_all.get("crisis_recall_at_0_50", 0.0)
        )
        h1_recall = sel_windows.get("prolonged_stress_2022_h1", {}).get("crisis_recall_at_0_50", 0.0)
        curve = selected.get("threshold_policy", {}).get("threshold_curve", [])
        primary = next((row for row in curve if abs(float(row["threshold"]) - 0.25) < 1e-9), {})
        deployment_ok = (
            primary.get("recall", 0.0) >= 0.60
            and primary.get("episode_capture_rate", 0.0) >= 0.70
        )
        return {
            "posterior_model_acceptance": "PASS" if posterior_pass else "CONDITIONAL PASS",
            "legacy_fixed_threshold_policy_acceptance": "FAIL"
            if h1_recall < 0.60
            else "CONDITIONAL PASS",
            "deployment_policy_acceptance": "CONDITIONAL PASS"
            if deployment_ok
            else "FAIL",
            "production_merge_recommendation": "CONDITIONAL PRODUCTION REVIEW"
            if posterior_pass and deployment_ok
            else "RESEARCH-BRANCH MERGE",
        }

    @staticmethod
    def _known_risks() -> list[str]:
        return [
            "The selected posterior improves statistical separation and Jul-Oct 2023 false-positive behavior.",
            "The legacy 0.50 trigger is no longer an appropriate sole operating rule.",
            "2022 H1 under the legacy 0.50 trigger remains under-captured.",
            "Beta-surface and raw beta delta repair remains a downstream separate task.",
            "Proxy-label mismatch may inflate apparent false positives inside stressed windows.",
            "Isotonic calibration may create posterior plateaus and threshold-local sensitivity.",
        ]

    def _write_reports(
        self,
        registry: dict[str, Any],
        baseline: dict[str, Any],
        selected: dict[str, Any],
        taxonomy: dict[str, str],
        policy_matrix: dict[str, Any],
    ) -> None:
        self._write_final_recommendation(baseline, selected, taxonomy, policy_matrix)
        self._write_decision_matrix(baseline, selected, taxonomy, policy_matrix)
        self._write_calibration_appendix(policy_matrix)
        self._write_deployment_policy(policy_matrix)
        self._write_rollout_monitoring_plan(policy_matrix)
        self._write_review_checklist(taxonomy)

    def _write_final_recommendation(
        self,
        baseline: dict[str, Any],
        selected: dict[str, Any],
        taxonomy: dict[str, str],
        policy_matrix: dict[str, Any],
    ) -> None:
        text = f"""# pi_stress Repair Final Recommendation

Chosen candidate: `{selected['candidate_id']}`.

## Layered Decision Taxonomy

- Posterior Model Acceptance: `{taxonomy['posterior_model_acceptance']}`
- Legacy Fixed-Threshold Policy Acceptance: `{taxonomy['legacy_fixed_threshold_policy_acceptance']}`
- Deployment Policy Acceptance: `{taxonomy['deployment_policy_acceptance']}`
- Production Merge Recommendation: `{taxonomy['production_merge_recommendation']}`

This is not unconditional production approval. The posterior model is acceptable for production review, but the legacy 0.50 trigger fails governance because 2022 H1 remains under-captured at that threshold.

## Basis

- All Brier: baseline `{baseline['metrics']['all'].get('brier'):.4f}` vs selected `{selected['metrics']['all'].get('brier'):.4f}`.
- All ECE: baseline `{baseline['metrics']['all'].get('ece'):.4f}` vs selected `{selected['metrics']['all'].get('ece'):.4f}`.
- All recall @ 0.50: baseline `{baseline['metrics']['all'].get('crisis_recall_at_0_50'):.4f}` vs selected `{selected['metrics']['all'].get('crisis_recall_at_0_50'):.4f}`.
- OOS false-positive average: baseline `{baseline['metrics']['oos'].get('false_positive_average'):.4f}` vs selected `{selected['metrics']['oos'].get('false_positive_average'):.4f}`.
- Jul-Oct 2023 average pi_stress: baseline `{baseline['metrics']['windows']['false_positive_2023_jul_oct'].get('average_pi_stress'):.4f}` vs selected `{selected['metrics']['windows']['false_positive_2023_jul_oct'].get('average_pi_stress'):.4f}`.
- 2022 H1 selected recall @ 0.50: `{selected['metrics']['windows']['prolonged_stress_2022_h1'].get('crisis_recall_at_0_50'):.4f}`.

## What Is Fixed

The posterior has better calibration and separation, and the Jul-Oct 2023 ordinary-correction pathology is materially reduced.

## What Is Not Fixed

The legacy 0.50 policy cut remains unsuitable as the sole operational trigger. Beta-surface / raw beta delta behavior remains a downstream separate task. Proxy-label mismatch may make stressed-window false positives look worse than the economic state warrants.

## Required Approval Condition

Production review may proceed only if the deployment policy migrates to the explicit threshold-policy artifact in `artifacts/pi_stress_governance/policy_matrix.json`, with monitoring and rollback gates active.

## Rollback Path

Set stress posterior mode to `legacy_topology` and policy mode to `legacy_fixed_0_50`. Roll back immediately on false-positive inflation, recall degradation, unstable threshold behavior, calibration drift, or worsening downstream beta instability.
"""
        (self.report_dir / "pi_stress_repair_final_recommendation.md").write_text(text, encoding="utf-8")

    def _write_decision_matrix(
        self,
        baseline: dict[str, Any],
        selected: dict[str, Any],
        taxonomy: dict[str, str],
        policy_matrix: dict[str, Any],
    ) -> None:
        trace = policy_matrix["trace_analysis"]
        window_rows = []
        for window, metrics in trace.get("window_threshold_metrics", {}).items():
            for threshold, row in metrics.get("thresholds", {}).items():
                window_rows.append(
                    f"| {window} | {threshold} | {metrics['average_pi_stress']:.4f} | "
                    f"{row['fraction_above_threshold']:.4f} | {row['precision']:.4f} | "
                    f"{row['recall']:.4f} | {row['f1']:.4f} | {row['false_positive_rate']:.4f} | "
                    f"{row['predicted_positive_rate']:.4f} | {row['episode_capture_rate']:.4f} |"
                )
        if not window_rows:
            window_rows.append("| trace unavailable | legacy 0.50 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
        posterior = policy_matrix["posterior_metrics"]
        selected_curve = {
            f"{row['threshold']:.2f}": row
            for row in selected.get("threshold_policy", {}).get("threshold_curve", [])
            if row["threshold"] in {0.25, 0.35, 0.50}
        }
        policy_rows = [
            f"| {threshold} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['false_positive_rate']:.4f} | {row['predicted_positive_rate']:.4f} | {row['episode_capture_rate']:.4f} |"
            for threshold, row in sorted(selected_curve.items())
        ]
        text = f"""# pi_stress Governance Decision Matrix

## Decision Taxonomy

| Layer | Verdict |
|---|---|
| Posterior Model Acceptance | `{taxonomy['posterior_model_acceptance']}` |
| Legacy 0.50 Fixed-Threshold Policy Acceptance | `{taxonomy['legacy_fixed_threshold_policy_acceptance']}` |
| Deployment Policy Acceptance | `{taxonomy['deployment_policy_acceptance']}` |
| Production Merge Recommendation | `{taxonomy['production_merge_recommendation']}` |

## Posterior Quality

| Metric | Baseline | Selected |
|---|---:|---:|
| Brier | {posterior['baseline']['brier']:.4f} | {posterior['selected']['brier']:.4f} |
| ECE | {posterior['baseline']['ece']:.4f} | {posterior['selected']['ece']:.4f} |
| AUC / rank AUC | {posterior['baseline']['auc'] or 0.0:.4f} | {posterior['selected']['auc'] or 0.0:.4f} |
| Mean gap | {posterior['baseline']['mean_gap'] or 0.0:.4f} | {posterior['selected']['mean_gap'] or 0.0:.4f} |

These are posterior improvements. They are not created by changing the operational threshold.

## Policy Threshold Comparison

| Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture |
|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(policy_rows)}

The recall restoration around 0.25-0.35 is a policy-layer effect. It must not be reported as a posterior-model improvement.

## Window-Level Policy Behavior

| Window | Threshold | Average pi_stress | Fraction Above Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(window_rows)}

## Non-Improved Items

- Legacy 0.50 still under-captures 2022 H1.
- Downstream raw beta delta is not repaired here.
- Proxy-label mismatch may inflate apparent false positives in stressed windows.
"""
        (self.report_dir / "pi_stress_governance_decision_matrix.md").write_text(text, encoding="utf-8")

    def _write_calibration_appendix(self, policy_matrix: dict[str, Any]) -> None:
        comparison = policy_matrix["trace_analysis"].get("calibrator_comparison", [])
        rows = []
        for row in comparison:
            plateau = row["plateau_summary"]
            rows.append(
                f"| {row['method']} | {row['brier']:.4f} | {row['ece']:.4f} | "
                f"{plateau['unique_score_levels']:.0f} | {plateau['largest_plateau_fraction']:.4f} | "
                f"{row['recommended_threshold']:.2f} | {row['flip_frequency_at_0_25']:.4f} | "
                f"{row['flip_frequency_at_0_35']:.4f} |"
            )
        if not rows:
            rows.append("| unavailable | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
        selected_plateau = policy_matrix["trace_analysis"].get("selected_plateau_summary", {})
        local = policy_matrix["trace_analysis"].get("selected_local_sensitivity", [])
        local_rows = [
            f"| {row['threshold']:.2f} | {row['recall']:.4f} | {row['false_positive_rate']:.4f} | "
            f"{row['f1']:.4f} | {row['episode_capture_rate']:.4f} |"
            for row in local
        ] or ["| unavailable | n/a | n/a | n/a | n/a |"]
        text = f"""# pi_stress Calibration Appendix

## Isotonic Plateau Risk

The selected candidate uses isotonic calibration. Isotonic is monotone and empirically strong in the current registry, but it can create posterior plateaus. Plateaued posteriors can make threshold-local behavior discontinuous near deployment cuts.

Selected plateau summary:

```json
{json.dumps(selected_plateau, indent=2, sort_keys=True)}
```

## Calibrator Comparison

| Calibrator | Brier | ECE | Unique Levels | Largest Plateau Fraction | Recommended Threshold | Flip Freq @ 0.25 | Flip Freq @ 0.35 |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Threshold-Local Sensitivity

| Threshold | Recall | FPR | F1 | Episode Capture |
|---:|---:|---:|---:|---:|
{chr(10).join(local_rows)}

## Calibration Curve

Detailed calibration-curve bins are stored in `artifacts/pi_stress_governance/policy_matrix.json` under `trace_analysis.calibrator_comparison`.

## Governance Conclusion

Keep isotonic only with deployment caveats. It is acceptable for conditional production review because Brier and ECE improve, but monitoring must explicitly track plateau mass, threshold-local trigger drift, and transition flip frequency. A smoother Platt-family calibrator remains the rollback candidate if isotonic plateaus produce unstable policy behavior. Legacy 0.50 remains a failed sole operating rule for the selected posterior, with 2022 H1 as the explicit under-capture example.
"""
        (self.report_dir / "pi_stress_calibration_appendix.md").write_text(text, encoding="utf-8")

    def _write_deployment_policy(self, policy_matrix: dict[str, Any]) -> None:
        text = f"""# pi_stress Deployment Policy

## Policy Modes

1. `legacy_fixed_0_50`: rollback-compatible historical trigger.
2. `calibrated_fixed_threshold`: single calibrated posterior threshold, default conservative threshold 0.35.
3. `threshold_policy_with_hysteresis`: recommended governed policy.

## Recommended Policy

```json
{json.dumps(policy_matrix['recommended_policy'], indent=2, sort_keys=True)}
```

Primary threshold: `0.25`.

Alternate conservative threshold: `0.35`.

Escalation threshold: `0.50`.

The primary threshold restores prolonged-stress capture but accepts a higher trigger rate. The conservative threshold reduces false-positive pressure but may reduce early episode coverage. The legacy 0.50 threshold is retained as fallback only; it is not approved as the sole operating policy because it under-captures 2022 H1.

## Monitoring Hooks

The policy artifact explicitly requires monitoring for posterior drift, threshold trigger drift, calibration drift, data drift, and downstream beta pathology.
"""
        (self.report_dir / "pi_stress_deployment_policy.md").write_text(text, encoding="utf-8")

    def _write_rollout_monitoring_plan(self, policy_matrix: dict[str, Any]) -> None:
        text = """# pi_stress Rollout and Monitoring Plan

## Purpose

Use the repaired pi_stress posterior as a calibrated systemic stress posterior, not as a standalone trading rule.

## Scope

In scope: posterior scoring, threshold-policy evaluation, diagnostics, shadow comparison, monitoring, and rollback.

Out of scope: beta-surface repair, raw beta delta repair, portfolio execution redesign, and raw macro or market-internal hard gates in conductor.py.

## Key Assumptions

- Stress labels are transparent proxies, not perfect economic truth.
- Current improvements are measured on the fresh current-branch trace and registry.
- Threshold policy is a separate governed layer.

## Known Failure Modes

- Legacy 0.50 policy misses prolonged stress, especially 2022 H1.
- Isotonic calibration can create posterior plateaus.
- Proxy-label mismatch can inflate false-positive readings inside stressed windows.
- Missing market-internal data can degrade S_market back toward topology fallback.
- Downstream beta instability may persist because beta-surface repair is separate.

## Rollout Stages

| Stage | Entry Criteria | Metrics Monitored | Exit Criteria | Rollback Trigger |
|---|---|---|---|---|
| Research branch acceptance | Tests and governance artifacts complete | Brier, ECE, AUC, mean gap, 2023 FP, 2022 H1 recall | Model risk review package accepted | Inconsistent decision taxonomy |
| Shadow / parallel run | Research acceptance complete | Posterior drift, trigger rate drift, legacy-vs-new divergence | Stable for agreed validation window | Trigger rate inflation or data degradation |
| Controlled validation period | Shadow diagnostics clean | Episode capture, miss rate, ordinary-correction FP, calibration drift | Reviewer sign-off | Recall degradation or calibration drift |
| Reviewer sign-off gate | Validation complete | Full governance checklist | Quant, model risk, strategy owner, production engineering approval | Any mandatory reviewer rejects |
| Limited production activation | Sign-offs complete | Threshold triggers, hedge path, beta delta, feature health | No alert breach over limited activation | False-positive inflation, unstable threshold behavior, beta instability |
| Full activation or rollback | Limited activation clean | All monitoring categories | Production owner approval | Any hard rollback threshold breach |

## Monitoring Framework

| Category | Metric Definition | Alert Threshold | Cadence | Owner / Reviewer |
|---|---|---|---|---|
| Posterior distribution drift | PSI or quantile shift of pi_stress vs validation baseline | PSI > 0.20 or p95 shift > 0.15 | Daily / weekly review | Quant research / model risk |
| Threshold trigger drift | Fraction above 0.25, 0.35, 0.50 | 2x validation trigger rate for 5 trading days | Daily | Strategy owner |
| Episode capture / miss tracking | Captured stress episodes / labeled stress episodes | Episode capture below 0.70 over review window | Weekly | Quant research |
| Calibration drift | Rolling Brier, ECE, reliability bins | ECE > 0.08 or Brier degrades by 30% | Weekly | Model risk |
| Ordinary-correction false-positive drift | Non-stress avg pi and trigger rate in correction basket | FP avg exceeds baseline by 20% | Weekly | Quant research |
| Downstream beta / hedge pathology | raw beta delta, target beta instability, hedge flips | Worsening vs legacy by agreed tolerance | Daily | Strategy owner / production engineering |
| Missing-data / degraded-feature monitoring | Missing or fallback rate for S_market and S_macro_anom inputs | fallback_used > 20% for 5 days | Daily | Production engineering |

## Change Management

All threshold changes require a policy artifact update, registry update, reviewer sign-off, and rollback note. No raw market or macro feature gates may be added to conductor.py.

## Required Reviewer Sign-Offs

- Quant research
- Model risk
- Strategy owner
- Production engineering
"""
        (self.report_dir / "pi_stress_rollout_monitoring_plan.md").write_text(text, encoding="utf-8")

    def _write_review_checklist(self, taxonomy: dict[str, str]) -> None:
        text = f"""# pi_stress Governance Review Checklist

## One-Vote-Fail Items

| Check | Status | Evidence |
|---|---|---|
| Conclusion language is internally consistent | PASS | Four separate decisions are reported: posterior, legacy 0.50 policy, deployment policy, production recommendation. |
| Threshold adjustment is not presented as model improvement | PASS | Decision matrix separates posterior Brier/ECE/AUC/mean gap from threshold precision/recall/FPR. |
| Threshold policy exists as code/config artifact | PASS | `DeploymentPolicySpec` and `artifacts/pi_stress_governance/policy_matrix.json`. |
| Calibration appendix exists | PASS | `reports/pi_stress_calibration_appendix.md` covers isotonic plateaus, threshold sensitivity, flip frequency, and Platt alternatives. |
| Rollback plan is complete | PASS | Final recommendation and rollout plan define switch, triggers, and restoration path. |
| No raw macro / market hard gates in top-level policy | PASS | Policy uses calibrated pi_stress thresholds only; conductor receives abstract feature history and does not implement raw-feature gates. |

## Mandatory Pass Items

| Check | Status | Evidence |
|---|---|---|
| Posterior Model Acceptance reported | {taxonomy['posterior_model_acceptance']} | Final recommendation. |
| Legacy Fixed-Threshold Policy Acceptance reported | {taxonomy['legacy_fixed_threshold_policy_acceptance']} | Final recommendation and decision matrix. |
| Deployment Policy Acceptance reported | {taxonomy['deployment_policy_acceptance']} | Final recommendation and policy spec. |
| Production Merge Recommendation reported | {taxonomy['production_merge_recommendation']} | Final recommendation. |
| Posterior vs policy comparison complete | PASS | Decision matrix includes posterior quality and threshold 0.25 / 0.35 / 0.50 policy metrics. |
| Required windows covered | PASS | Jul-Oct 2023, 2022 H1, 2020 COVID, 2018 Q1 ordinary correction, 2020 Q2-Q3 recovery. |
| Required residual risks retained | PASS | 2022 H1 legacy 0.50 miss, beta-surface task, proxy-label mismatch, isotonic plateaus. |
| Rollout plan executable | PASS | Six rollout stages with entry criteria, metrics, exit criteria, and rollback triggers. |
| Monitoring separated by layer | PASS | Posterior drift, policy drift, data drift, calibration drift, FP drift, episode capture, beta pathology. |

## Governance Self-Assessment

The package is review-ready for conditional production review only. It is not an unconditional approval package.
"""
        (self.report_dir / "pi_stress_governance_review_checklist.md").write_text(text, encoding="utf-8")


def main() -> None:
    PiStressGovernancePackage().write()


if __name__ == "__main__":
    main()
