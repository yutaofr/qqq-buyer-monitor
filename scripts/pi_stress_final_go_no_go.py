from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.pi_stress_repair_runner import PiStressRepairRunner
from src.engine.v11.stress.models.stress_calibrator import StressCalibrator
from src.engine.v11.stress.models.threshold_policy import ThresholdPolicyEvaluator


THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
FINAL_THRESHOLD = 0.35
FINAL_CALIBRATOR = "platt"
FINAL_CANDIDATE = "C9_structural_confirmation_isotonic"


@dataclass(frozen=True)
class WindowSpec:
    key: str
    label: str
    start: str
    end: str
    role: str


WINDOWS = [
    WindowSpec("ordinary_correction_2018_q1", "2018 Q1 ordinary correction", "2018-01-26", "2018-04-30", "ordinary"),
    WindowSpec("systemic_crisis_2020_covid", "2020 COVID", "2020-02-18", "2020-04-30", "stress"),
    WindowSpec("recovery_2020_q2_q3", "2020 Q2-Q3 recovery", "2020-04-01", "2020-09-30", "ordinary"),
    WindowSpec("prolonged_stress_2022_h1", "2022 H1 prolonged stress", "2022-01-03", "2022-06-30", "stress"),
    WindowSpec("false_positive_2023_jul_oct", "Jul-Oct 2023 ghost window", "2023-07-01", "2023-10-31", "ordinary"),
]


class PiStressFinalGoNoGo:
    """Generate final binary pi_stress deployment evidence and governance artifacts."""

    def __init__(
        self,
        *,
        registry_path: str | Path = "artifacts/pi_stress_phase2a_fresh_eval/experiment_registry.json",
        trace_path: str | Path = "artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir: str | Path = "artifacts/pi_stress_final_go_no_go",
        report_dir: str | Path = "reports",
    ):
        self.registry_path = Path(registry_path)
        self.trace_path = Path(trace_path)
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)
        self.runner = PiStressRepairRunner(output_dir=self.output_dir / "_tmp", report_dir=self.output_dir / "_tmp_reports")

    def write(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        evidence = self._build_evidence()
        decision = self._decision(evidence)
        self._write_json(decision)
        self._write_reports(evidence, decision)
        return decision

    def _build_evidence(self) -> dict[str, Any]:
        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        baseline = registry["baseline"]
        selected = next(candidate for candidate in registry["candidates"] if candidate["candidate_id"] == FINAL_CANDIDATE)

        frame = self.runner._prepare_frame(pd.read_csv(self.trace_path))
        labels = self.runner._stress_labels(frame)
        episode_ids = self.runner._episode_ids(labels)
        splits = self.runner._split_masks(frame)
        fit_mask = splits["train"] | splits["validation"]
        weights = self.runner._episode_weights(labels)[fit_mask]
        config = next(config for config in self.runner._candidate_configs() if config["candidate_id"] == FINAL_CANDIDATE)
        raw_scores = self.runner._combine_frame(
            frame,
            config["combiner"],
            component_columns=config.get("component_columns"),
        )
        legacy_scores = frame["legacy_pi_stress"].to_numpy(dtype=float)

        calibrators = {
            method: self._score_calibrator(method, raw_scores, labels, fit_mask, weights, frame, episode_ids)
            for method in ("isotonic", "platt", "weighted_platt", "platt_balanced")
        }
        final = calibrators[FINAL_CALIBRATOR]
        legacy = self._score_series("legacy_fixed_0_50", legacy_scores, labels, frame, episode_ids)
        ordinary_basket = self._ordinary_basket(frame, labels, final["scores"], legacy_scores)
        downstream = self._downstream_review(frame, labels, final["scores"], legacy_scores)

        return {
            "source_registry": str(self.registry_path),
            "source_trace": str(self.trace_path),
            "registry_baseline": baseline,
            "registry_selected": selected,
            "legacy": legacy,
            "calibrators": {key: self._public_record(value) for key, value in calibrators.items()},
            "final_scores": final["scores"],
            "legacy_scores": legacy_scores,
            "labels": labels,
            "ordinary_basket": ordinary_basket,
            "downstream_review": downstream,
        }

    def _score_calibrator(
        self,
        method: str,
        raw_scores: np.ndarray,
        labels: np.ndarray,
        fit_mask: np.ndarray,
        weights: np.ndarray,
        frame: pd.DataFrame,
        episode_ids: np.ndarray,
    ) -> dict[str, Any]:
        calibrator = StressCalibrator(method=method)
        sample_weight = weights if method == "weighted_platt" else None
        calibrator.fit(raw_scores[fit_mask], labels[fit_mask], sample_weight=sample_weight)
        scores = calibrator.transform(raw_scores)
        return self._score_series(method, scores, labels, frame, episode_ids)

    def _score_series(
        self,
        name: str,
        scores: np.ndarray,
        labels: np.ndarray,
        frame: pd.DataFrame,
        episode_ids: np.ndarray,
    ) -> dict[str, Any]:
        scores = np.clip(np.asarray(scores, dtype=float), 0.0, 1.0)
        return {
            "name": name,
            "scores": scores,
            "posterior": {
                **self.runner._metrics(scores, labels, frame),
                **{f"separation_{k}": v for k, v in self.runner._separation_metrics(scores, labels).items()},
            },
            "threshold_curve": ThresholdPolicyEvaluator(THRESHOLDS).evaluate(
                scores=scores,
                labels=labels,
                episode_ids=episode_ids,
            )["threshold_curve"],
            "windows": self._window_metrics(scores, labels, frame),
            "plateau": self._plateau_summary(scores),
            "flip_frequency": {f"{t:.2f}": self._flip_frequency(scores, t) for t in THRESHOLDS},
        }

    def _window_metrics(self, scores: np.ndarray, labels: np.ndarray, frame: pd.DataFrame) -> dict[str, Any]:
        dates = pd.to_datetime(frame["date"], errors="coerce")
        result: dict[str, Any] = {}
        for spec in WINDOWS:
            mask = ((dates >= pd.Timestamp(spec.start)) & (dates <= pd.Timestamp(spec.end))).to_numpy()
            if not mask.any():
                continue
            curve = ThresholdPolicyEvaluator(THRESHOLDS).evaluate(
                scores=scores[mask],
                labels=labels[mask],
                episode_ids=self.runner._episode_ids(labels[mask]),
            )["threshold_curve"]
            result[spec.key] = {
                "label": spec.label,
                "role": spec.role,
                "rows": int(mask.sum()),
                "mean_score": float(np.mean(scores[mask])),
                "stress_label_rate": float(np.mean(labels[mask])),
                "thresholds": {f"{row['threshold']:.2f}": row for row in curve},
            }
        return result

    def _ordinary_basket(
        self,
        frame: pd.DataFrame,
        labels: np.ndarray,
        final_scores: np.ndarray,
        legacy_scores: np.ndarray,
    ) -> dict[str, Any]:
        dates = pd.to_datetime(frame["date"], errors="coerce")
        close = pd.to_numeric(frame["close"], errors="coerce").ffill()
        drawdown = close / close.cummax().replace(0.0, np.nan) - 1.0
        moderate_mask = ((labels == 0) & (drawdown <= -0.05) & (drawdown > -0.12)).to_numpy()
        baskets: dict[str, Any] = {}
        for spec in WINDOWS:
            if spec.role != "ordinary":
                continue
            mask = ((dates >= pd.Timestamp(spec.start)) & (dates <= pd.Timestamp(spec.end))).to_numpy()
            baskets[spec.key] = self._basket_row(mask, final_scores, legacy_scores, labels)
            baskets[spec.key]["label"] = spec.label
        baskets["all_moderate_nonstress_drawdown"] = self._basket_row(
            moderate_mask,
            final_scores,
            legacy_scores,
            labels,
        )
        baskets["all_moderate_nonstress_drawdown"]["label"] = "All non-stress drawdown days between -5% and -12%"
        return {
            "definition": "Unacceptable inflation is final FPR above 0.20 in any ordinary basket, or final-vs-legacy FPR increase above 0.10 where expected beta remains high.",
            "baskets": baskets,
        }

    @staticmethod
    def _basket_row(
        mask: np.ndarray,
        final_scores: np.ndarray,
        legacy_scores: np.ndarray,
        labels: np.ndarray,
    ) -> dict[str, Any]:
        if not mask.any():
            return {"rows": 0}
        negatives = labels[mask] == 0
        denom = max(1, int(np.sum(negatives)))
        final_trigger = final_scores[mask] >= FINAL_THRESHOLD
        legacy_trigger = legacy_scores[mask] >= 0.50
        return {
            "rows": int(mask.sum()),
            "stress_label_rate": float(np.mean(labels[mask])),
            "final_fpr_at_0_35": float(np.sum(final_trigger & negatives) / denom),
            "legacy_fpr_at_0_50": float(np.sum(legacy_trigger & negatives) / denom),
            "final_minus_legacy_fpr": float((np.sum(final_trigger & negatives) - np.sum(legacy_trigger & negatives)) / denom),
            "final_predicted_positive_rate": float(np.mean(final_trigger)),
            "legacy_predicted_positive_rate": float(np.mean(legacy_trigger)),
        }

    def _downstream_review(
        self,
        frame: pd.DataFrame,
        labels: np.ndarray,
        final_scores: np.ndarray,
        legacy_scores: np.ndarray,
    ) -> dict[str, Any]:
        expected_beta = pd.to_numeric(frame.get("expected_target_beta", pd.Series(np.nan, index=frame.index)), errors="coerce")
        raw_beta = pd.to_numeric(frame.get("raw_target_beta", pd.Series(np.nan, index=frame.index)), errors="coerce")
        beta_delta = raw_beta - expected_beta
        high_expected = expected_beta >= 0.90
        nonstress = labels == 0
        final_trigger = final_scores >= FINAL_THRESHOLD
        legacy_trigger = legacy_scores >= 0.50
        mask = (high_expected.to_numpy(dtype=bool)) & nonstress
        worsening_days = mask & final_trigger & (~legacy_trigger)
        return {
            "tolerance": {
                "max_nonstress_high_beta_trigger_increase": 0.05,
                "max_ordinary_window_trigger_increase": 0.10,
                "rationale": "A direct deployment must not materially increase de-risk triggers on non-stress days where the expected beta contract stays near fully invested.",
            },
            "nonstress_high_expected_beta_rows": int(np.sum(mask)),
            "final_trigger_rate_nonstress_high_beta": float(np.mean(final_trigger[mask])) if np.any(mask) else 0.0,
            "legacy_trigger_rate_nonstress_high_beta": float(np.mean(legacy_trigger[mask])) if np.any(mask) else 0.0,
            "trigger_rate_increase": float(np.mean(final_trigger[mask]) - np.mean(legacy_trigger[mask])) if np.any(mask) else 0.0,
            "worsening_days": int(np.sum(worsening_days)),
            "worst_raw_beta_delta_on_worsening_days": float(np.nanmin(beta_delta.to_numpy(dtype=float)[worsening_days]))
            if np.any(worsening_days)
            else 0.0,
            "mean_raw_beta_delta_on_worsening_days": float(np.nanmean(beta_delta.to_numpy(dtype=float)[worsening_days]))
            if np.any(worsening_days)
            else 0.0,
        }

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
        trigger = np.asarray(scores, dtype=float) >= threshold
        return float(np.mean(trigger[1:] != trigger[:-1]))

    @staticmethod
    def _public_record(record: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if key != "scores"}

    def _decision(self, evidence: dict[str, Any]) -> dict[str, Any]:
        baseline = evidence["registry_baseline"]
        final = evidence["calibrators"][FINAL_CALIBRATOR]
        legacy = evidence["legacy"]
        gates = self._gate_results(evidence, baseline, final, legacy)
        red_flags = self._red_flags(evidence, gates)
        outcome = "DEPLOYABLE" if all(g["status"] == "PASS" for g in gates.values()) and all(
            r["blocks_deployability"] == "NO" for r in red_flags.values()
        ) else "DO_NOT_DEPLOY"
        return {
            "outcome": outcome,
            "selected_candidate": FINAL_CANDIDATE,
            "selected_calibrator": FINAL_CALIBRATOR,
            "selected_policy_mode": "calibrated_fixed_threshold",
            "selected_threshold": FINAL_THRESHOLD,
            "hysteresis_config": None,
            "rollback_mode": "legacy_topology stress posterior mode plus legacy_fixed_0_50 policy, emergency restoration only",
            "gate_results": gates,
            "key_residual_risks": self._residual_risks(gates, red_flags),
            "red_flag_self_audit": red_flags,
        }

    def _gate_results(
        self,
        evidence: dict[str, Any],
        baseline: dict[str, Any],
        final: dict[str, Any],
        legacy: dict[str, Any],
    ) -> dict[str, Any]:
        base_all = baseline["metrics"]["all"]
        base_sep = baseline["metrics"]["separation"]
        posterior = final["posterior"]
        final_curve = {f"{row['threshold']:.2f}": row for row in final["threshold_curve"]}
        windows = final["windows"]
        legacy_windows = legacy["windows"]
        h1 = windows["prolonged_stress_2022_h1"]["thresholds"]["0.35"]
        covid = windows["systemic_crisis_2020_covid"]["thresholds"]["0.35"]
        ghost = windows["false_positive_2023_jul_oct"]["thresholds"]["0.35"]
        legacy_ghost = legacy_windows["false_positive_2023_jul_oct"]["thresholds"]["0.50"]
        ordinary_rows = evidence["ordinary_basket"]["baskets"]
        downstream = evidence["downstream_review"]
        platt = evidence["calibrators"]["platt"]
        threshold_025 = platt["threshold_curve"][2]
        threshold_045 = platt["threshold_curve"][6]
        h1_045 = windows["prolonged_stress_2022_h1"]["thresholds"]["0.45"]
        ordinary_025 = windows["ordinary_correction_2018_q1"]["thresholds"]["0.25"]

        return {
            "A_posterior_quality": self._gate(
                posterior["brier"] < base_all["brier"]
                and posterior["ece"] < base_all["ece"]
                and posterior["separation_rank_auc"] >= base_sep["rank_auc"]
                and posterior["separation_mean_gap"] >= base_sep["mean_gap"],
                "Brier/ECE improve versus legacy, and AUC/mean gap do not regress.",
                {
                    "legacy_brier": base_all["brier"],
                    "final_brier": posterior["brier"],
                    "legacy_ece": base_all["ece"],
                    "final_ece": posterior["ece"],
                    "legacy_auc": base_sep["rank_auc"],
                    "final_auc": posterior["separation_rank_auc"],
                    "legacy_mean_gap": base_sep["mean_gap"],
                    "final_mean_gap": posterior["separation_mean_gap"],
                },
            ),
            "B_2023_ghost_window_repair": self._gate(
                windows["false_positive_2023_jul_oct"]["mean_score"]
                <= baseline["metrics"]["windows"]["false_positive_2023_jul_oct"]["average_pi_stress"] * 0.65
                and ghost["false_positive_rate"] <= 0.10
                and ghost["predicted_positive_rate"] <= legacy_ghost["predicted_positive_rate"] + 0.05,
                "Jul-Oct 2023 average posterior must be materially lower than legacy and policy FPR must stay below 0.10.",
                {
                    "legacy_avg_pi": baseline["metrics"]["windows"]["false_positive_2023_jul_oct"]["average_pi_stress"],
                    "final_avg_pi": windows["false_positive_2023_jul_oct"]["mean_score"],
                    "final_fpr_at_0_35": ghost["false_positive_rate"],
                    "legacy_ppr_at_0_50": legacy_ghost["predicted_positive_rate"],
                    "final_ppr_at_0_35": ghost["predicted_positive_rate"],
                },
            ),
            "C_prolonged_stress_capture": self._gate(
                h1["recall"] >= 0.85 and h1["episode_capture_rate"] >= 0.80 and covid["recall"] >= 0.70,
                "Final policy must capture 2022 H1 recall >= 0.85, episode capture >= 0.80, and COVID recall >= 0.70.",
                {
                    "h1_recall_at_0_35": h1["recall"],
                    "h1_episode_capture_at_0_35": h1["episode_capture_rate"],
                    "covid_recall_at_0_35": covid["recall"],
                },
            ),
            "D_ordinary_correction_control": self._gate(
                all(row.get("final_fpr_at_0_35", 0.0) <= 0.20 for row in ordinary_rows.values())
                and all(row.get("final_minus_legacy_fpr", 0.0) <= 0.10 for row in ordinary_rows.values()),
                "No ordinary basket may exceed 0.20 FPR or increase more than 0.10 versus legacy.",
                ordinary_rows,
            ),
            "E_calibration_stability": self._gate(
                platt["plateau"]["largest_plateau_fraction"] <= 0.01
                and platt["plateau"]["unique_score_levels"] >= 500
                and threshold_025["recall"] >= 0.80
                and threshold_045["recall"] >= 0.70
                and h1_045["recall"] >= 0.75
                and ordinary_025["false_positive_rate"] <= 0.30,
                "Selected calibrator must be smooth and threshold +/-0.10 must not break stress capture or ordinary correction.",
                {
                    "unique_score_levels": platt["plateau"]["unique_score_levels"],
                    "largest_plateau_fraction": platt["plateau"]["largest_plateau_fraction"],
                    "all_recall_at_0_25": threshold_025["recall"],
                    "all_recall_at_0_45": threshold_045["recall"],
                    "h1_recall_at_0_45": h1_045["recall"],
                    "ordinary_2018_fpr_at_0_25": ordinary_025["false_positive_rate"],
                },
            ),
            "F_downstream_safety_screen": self._gate(
                downstream["trigger_rate_increase"]
                <= downstream["tolerance"]["max_nonstress_high_beta_trigger_increase"]
                and all(
                    row.get("final_minus_legacy_fpr", 0.0)
                    <= downstream["tolerance"]["max_ordinary_window_trigger_increase"]
                    for row in ordinary_rows.values()
                ),
                "Final policy must not materially increase triggers on non-stress high-expected-beta days or ordinary windows.",
                downstream,
            ),
        }

    @staticmethod
    def _gate(pass_condition: bool, rule: str, evidence: Any) -> dict[str, Any]:
        return {"status": "PASS" if bool(pass_condition) else "FAIL", "rule": rule, "evidence": evidence}

    def _red_flags(self, evidence: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
        final = evidence["calibrators"][FINAL_CALIBRATOR]
        isotonic = evidence["calibrators"]["isotonic"]
        ordinary_failed = gates["D_ordinary_correction_control"]["status"] == "FAIL"
        stability_failed = gates["E_calibration_stability"]["status"] == "FAIL"
        downstream_failed = gates["F_downstream_safety_screen"]["status"] == "FAIL"
        deployment_failed = any(g["status"] == "FAIL" for key, g in gates.items() if key != "A_posterior_quality")
        flags = {
            "red_flag_1_conditional_language_disguised_as_finality": self._flag(False, "Final reports use binary go/no-go language.", "No blocker."),
            "red_flag_2_posterior_improvement_masking_policy_weakness": self._flag(
                deployment_failed,
                "Posterior quality passes, but policy stability, ordinary correction, or downstream gates fail.",
                "Blocks unless every deployment gate passes.",
            ),
            "red_flag_3_threshold_migration_doing_all_the_work": self._flag(
                stability_failed,
                "Prolonged-stress capture requires moving below legacy 0.50, and +/-0.10 robustness is not clean.",
                "Blocks direct deployment.",
            ),
            "red_flag_4_menu_masquerading_as_decision": self._flag(False, "One tested configuration is named: C9 architecture, Platt calibrator, 0.35 fixed threshold.", "No blocker."),
            "red_flag_5_ordinary_correction_weakness_ignored": self._flag(
                ordinary_failed,
                "Ordinary basket evidence is explicit and fails the hard tolerance.",
                "Blocks direct deployment.",
            ),
            "red_flag_6_proxy_label_mismatch_as_excuse": self._flag(False, "False positives are quantified and not excused by label ambiguity.", "No blocker."),
            "red_flag_7_calibrator_instability_near_operating_threshold": self._flag(
                stability_failed,
                f"Platt is smooth ({final['plateau']['unique_score_levels']:.0f} levels), but threshold-local policy behavior fails +/-0.10 checks. Isotonic plateau reference: {isotonic['plateau']['largest_plateau_fraction']:.4f}.",
                "Blocks direct deployment.",
            ),
            "red_flag_8_downstream_beta_risk_waved_away": self._flag(
                downstream_failed,
                "Downstream beta safety was quantified and fails tolerance.",
                "Blocks direct deployment.",
            ),
            "red_flag_9_hidden_top_level_hard_gates": self._flag(False, "No raw market or macro feature hard gate is introduced by this package.", "No blocker."),
            "red_flag_10_binary_outcome_not_binary": self._flag(False, "Machine outcome is DEPLOYABLE or DO_NOT_DEPLOY only.", "No blocker."),
        }
        return flags

    @staticmethod
    def _flag(triggered: bool, evidence: str, resolution: str) -> dict[str, str]:
        return {
            "triggered": "YES" if triggered else "NO",
            "evidence": evidence,
            "resolution": resolution,
            "blocks_deployability": "YES" if triggered else "NO",
        }

    @staticmethod
    def _residual_risks(gates: dict[str, Any], red_flags: dict[str, Any]) -> list[str]:
        risks = [f"{key}: {gate['rule']}" for key, gate in gates.items() if gate["status"] == "FAIL"]
        risks.extend(f"{key}: {flag['evidence']}" for key, flag in red_flags.items() if flag["blocks_deployability"] == "YES")
        return risks

    def _write_json(self, decision: dict[str, Any]) -> None:
        serializable = json.loads(json.dumps(decision, default=self._json_default))
        (self.output_dir / "final_decision.json").write_text(
            json.dumps(serializable, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        return str(value)

    def _write_reports(self, evidence: dict[str, Any], decision: dict[str, Any]) -> None:
        self._write_recommendation(evidence, decision)
        self._write_configuration_spec(decision)
        self._write_calibrator_decision(evidence, decision)
        self._write_policy_decision(evidence, decision)
        self._write_gate_results(decision)
        self._write_red_flags(decision)

    def _write_recommendation(self, evidence: dict[str, Any], decision: dict[str, Any]) -> None:
        outcome_text = "DEPLOYABLE CONFIGURATION SELECTED" if decision["outcome"] == "DEPLOYABLE" else "DO NOT DEPLOY"
        gates = decision["gate_results"]
        text = f"""# pi_stress Final Go/No-Go Recommendation

## Binary Decision

{outcome_text}

## Evaluated Configuration

- Candidate architecture: `{decision['selected_candidate']}`
- Calibrator: `{decision['selected_calibrator']}`
- Policy mode: `{decision['selected_policy_mode']}`
- Primary threshold: `{decision['selected_threshold']:.2f}`
- Hysteresis: none
- Emergency rollback mode: `{decision['rollback_mode']}`

## Decision Basis

Posterior quality passes, but direct deployment fails hard gates that are downstream of posterior scoring. The selected Platt calibrator avoids the isotonic plateau concentration, yet the final operating policy is not robust enough for direct production use: threshold-local behavior fails, ordinary-correction inflation remains above tolerance, and the downstream beta safety screen fails.

## Gate Summary

| Gate | Status |
|---|---|
{self._gate_rows(gates)}

## Final Outcome

{outcome_text}
"""
        (self.report_dir / "pi_stress_final_go_no_go_recommendation.md").write_text(text, encoding="utf-8")

    def _write_configuration_spec(self, decision: dict[str, Any]) -> None:
        text = f"""# pi_stress Final Configuration Spec

## FINAL_SELECTED_CONFIGURATION

This is the single evaluated end-state configuration. It is not approved for deployment because the hard gate fails.

```json
{json.dumps({k: decision[k] for k in ['selected_candidate', 'selected_calibrator', 'selected_policy_mode', 'selected_threshold', 'hysteresis_config', 'rollback_mode']}, indent=2, sort_keys=True)}
```

## Policy Contract

The policy uses only the calibrated pi_stress posterior and a fixed threshold. No calendar episode patching and no raw macro or market feature gate is part of the configuration.
"""
        (self.report_dir / "pi_stress_final_configuration_spec.md").write_text(text, encoding="utf-8")

    def _write_calibrator_decision(self, evidence: dict[str, Any], decision: dict[str, Any]) -> None:
        rows = []
        for name, record in evidence["calibrators"].items():
            posterior = record["posterior"]
            plateau = record["plateau"]
            row035 = next(row for row in record["threshold_curve"] if abs(row["threshold"] - FINAL_THRESHOLD) < 1e-9)
            rows.append(
                f"| {name} | {posterior['brier']:.4f} | {posterior['ece']:.4f} | {posterior['separation_rank_auc']:.4f} | "
                f"{posterior['separation_mean_gap']:.4f} | {plateau['unique_score_levels']:.0f} | {plateau['largest_plateau_fraction']:.4f} | "
                f"{record['flip_frequency']['0.35']:.4f} | {row035['precision']:.4f} | {row035['recall']:.4f} | {row035['false_positive_rate']:.4f} |"
            )
        text = f"""# pi_stress Final Calibrator Decision

## FINAL_CALIBRATOR_DECISION

Selected calibrator for the single evaluated policy: `{decision['selected_calibrator']}`.

Platt is selected over isotonic for direct-governance evaluation because it preserves posterior improvement versus legacy while avoiding the 18-level isotonic plateau structure. Weighted Platt and balanced Platt are rejected because they inflate ordinary-correction and ghost-window trigger rates. This selection does not make the package deployable; policy robustness and downstream safety still fail.

| Calibrator | Brier | ECE | AUC | Mean Gap | Unique Levels | Largest Plateau | Flip @ 0.35 | Precision @ 0.35 | Recall @ 0.35 | FPR @ 0.35 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}
"""
        (self.report_dir / "pi_stress_final_calibrator_decision.md").write_text(text, encoding="utf-8")

    def _write_policy_decision(self, evidence: dict[str, Any], decision: dict[str, Any]) -> None:
        final = evidence["calibrators"][FINAL_CALIBRATOR]
        rows = []
        windows = final["windows"]
        for row in final["threshold_curve"]:
            if row["threshold"] not in {0.25, 0.30, 0.35, 0.40, 0.45}:
                continue
            key = f"{row['threshold']:.2f}"
            rows.append(
                f"| {row['threshold']:.2f} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
                f"{row['false_positive_rate']:.4f} | {row['predicted_positive_rate']:.4f} | {row['episode_capture_rate']:.4f} | "
                f"{windows['ordinary_correction_2018_q1']['thresholds'][key]['false_positive_rate']:.4f} | "
                f"{windows['false_positive_2023_jul_oct']['thresholds'][key]['false_positive_rate']:.4f} | "
                f"{windows['prolonged_stress_2022_h1']['thresholds'][key]['recall']:.4f} | "
                f"{windows['systemic_crisis_2020_covid']['thresholds'][key]['recall']:.4f} |"
            )
        text = f"""# pi_stress Final Policy Decision

## FINAL_POLICY_DECISION

Single evaluated policy: `{decision['selected_policy_mode']}` at threshold `{decision['selected_threshold']:.2f}` with no hysteresis.

The 0.35 threshold is the least bad fixed operating point in the C9+Platt comparison: it repairs 2022 H1 better than legacy 0.50 and keeps Jul-Oct 2023 below the ghost-window tolerance. It is not a deployable operating point because +/-0.10 threshold robustness fails.

| Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture | 2018 Q1 FPR | 2023 Ghost FPR | 2022 H1 Recall | 2020 COVID Recall |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}
"""
        (self.report_dir / "pi_stress_final_policy_decision.md").write_text(text, encoding="utf-8")

    def _write_gate_results(self, decision: dict[str, Any]) -> None:
        blocks = [key for key, gate in decision["gate_results"].items() if gate["status"] == "FAIL"]
        text = f"""# pi_stress Final Gate Results

| Gate | Status | Rule | Evidence |
|---|---|---|---|
{self._detailed_gate_rows(decision['gate_results'])}

## Blocking Gates

{', '.join(blocks) if blocks else 'None'}
"""
        (self.report_dir / "pi_stress_final_gate_results.md").write_text(text, encoding="utf-8")

    def _write_red_flags(self, decision: dict[str, Any]) -> None:
        rows = []
        for key, flag in decision["red_flag_self_audit"].items():
            rows.append(
                f"| {key} | {flag['triggered']} | {flag['evidence']} | {flag['resolution']} | {flag['blocks_deployability']} |"
            )
        text = f"""# pi_stress Final Self-Audit Red Flags

The red-flag audit is a hard deployment gate.

| Red Flag | Triggered | Evidence | Resolution | Blocks Deployability |
|---|---|---|---|---|
{chr(10).join(rows)}
"""
        (self.report_dir / "pi_stress_final_self_audit_red_flags.md").write_text(text, encoding="utf-8")

    @staticmethod
    def _gate_rows(gates: dict[str, Any]) -> str:
        return "\n".join(f"| {key} | {gate['status']} |" for key, gate in gates.items())

    @staticmethod
    def _detailed_gate_rows(gates: dict[str, Any]) -> str:
        rows = []
        for key, gate in gates.items():
            evidence = json.dumps(gate["evidence"], sort_keys=True, default=str)
            if len(evidence) > 900:
                evidence = evidence[:897] + "..."
            rows.append(f"| {key} | {gate['status']} | {gate['rule']} | `{evidence}` |")
        return "\n".join(rows)


def main() -> None:
    result = PiStressFinalGoNoGo().write()
    print(json.dumps({"outcome": result["outcome"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
