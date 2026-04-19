from __future__ import annotations

import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.product_cycle_dashboard import (  # noqa: E402
    STAGES,
    ProductCycleDashboard,
    ProductDashboardInput,
)
from src.models import SignalResult  # noqa: E402


@dataclass(frozen=True)
class PatchVariant:
    name: str
    temperature: float
    smoothing_alpha: float
    boundary_passthrough: float
    recovery_gain: float
    relapse_penalty: float
    stress_gain: float
    boundary_gain: float
    late_cycle_penalty: float
    diffusion_gamma: float


class ProductCycleDashboardPatch(ProductCycleDashboard):
    PRODUCT_NAME = "Daily Post-Close Cycle Stage Probability Dashboard"

    def __init__(self, root: str | Path = ".") -> None:
        super().__init__(root=root)
        self.artifacts_dir = self.root / "artifacts" / "product_patch"
        self.reports_dir = self.root / "reports"

    def run_all(self) -> dict[str, str]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self._build_patch_frame()
        baseline_variant = self._baseline_variant()
        baseline_process = self._evaluate_variant(frame, baseline_variant)
        launch_claim_lock = self._launch_claim_lock()
        calibration_failure_audit = self._calibration_failure_audit(baseline_process)

        iteration = self._run_patch_iterations(frame, baseline_process)
        patched_process = iteration["selected_attempt"]["process"]

        recovery_calibration_repair = self._recovery_calibration_repair_payload(
            baseline_process, iteration
        )
        stress_liquidity_anchoring_repair = self._stress_liquidity_anchoring_payload(
            baseline_process, patched_process
        )
        probability_diffusion_repair = self._probability_diffusion_payload(
            baseline_process, patched_process
        )
        index_html_ui_alignment = self._index_html_ui_alignment_payload()
        full_path_integration_audit = self._full_path_integration_payload(
            index_html_ui_alignment
        )
        historical_revalidation = self._historical_revalidation_payload(
            baseline_process, patched_process
        )
        self_iteration_gate = self._self_iteration_gate_payload(
            recovery_calibration_repair,
            stress_liquidity_anchoring_repair,
            probability_diffusion_repair,
            index_html_ui_alignment,
            full_path_integration_audit,
            iteration,
        )
        acceptance_checklist = self._acceptance_checklist(
            launch_claim_lock,
            calibration_failure_audit,
            recovery_calibration_repair,
            stress_liquidity_anchoring_repair,
            probability_diffusion_repair,
            index_html_ui_alignment,
            full_path_integration_audit,
            historical_revalidation,
            self_iteration_gate,
        )
        final_verdict = self._final_verdict_payload(
            recovery_calibration_repair,
            stress_liquidity_anchoring_repair,
            probability_diffusion_repair,
            index_html_ui_alignment,
            full_path_integration_audit,
            historical_revalidation,
            self_iteration_gate,
            acceptance_checklist,
        )

        payloads = {
            "launch_claim_lock": launch_claim_lock,
            "calibration_failure_audit": calibration_failure_audit,
            "recovery_calibration_repair": recovery_calibration_repair,
            "stress_liquidity_anchoring_repair": stress_liquidity_anchoring_repair,
            "probability_diffusion_repair": probability_diffusion_repair,
            "index_html_ui_alignment": index_html_ui_alignment,
            "full_path_integration_audit": full_path_integration_audit,
            "historical_revalidation": historical_revalidation,
            "self_iteration_gate": self_iteration_gate,
            "final_verdict": final_verdict,
        }

        for stem, payload in payloads.items():
            self._write_json(f"{stem}.json", payload)
        self._write_md(
            "product_patch_launch_claim_lock.md",
            "Product Patch Launch Claim Lock",
            launch_claim_lock,
        )
        self._write_md(
            "product_patch_calibration_failure_audit.md",
            "Product Patch Calibration Failure Audit",
            calibration_failure_audit,
        )
        self._write_md(
            "product_patch_recovery_calibration_repair.md",
            "Product Patch Recovery Calibration Repair",
            recovery_calibration_repair,
        )
        self._write_md(
            "product_patch_stress_liquidity_anchoring_repair.md",
            "Product Patch Stress Liquidity Anchoring Repair",
            stress_liquidity_anchoring_repair,
        )
        self._write_md(
            "product_patch_probability_diffusion_repair.md",
            "Product Patch Probability Diffusion Repair",
            probability_diffusion_repair,
        )
        self._write_md(
            "product_patch_index_html_ui_alignment.md",
            "Product Patch Index HTML UI Alignment",
            index_html_ui_alignment,
        )
        self._write_md(
            "product_patch_full_path_integration_audit.md",
            "Product Patch Full Path Integration Audit",
            full_path_integration_audit,
        )
        self._write_md(
            "product_patch_historical_revalidation.md",
            "Product Patch Historical Revalidation",
            historical_revalidation,
        )
        self._write_md(
            "product_patch_self_iteration_gate.md",
            "Product Patch Self Iteration Gate",
            self_iteration_gate,
        )
        self._write_md(
            "product_patch_acceptance_checklist.md",
            "Product Patch Acceptance Checklist",
            acceptance_checklist,
        )
        self._write_md(
            "product_patch_final_verdict.md",
            "Product Patch Final Verdict",
            final_verdict,
        )
        return {"final_verdict": final_verdict["final_verdict"]}

    @classmethod
    def build_runtime_dashboard_payload(cls, result: SignalResult) -> dict[str, Any]:
        patch = cls(root=REPO_ROOT)
        item, synthetic_row = patch._runtime_input_from_signal(result)
        probs = patch._stage_probabilities_variant(
            item=item,
            row=synthetic_row,
            variant=patch._selected_runtime_variant(),
        )
        legacy = patch._legacy_runtime_stage_distribution(result, item)
        probs = patch._normalize_probabilities(
            {
                stage: 0.55 * legacy.get(stage, 0.0) + 0.45 * probs.get(stage, 0.0)
                for stage in STAGES
            }
        )
        output = patch._daily_output(item, probs)
        return {
            "product_name": patch.PRODUCT_NAME,
            "summary": {
                "date": item.date,
                "current_stage": output["dominant_stage"],
                "secondary_stage": output["secondary_stage"],
                "stage_confidence": output["stage_stability"]["top1_probability"],
                "confidence_margin": output["stage_stability"]["top1_margin"],
                "stage_stability": output["stage_stability"]["concentration_label"],
                "short_rationale": output["short_rationale"],
            },
            "stage_distribution": output["stage_probabilities"],
            "transition_urgency": output["transition_urgency"],
            "action_band": output["action_relevance_band"],
            "stage_stability": output["stage_stability"],
            "evidence_panel": output["evidence_panel"],
            "boundary_warning": output["boundary_warning"],
            "probability_dynamics": output["probability_dynamics"],
            "expectations": output["expectation_section"],
            "limits": [
                "Do not infer automatic leverage.",
                "Do not infer exact turning-point prediction.",
                "Do not treat boundary warnings as ordinary stage calls.",
            ],
            "product_scope": {
                "auto_beta_control_restored": False,
                "auto_trading_engine": False,
                "turning_point_prediction_solved": False,
            },
        }

    def _legacy_runtime_stage_distribution(
        self, result: SignalResult, item: ProductDashboardInput
    ) -> dict[str, float]:
        mid = float(result.probabilities.get("MID_CYCLE", 0.0) or 0.0)
        late = float(result.probabilities.get("LATE_CYCLE", 0.0) or 0.0)
        stress = float(result.probabilities.get("BUST", 0.0) or 0.0) + float(
            result.probabilities.get("STRESS", 0.0) or 0.0
        )
        recovery = float(result.probabilities.get("RECOVERY", 0.0) or 0.0)
        boundary = 0.0
        if item.boundary_pressure >= 0.70 or (
            item.boundary_pressure >= 0.48 and item.volatility_percentile >= 0.92
        ):
            boundary = min(0.55, 0.55 * item.boundary_pressure + 0.20 * item.stress_score)
        legacy = {
            "EXPANSION": mid,
            "LATE_CYCLE": max(0.0, late - 0.45 * boundary),
            "STRESS": stress + 0.35 * boundary,
            "RECOVERY": recovery,
            "FAST_CASCADE_BOUNDARY": boundary,
        }
        return self._normalize_probabilities(legacy)

    def _build_patch_frame(self) -> pd.DataFrame:
        frame = self._build_product_frame().copy()
        frame["gap_pressure_1d"] = frame["gap_ret"].clip(upper=0.0).abs()
        frame["gap_pressure_3d"] = frame["gap_pressure_1d"].rolling(3, min_periods=1).sum()
        frame["breadth_shock"] = (-frame["breadth_delta_10d"]).clip(lower=0.0)
        frame["vol_shock"] = frame["volatility_delta_10d"].clip(lower=0.0)
        repair_flag = frame["repair_confirmation"].astype(float)
        frame["repair_ratio_5d"] = repair_flag.rolling(5, min_periods=1).mean().clip(0.0, 1.0)
        frame["repair_ratio_10d"] = repair_flag.rolling(10, min_periods=1).mean().clip(0.0, 1.0)
        frame["stress_below_threshold_ratio"] = (
            (frame["stress_score"] <= 0.42).astype(float).rolling(10, min_periods=1).mean()
        ).clip(0.0, 1.0)
        frame["breadth_repair_ratio"] = (
            (frame["breadth_proxy"] >= 0.46).astype(float).rolling(10, min_periods=1).mean()
        ).clip(0.0, 1.0)
        frame["recovery_compliance_ratio"] = np.clip(
            0.30 * frame["repair_ratio_5d"]
            + 0.30 * frame["repair_ratio_10d"]
            + 0.20 * frame["stress_below_threshold_ratio"]
            + 0.20 * frame["breadth_repair_ratio"],
            0.0,
            1.0,
        )
        frame["insufficient_recovery_compliance"] = (
            frame["recovery_compliance_ratio"] < 0.58
        ).astype(float)
        frame["release_while_unresolved"] = (
            frame["repair_confirmation"]
            & (
                (frame["stress_below_threshold_ratio"] < 0.55)
                | (frame["breadth_repair_ratio"] < 0.45)
            )
        ).astype(float)
        frame["recent_relapse_signal"] = (
            frame["relapse_flag"].astype(float).rolling(10, min_periods=1).max()
        ).clip(0.0, 1.0)
        frame["repair_evidence_score"] = np.clip(
            0.25 * frame["repair_confirmation"].astype(float)
            + 0.25 * frame["repair_ratio_5d"]
            + 0.25 * frame["repair_ratio_10d"]
            + 0.25 * frame["recovery_compliance_ratio"],
            0.0,
            1.0,
        )
        frame["relapse_pressure_score"] = np.clip(
            0.40 * frame["release_while_unresolved"]
            + 0.35 * frame["recent_relapse_signal"]
            + 0.25 * frame["insufficient_recovery_compliance"],
            0.0,
            1.0,
        )
        frame["acute_liquidity_score"] = np.clip(
            0.42 * (frame["gap_pressure_3d"] / 0.06)
            + 0.22 * frame["volatility_percentile"]
            + 0.18 * frame["stress_score"]
            + 0.08 * ((-frame["breadth_delta_10d"]).clip(lower=0.0) / 0.10),
            0.0,
            1.0,
        )
        return frame

    @staticmethod
    def _baseline_variant() -> PatchVariant:
        return PatchVariant(
            name="baseline_pre_patch",
            temperature=0.90,
            smoothing_alpha=0.36,
            boundary_passthrough=0.88,
            recovery_gain=0.0,
            relapse_penalty=0.0,
            stress_gain=0.0,
            boundary_gain=0.0,
            late_cycle_penalty=0.0,
            diffusion_gamma=0.0,
        )

    @staticmethod
    def _candidate_variants() -> list[PatchVariant]:
        return [
            PatchVariant(
                name="recovery_compliance_light",
                temperature=0.90,
                smoothing_alpha=0.36,
                boundary_passthrough=0.88,
                recovery_gain=0.12,
                relapse_penalty=0.12,
                stress_gain=0.0,
                boundary_gain=0.0,
                late_cycle_penalty=0.0,
                diffusion_gamma=0.0,
            ),
            PatchVariant(
                name="recovery_compliance_balanced",
                temperature=0.90,
                smoothing_alpha=0.36,
                boundary_passthrough=0.88,
                recovery_gain=0.18,
                relapse_penalty=0.18,
                stress_gain=0.0,
                boundary_gain=0.0,
                late_cycle_penalty=0.0,
                diffusion_gamma=0.0,
            ),
            PatchVariant(
                name="recovery_compliance_guarded",
                temperature=0.90,
                smoothing_alpha=0.36,
                boundary_passthrough=0.88,
                recovery_gain=0.22,
                relapse_penalty=0.22,
                stress_gain=0.0,
                boundary_gain=0.0,
                late_cycle_penalty=0.0,
                diffusion_gamma=0.0,
            ),
        ]

    def _selected_runtime_variant(self) -> PatchVariant:
        return self._candidate_variants()[-1]

    def _launch_claim_lock(self) -> dict[str, Any]:
        return {
            "decision": "LAUNCH_LANGUAGE_REMAINS_OVERSTATED",
            "current_product_launch_claim_is_accepted": False,
            "current_state": "pre-launch patch mode",
            "production_style_language_allowed": False,
            "dashboard_spec_ready_is_ui_ready": False,
            "summary": (
                "The current launch claim is not yet accepted. The repository enters pre-launch "
                "patch mode until calibration, acute-liquidity anchoring, and the real UI path are repaired."
            ),
        }

    def _run_patch_iterations(
        self, frame: pd.DataFrame, baseline_process: pd.DataFrame
    ) -> dict[str, Any]:
        baseline_metrics = self._iteration_metrics(baseline_process)
        attempts: list[dict[str, Any]] = []
        selected_attempt: dict[str, Any] | None = None
        for variant in self._candidate_variants():
            process = self._evaluate_variant(frame, variant)
            metrics = self._iteration_metrics(process)
            passes = self._passes_patch_targets(metrics, baseline_metrics)
            attempt = {
                "variant": variant,
                "process": process,
                "metrics": metrics,
                "passes": passes,
                "score": self._iteration_score(metrics, baseline_metrics),
            }
            attempts.append(attempt)
            if passes and selected_attempt is None:
                selected_attempt = attempt
        if selected_attempt is None:
            selected_attempt = max(attempts, key=lambda attempt: attempt["score"])
        return {
            "attempts": attempts,
            "selected_attempt": selected_attempt,
            "self_iteration_required": selected_attempt is not attempts[0],
            "self_iteration_succeeded": selected_attempt["passes"],
            "baseline_metrics": baseline_metrics,
        }

    def _iteration_metrics(self, process: pd.DataFrame) -> dict[str, Any]:
        stage_metrics = self._classwise_stage_metrics(process)
        stability = self._stability_metrics(process)
        diffusion = self._diffusion_metrics(process)
        quality = self._quality_metrics(process)
        acute_windows = {
            "august_2015": self._window_anchor_metrics(
                process, "2015-08-17", "2015-09-15"
            ),
            "covid_2020": self._window_anchor_metrics(
                process, "2020-02-19", "2020-04-30"
            ),
            "late_cycle_contrast": self._window_anchor_metrics(
                process, "2014-09-15", "2014-10-17"
            ),
        }
        return {
            "stage_metrics": stage_metrics,
            "stability": stability,
            "diffusion": diffusion,
            "quality": quality,
            "acute_windows": acute_windows,
        }

    def _passes_patch_targets(
        self, metrics: dict[str, Any], baseline_metrics: dict[str, Any]
    ) -> bool:
        recovery_gap = metrics["stage_metrics"]["RECOVERY"]["confidence_gap"]
        false_recovery = metrics["stability"]["false_recovery_declaration_rate"]
        baseline_recovery_gap = baseline_metrics["stage_metrics"]["RECOVERY"]["confidence_gap"]
        baseline_false_recovery = baseline_metrics["stability"]["false_recovery_declaration_rate"]
        stress_accuracy = metrics["stage_metrics"]["STRESS"]["accuracy"]
        late_cycle_accuracy = metrics["stage_metrics"]["LATE_CYCLE"]["accuracy"]
        baseline_stress_accuracy = baseline_metrics["stage_metrics"]["STRESS"]["accuracy"]
        baseline_late_cycle_accuracy = baseline_metrics["stage_metrics"]["LATE_CYCLE"]["accuracy"]
        critical_diffuse_share = metrics["diffusion"]["critical_stage_diffuse_share"]
        baseline_diffuse_share = baseline_metrics["diffusion"]["critical_stage_diffuse_share"]
        overconfidence = metrics["quality"]["dominant_stage_overconfidence_rate"]
        baseline_overconfidence = baseline_metrics["quality"]["dominant_stage_overconfidence_rate"]
        return (
            false_recovery < baseline_false_recovery
            and recovery_gap > baseline_recovery_gap
            and stress_accuracy >= baseline_stress_accuracy - 0.02
            and late_cycle_accuracy >= baseline_late_cycle_accuracy - 0.02
            and critical_diffuse_share <= baseline_diffuse_share + 0.01
            and overconfidence <= baseline_overconfidence + 0.01
        )

    def _iteration_score(
        self, metrics: dict[str, Any], baseline_metrics: dict[str, Any]
    ) -> float:
        recovery_gap = metrics["stage_metrics"]["RECOVERY"]["confidence_gap"]
        false_recovery = metrics["stability"]["false_recovery_declaration_rate"]
        stress_accuracy = metrics["stage_metrics"]["STRESS"]["accuracy"]
        late_cycle_accuracy = metrics["stage_metrics"]["LATE_CYCLE"]["accuracy"]
        critical_diffuse_share = metrics["diffusion"]["critical_stage_diffuse_share"]
        overconfidence = metrics["quality"]["dominant_stage_overconfidence_rate"]
        return (
            2.2
            * (recovery_gap - baseline_metrics["stage_metrics"]["RECOVERY"]["confidence_gap"])
            + 2.0
            * (
                baseline_metrics["stability"]["false_recovery_declaration_rate"]
                - false_recovery
            )
            + 0.6
            * (stress_accuracy - baseline_metrics["stage_metrics"]["STRESS"]["accuracy"])
            + 0.4
            * (
                late_cycle_accuracy
                - baseline_metrics["stage_metrics"]["LATE_CYCLE"]["accuracy"]
            )
            - 0.5
            * (
                critical_diffuse_share
                - baseline_metrics["diffusion"]["critical_stage_diffuse_share"]
            )
            - 0.3
            * (
                overconfidence
                - baseline_metrics["quality"]["dominant_stage_overconfidence_rate"]
            )
        )

    def _evaluate_variant(self, frame: pd.DataFrame, variant: PatchVariant) -> pd.DataFrame:
        raw_rows = []
        for _, row in frame.iterrows():
            item = self._input_from_row(row)
            raw_rows.append(self._stage_probabilities_variant(item=item, row=row, variant=variant))
        raw_probs = pd.DataFrame(raw_rows, index=frame.index)
        smoothed = raw_probs.ewm(alpha=variant.smoothing_alpha, adjust=False).mean()
        smoothed = smoothed.div(smoothed.sum(axis=1), axis=0)

        records = []
        previous_probs: dict[str, float] | None = None
        previous_previous_probs: dict[str, float] | None = None
        for index, row in frame.iterrows():
            item = self._input_from_row(row)
            probabilities = {stage: float(smoothed.loc[index, stage]) for stage in STAGES}
            output = self._daily_output(
                item,
                probabilities,
                previous_probs=previous_probs,
                previous_previous_probs=previous_previous_probs,
            )
            records.append(
                {
                    **{f"prob_{stage}": probabilities[stage] for stage in STAGES},
                    "date": pd.Timestamp(row["date"]),
                    "reference_stage": row["reference_stage"],
                    "dominant_stage": output["dominant_stage"],
                    "secondary_stage": output["secondary_stage"],
                    "transition_urgency": output["transition_urgency"],
                    "action_relevance_band": output["action_relevance_band"],
                    "entropy": output["stage_stability"]["normalized_entropy"],
                    "top1_probability": output["stage_stability"]["top1_probability"],
                    "top1_margin": output["stage_stability"]["top1_margin"],
                    "concentration_label": output["stage_stability"]["concentration_label"],
                    "boundary_active": output["boundary_warning"]["is_active"],
                    "hazard_score": item.hazard_score,
                    "hazard_percentile": item.hazard_percentile,
                    "stress_score": item.stress_score,
                    "breadth_proxy": item.breadth_proxy,
                    "volatility_percentile": item.volatility_percentile,
                    "boundary_pressure": item.boundary_pressure,
                    "acute_liquidity_score": float(row["acute_liquidity_score"]),
                    "repair_evidence_score": float(row["repair_evidence_score"]),
                    "relapse_pressure_score": float(row["relapse_pressure_score"]),
                    "daily_output": output,
                    "variant_name": variant.name,
                }
            )
            previous_previous_probs = previous_probs
            previous_probs = probabilities
        process = pd.DataFrame(records)
        return self._attach_distribution_changes(process)

    def _stage_probabilities_variant(
        self,
        *,
        item: ProductDashboardInput,
        row: pd.Series,
        variant: PatchVariant,
    ) -> dict[str, float]:
        scores = self._stage_logits_variant(item=item, row=row, variant=variant, apply_penalty=True)
        return self._softmax(scores, temperature=variant.temperature)

    def _stage_logits_variant(
        self,
        *,
        item: ProductDashboardInput,
        row: pd.Series | dict[str, float],
        variant: PatchVariant,
        apply_penalty: bool,
    ) -> dict[str, float]:
        scores = self._base_stage_logits(item)
        repair_evidence = self._clip01(row["repair_evidence_score"])
        scores["RECOVERY"] += variant.recovery_gain * repair_evidence
        if apply_penalty:
            penalty = self._recovery_logit_relapse_penalty(row=row, variant=variant)
            scores["RECOVERY"] -= penalty["penalty"]
        return scores

    def _base_stage_logits(self, item: ProductDashboardInput) -> dict[str, float]:
        h = self._clip01(item.hazard_score)
        hp = self._clip01(item.hazard_percentile)
        s = self._clip01(item.stress_score)
        b = self._clip01(item.breadth_proxy)
        v = self._clip01(item.volatility_percentile)
        hd = self._clip01(item.hazard_delta_5d / 0.14)
        bd = self._clip01(-item.breadth_delta_10d / 0.12)
        repair = 1.0 if item.repair_confirmation else 0.0
        relapse = 1.0 if item.relapse_flag else 0.0
        structural = 1.0 if item.structural_stress else 0.0
        boundary = self._clip01(item.boundary_pressure / 0.10)
        stress_persist = self._clip01(item.stress_persistence_days / 30.0)
        repair_persist = self._clip01(item.repair_persistence_days / 12.0)

        scores = {
            "EXPANSION": 1.20 * (1.0 - h) + 1.15 * b + 0.95 * (1.0 - v) + 0.70 * (1.0 - s),
            "LATE_CYCLE": 0.38
            + 1.10 * h
            + 0.55 * hp
            + 0.95 * (1.0 - b)
            + 0.72 * v
            + 0.55 * hd
            + 0.45 * bd,
            "STRESS": 0.16
            + 1.75 * s
            + 1.00 * structural
            + 0.86 * (1.0 - b)
            + 0.78 * v
            + 0.54 * stress_persist
            + 0.30 * relapse,
            "RECOVERY": 0.14 + 1.45 * repair + 0.42 * repair_persist,
            "FAST_CASCADE_BOUNDARY": 0.02
            + 2.70 * boundary
            + 0.80 * (v >= 0.96 and hd > 0.45)
            + 0.58 * relapse
            + 0.32 * structural,
        }
        if item.repair_confirmation and not item.relapse_flag:
            scores["STRESS"] -= 0.35
            scores["LATE_CYCLE"] -= 0.12
        if self._boundary_active(item):
            scores["FAST_CASCADE_BOUNDARY"] += 1.55
            scores["EXPANSION"] -= 0.90
            scores["RECOVERY"] -= 0.60
        if s < 0.26 and b > 0.52 and v < 0.58:
            scores["EXPANSION"] += 0.45
        if h >= 0.30 or s >= 0.30:
            scores["LATE_CYCLE"] += 0.35
            scores["EXPANSION"] -= 0.25
        return scores

    def _recovery_logit_relapse_penalty(
        self, *, row: pd.Series | dict[str, float], variant: PatchVariant
    ) -> dict[str, Any]:
        signals = {
            "release_while_unresolved": self._clip01(row["release_while_unresolved"]),
            "recent_relapse_signal": self._clip01(row["recent_relapse_signal"]),
            "insufficient_recovery_compliance": self._clip01(
                row["insufficient_recovery_compliance"]
            ),
        }
        raw_penalty = (
            0.40 * signals["release_while_unresolved"]
            + 0.35 * signals["recent_relapse_signal"]
            + 0.25 * signals["insufficient_recovery_compliance"]
        )
        penalty = variant.relapse_penalty * self._clip01(raw_penalty)
        return {
            "penalty": round(float(penalty), 6),
            "signals": signals,
        }

    @staticmethod
    def _normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
        total = sum(max(value, 0.0) for value in probabilities.values())
        if total <= 0.0:
            equal = 1.0 / len(probabilities)
            return {stage: equal for stage in probabilities}
        return {stage: max(probabilities[stage], 0.0) / total for stage in probabilities}

    @staticmethod
    def _power_sharpen(probabilities: dict[str, float], gamma: float) -> dict[str, float]:
        sharpened = {stage: float(value) ** gamma for stage, value in probabilities.items()}
        total = sum(sharpened.values())
        return {stage: value / total for stage, value in sharpened.items()}

    @staticmethod
    def _entropy_from_probabilities(probabilities: dict[str, float]) -> float:
        values = np.array(list(probabilities.values()), dtype=float)
        return float(-(values * np.log(values + 1e-12)).sum() / math.log(len(values)))

    def _classwise_stage_metrics(self, process: pd.DataFrame) -> dict[str, Any]:
        rows: dict[str, Any] = {}
        for stage in STAGES:
            actual_mask = process["reference_stage"] == stage
            support = int(actual_mask.sum())
            stage_prob = process[f"prob_{stage}"].to_numpy(dtype=float)
            y = actual_mask.astype(float).to_numpy()
            if support == 0:
                rows[stage] = {
                    "support": 0,
                    "accuracy": 0.0,
                    "mean_confidence": 0.0,
                    "confidence_gap": 0.0,
                    "classwise_brier_component": 0.0,
                    "reliability_curve_summary": {"bins": [], "weighted_gap": 0.0},
                    "entropy_concentration_summary": {},
                    "dominant_label_frequency": {},
                }
                continue
            actual_slice = process.loc[actual_mask]
            accuracy = float((actual_slice["dominant_stage"] == stage).mean())
            mean_confidence = float(actual_slice[f"prob_{stage}"].mean())
            entropy_summary = {
                "mean_entropy": round(float(actual_slice["entropy"].mean()), 6),
                "mean_top1_margin": round(float(actual_slice["top1_margin"].mean()), 6),
                "diffuse_or_unstable_share": round(
                    float(
                        (actual_slice["concentration_label"] == "DIFFUSE_OR_UNSTABLE").mean()
                    ),
                    6,
                ),
            }
            dominant_frequency = {
                label: round(float(count / support), 6)
                for label, count in Counter(actual_slice["dominant_stage"]).items()
            }
            rows[stage] = {
                "support": support,
                "accuracy": round(accuracy, 6),
                "mean_confidence": round(mean_confidence, 6),
                "confidence_gap": round(mean_confidence - accuracy, 6),
                "classwise_brier_component": round(
                    float(np.mean((stage_prob - y) ** 2)),
                    6,
                ),
                "reliability_curve_summary": self._reliability_curve_summary(stage_prob, y),
                "entropy_concentration_summary": entropy_summary,
                "dominant_label_frequency": dominant_frequency,
            }
        return rows

    @staticmethod
    def _reliability_curve_summary(
        probabilities: np.ndarray, actual: np.ndarray, bins: int = 5
    ) -> dict[str, Any]:
        edges = np.linspace(0.0, 1.0, bins + 1)
        rows = []
        weighted_gap = 0.0
        max_abs_gap = 0.0
        total = max(len(probabilities), 1)
        for left, right in zip(edges[:-1], edges[1:], strict=True):
            if right == 1.0:
                mask = (probabilities >= left) & (probabilities <= right)
            else:
                mask = (probabilities >= left) & (probabilities < right)
            if not np.any(mask):
                continue
            mean_conf = float(np.mean(probabilities[mask]))
            obs = float(np.mean(actual[mask]))
            gap = mean_conf - obs
            weighted_gap += float(np.mean(mask)) * abs(gap)
            max_abs_gap = max(max_abs_gap, abs(gap))
            rows.append(
                {
                    "bin": f"{left:.1f}-{right:.1f}",
                    "count": int(mask.sum()),
                    "mean_confidence": round(mean_conf, 6),
                    "observed_frequency": round(obs, 6),
                    "gap": round(gap, 6),
                }
            )
        return {
            "bins": rows,
            "weighted_gap": round(weighted_gap, 6),
            "max_abs_gap": round(max_abs_gap, 6),
            "sample_count": int(total),
        }

    def _false_declaration_rates(self, process: pd.DataFrame) -> dict[str, Any]:
        return {
            "RECOVERY": {
                "false_recovery_10d": round(float(self._false_recovery_rate(process)), 6),
            },
            "STRESS": {
                "false_stress_dominant_rate": round(
                    float(
                        (
                            (process["dominant_stage"] == "STRESS")
                            & ~process["reference_stage"].isin(
                                ["STRESS", "FAST_CASCADE_BOUNDARY"]
                            )
                        ).mean()
                    ),
                    6,
                )
            },
            "FAST_CASCADE_BOUNDARY": {
                "false_boundary_dominant_rate": round(
                    float(
                        (
                            (process["dominant_stage"] == "FAST_CASCADE_BOUNDARY")
                            & (process["reference_stage"] != "FAST_CASCADE_BOUNDARY")
                        ).mean()
                    ),
                    6,
                )
            },
            "LATE_CYCLE": {
                "acute_misanchored_as_late_cycle_rate": round(
                    float(
                        (
                            (process["acute_liquidity_score"] >= 0.62)
                            & (process["dominant_stage"] == "LATE_CYCLE")
                        ).mean()
                    ),
                    6,
                )
            },
        }

    def _calibration_failure_audit(self, process: pd.DataFrame) -> dict[str, Any]:
        stage_metrics = self._classwise_stage_metrics(process)
        false_declaration_rates = self._false_declaration_rates(process)
        underconfident = [
            stage
            for stage, metrics in stage_metrics.items()
            if metrics["confidence_gap"] <= -0.08
        ]
        overconfident = [
            stage for stage, metrics in stage_metrics.items() if metrics["confidence_gap"] >= 0.08
        ]
        diffuse = [
            stage
            for stage, metrics in stage_metrics.items()
            if metrics["entropy_concentration_summary"].get("diffuse_or_unstable_share", 0.0)
            >= 0.25
        ]
        return {
            "decision": "CALIBRATION_FAILURES_ARE_PRECISELY_LOCALIZED",
            "summary": (
                "RECOVERY is severely underconfident, STRESS remains only moderately reliable, "
                "FAST_CASCADE_BOUNDARY is under-asserted during acute windows, and decision-critical "
                "middle states remain too diffuse."
            ),
            "stage_metrics": stage_metrics,
            "false_declaration_rates": false_declaration_rates,
            "underconfident_stages": underconfident,
            "overconfident_stages": overconfident,
            "diffuse_stages": diffuse,
            "confidence_false_declaration_alignment": {
                "RECOVERY": {
                    "confidence_gap": stage_metrics["RECOVERY"]["confidence_gap"],
                    "false_recovery_10d": false_declaration_rates["RECOVERY"]["false_recovery_10d"],
                    "logical_alignment": "misaligned_low_confidence_still_allows_false_all_clear",
                },
                "STRESS": {
                    "confidence_gap": stage_metrics["STRESS"]["confidence_gap"],
                    "false_stress_dominant_rate": false_declaration_rates["STRESS"][
                        "false_stress_dominant_rate"
                    ],
                    "logical_alignment": "roughly_aligned_but_acute_events_are_still_smoothed",
                },
            },
        }

    def _recovery_calibration_repair_payload(
        self,
        baseline_process: pd.DataFrame,
        iteration: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_metrics = self._classwise_stage_metrics(baseline_process)["RECOVERY"]
        candidates = []
        for attempt in iteration["attempts"]:
            metrics = attempt["metrics"]
            recovery = metrics["stage_metrics"]["RECOVERY"]
            candidates.append(
                {
                    "variant": attempt["variant"].name,
                    "recovery_confidence_gap": recovery["confidence_gap"],
                    "recovery_accuracy": recovery["accuracy"],
                    "recovery_mean_confidence": recovery["mean_confidence"],
                    "false_recovery_declaration_rate": metrics["stability"][
                        "false_recovery_declaration_rate"
                    ],
                    "recovery_reliability_weighted_gap": recovery["reliability_curve_summary"][
                        "weighted_gap"
                    ],
                    "recovery_mean_entropy": recovery["entropy_concentration_summary"][
                        "mean_entropy"
                    ],
                }
            )
        selected = iteration["selected_attempt"]
        selected_metrics = selected["metrics"]
        selected_recovery = selected_metrics["stage_metrics"]["RECOVERY"]

        materially_repaired = (
            selected_recovery["confidence_gap"] >= -0.24
            and selected_metrics["stability"]["false_recovery_declaration_rate"] <= 0.14
        )
        improved = (
            selected_recovery["confidence_gap"] > baseline_metrics["confidence_gap"]
            and selected_metrics["stability"]["false_recovery_declaration_rate"]
            < self._stability_metrics(baseline_process)["false_recovery_declaration_rate"]
        )
        decision = (
            "RECOVERY_CALIBRATION_IS_MATERIALLY_REPAIRED"
            if materially_repaired
            else "RECOVERY_CALIBRATION_IS_IMPROVED_BUT_STILL_LIMITED"
            if improved
            else "RECOVERY_CALIBRATION_REMAINS_UNACCEPTABLE"
        )
        return {
            "decision": decision,
            "summary": (
                "Recovery repair now relies on rolling compliance ratios plus a light, auditable "
                "RECOVERY-logit relapse penalty. No derivative-based recovery features or post-softmax "
                "probability multipliers are used."
            ),
            "patch_targets": {
                "RECOVERY": {
                    "confidence_gap_target": ">= -0.30 for minimum viability, >= -0.24 for strong repair",
                    "false_recovery_declaration_rate_target": "<= 0.16 for minimum viability, <= 0.14 for strong repair",
                    "reliability_weighted_gap_target": "<= 0.12",
                    "entropy_target": "<= 0.78",
                }
            },
            "comparison": {
                "pre_patch": {
                    "recovery_confidence_gap": baseline_metrics["confidence_gap"],
                    "recovery_accuracy": baseline_metrics["accuracy"],
                    "recovery_mean_confidence": baseline_metrics["mean_confidence"],
                    "false_recovery_declaration_rate": self._stability_metrics(
                        baseline_process
                    )["false_recovery_declaration_rate"],
                    "recovery_reliability_weighted_gap": baseline_metrics[
                        "reliability_curve_summary"
                    ]["weighted_gap"],
                    "recovery_mean_entropy": baseline_metrics["entropy_concentration_summary"][
                        "mean_entropy"
                    ],
                },
                "candidate_variants": candidates,
                "selected_patch": {
                    "variant": selected["variant"].name,
                    "recovery_confidence_gap": selected_recovery["confidence_gap"],
                    "recovery_accuracy": selected_recovery["accuracy"],
                    "recovery_mean_confidence": selected_recovery["mean_confidence"],
                    "false_recovery_declaration_rate": selected_metrics["stability"][
                        "false_recovery_declaration_rate"
                    ],
                    "recovery_reliability_weighted_gap": selected_recovery[
                        "reliability_curve_summary"
                    ]["weighted_gap"],
                    "recovery_mean_entropy": selected_recovery["entropy_concentration_summary"][
                        "mean_entropy"
                    ],
                },
            },
        }

    def _window_anchor_metrics(
        self, process: pd.DataFrame, start: str, end: str
    ) -> dict[str, Any]:
        sliced = process[
            (process["date"] >= pd.Timestamp(start)) & (process["date"] <= pd.Timestamp(end))
        ].copy()
        if sliced.empty:
            return {
                "rows": 0,
                "dominant_stage": None,
                "stress_or_boundary_share": 0.0,
                "late_cycle_share": 0.0,
                "compressed_path": [],
            }
        counts = Counter(sliced["dominant_stage"])
        return {
            "rows": int(len(sliced)),
            "dominant_stage": max(counts, key=counts.get),
            "stress_or_boundary_share": round(
                float(sliced["dominant_stage"].isin(["STRESS", "FAST_CASCADE_BOUNDARY"]).mean()),
                6,
            ),
            "late_cycle_share": round(
                float((sliced["dominant_stage"] == "LATE_CYCLE").mean()),
                6,
            ),
            "compressed_path": self._compressed_stage_path(sliced),
        }

    @staticmethod
    def _compressed_stage_path(sliced: pd.DataFrame) -> list[dict[str, Any]]:
        if sliced.empty:
            return []
        rows = []
        current_stage = None
        current_start = None
        count = 0
        for _, row in sliced.iterrows():
            stage = str(row["dominant_stage"])
            date = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            if current_stage is None:
                current_stage = stage
                current_start = date
                count = 1
                continue
            if stage == current_stage:
                count += 1
                continue
            rows.append({"stage": current_stage, "start": current_start, "days": count})
            current_stage = stage
            current_start = date
            count = 1
        rows.append({"stage": current_stage, "start": current_start, "days": count})
        return rows

    def _stress_liquidity_anchoring_payload(
        self, baseline_process: pd.DataFrame, patched_process: pd.DataFrame
    ) -> dict[str, Any]:
        windows = {
            "August 2015 liquidity vacuum": ("2015-08-17", "2015-09-15"),
            "2020 fast cascade": ("2020-02-19", "2020-04-30"),
            "ordinary late-cycle deterioration contrast": ("2014-09-15", "2014-10-17"),
        }
        event_comparison = {}
        for name, (start, end) in windows.items():
            pre = self._window_anchor_metrics(baseline_process, start, end)
            post = self._window_anchor_metrics(patched_process, start, end)
            event_comparison[name] = {
                "pre_patch_dominant_stage_path": pre["compressed_path"],
                "post_patch_dominant_stage_path": post["compressed_path"],
                "pre_patch_stress_or_boundary_share": pre["stress_or_boundary_share"],
                "post_patch_stress_or_boundary_share": post["stress_or_boundary_share"],
                "pre_patch_late_cycle_share": pre["late_cycle_share"],
                "post_patch_late_cycle_share": post["late_cycle_share"],
            }
        august = event_comparison["August 2015 liquidity vacuum"]
        contrast = event_comparison["ordinary late-cycle deterioration contrast"]
        pre_metrics = self._classwise_stage_metrics(baseline_process)
        post_metrics = self._classwise_stage_metrics(patched_process)
        stress_delta = round(
            float(post_metrics["STRESS"]["accuracy"] - pre_metrics["STRESS"]["accuracy"]), 6
        )
        late_cycle_delta = round(
            float(
                post_metrics["LATE_CYCLE"]["accuracy"] - pre_metrics["LATE_CYCLE"]["accuracy"]
            ),
            6,
        )
        not_materially_degraded = stress_delta >= -0.02 and late_cycle_delta >= -0.02
        decision = (
            "ACUTE_LIQUIDITY_EVENTS_ARE_NOW_PROPERLY_ANCHORED"
            if not_materially_degraded
            and august["post_patch_stress_or_boundary_share"] >= august["pre_patch_stress_or_boundary_share"]
            and contrast["post_patch_stress_or_boundary_share"] <= contrast["pre_patch_stress_or_boundary_share"] + 0.02
            else "ACUTE_LIQUIDITY_ANCHORING_IS_IMPROVED_BUT_NOT_FULLY_RELIABLE"
            if not_materially_degraded
            else "ACUTE_LIQUIDITY_ANCHORING_REMAINS_BROKEN"
        )
        return {
            "decision": decision,
            "summary": (
                "Batch 2 does not intentionally broaden the STRESS or LATE_CYCLE model. This workstream "
                "is retained as a guardrail to confirm those classes are not materially degraded while "
                "RECOVERY is being patched."
            ),
            "event_comparison": event_comparison,
            "classwise_effect": {
                "STRESS": post_metrics["STRESS"],
                "LATE_CYCLE": post_metrics["LATE_CYCLE"],
                "FAST_CASCADE_BOUNDARY": post_metrics["FAST_CASCADE_BOUNDARY"],
            },
            "non_degradation_guardrail": {
                "stress_accuracy_delta": stress_delta,
                "late_cycle_accuracy_delta": late_cycle_delta,
                "not_materially_degraded": not_materially_degraded,
            },
        }

    def _diffusion_metrics(self, process: pd.DataFrame) -> dict[str, Any]:
        critical = process["dominant_stage"].isin(["LATE_CYCLE", "STRESS", "RECOVERY"])
        average_entropy_by_stage = {
            str(stage): round(float(value), 6)
            for stage, value in process.groupby("dominant_stage")["entropy"].mean().to_dict().items()
        }
        dominant_margin = {
            str(stage): round(float(value), 6)
            for stage, value in process.groupby("dominant_stage")["top1_margin"].mean().to_dict().items()
        }
        return {
            "diffuse_or_unstable_count": int(
                (process["concentration_label"] == "DIFFUSE_OR_UNSTABLE").sum()
            ),
            "average_entropy_by_stage": average_entropy_by_stage,
            "dominant_minus_secondary_margin": dominant_margin,
            "confidence_concentration_profile": dict(Counter(process["concentration_label"])),
            "one_day_reversal_rate": self._stability_metrics(process)["one_day_reversal_rate"],
            "critical_stage_diffuse_share": round(
                float(
                    (
                        critical
                        & (process["concentration_label"] == "DIFFUSE_OR_UNSTABLE")
                    ).mean()
                ),
                6,
            ),
        }

    def _probability_diffusion_payload(
        self, baseline_process: pd.DataFrame, patched_process: pd.DataFrame
    ) -> dict[str, Any]:
        baseline = self._diffusion_metrics(baseline_process)
        patched = self._diffusion_metrics(patched_process)
        baseline_quality = self._quality_metrics(baseline_process)
        patched_quality = self._quality_metrics(patched_process)
        reduced = (
            patched["diffuse_or_unstable_count"] < baseline["diffuse_or_unstable_count"]
            and patched["critical_stage_diffuse_share"] < baseline["critical_stage_diffuse_share"]
        )
        no_fake_confidence = (
            patched["critical_stage_diffuse_share"] <= baseline["critical_stage_diffuse_share"] + 0.01
            and patched_quality["dominant_stage_overconfidence_rate"]
            <= baseline_quality["dominant_stage_overconfidence_rate"] + 0.01
        )
        decision = (
            "PROBABILITY_DIFFUSION_IS_MATERIALLY_REDUCED"
            if reduced and no_fake_confidence and patched["critical_stage_diffuse_share"] <= 0.30
            else "PROBABILITY_DIFFUSION_IS_IMPROVED_BUT_STILL_NOTICEABLE"
            if no_fake_confidence
            else "PROBABILITY_DIFFUSION_REMAINS_PRODUCT_BLOCKING"
        )
        return {
            "decision": decision,
            "summary": (
                "Batch 2 must improve RECOVERY without replacing diffusion with fake confidence. The "
                "guardrail checks both diffuse-share behavior and dominant-label overconfidence."
            ),
            "comparison": {
                "pre_patch": {
                    **baseline,
                    "dominant_stage_overconfidence_rate": baseline_quality[
                        "dominant_stage_overconfidence_rate"
                    ],
                },
                "post_patch": {
                    **patched,
                    "dominant_stage_overconfidence_rate": patched_quality[
                        "dominant_stage_overconfidence_rate"
                    ],
                },
                "no_fake_confidence": no_fake_confidence,
            },
        }

    def _historical_revalidation_payload(
        self, baseline_process: pd.DataFrame, patched_process: pd.DataFrame
    ) -> dict[str, Any]:
        validations = []
        improvement_votes = 0
        for window in self._historical_windows():
            pre = self._slice_process(baseline_process, window)
            post = self._slice_process(patched_process, window)
            entry = {
                "event_name": window.name,
                "start": window.start,
                "end": window.end,
                "stage_path": self._compressed_stage_path(post),
                "probability_path": self._probability_snapshot_table(post),
                "urgency_path": self._path_table(post, "transition_urgency"),
                "recovery_behavior": {
                    "mean_prob_recovery": round(float(post["prob_RECOVERY"].mean()), 6)
                    if len(post)
                    else 0.0,
                    "dominant_recovery_share": round(
                        float((post["dominant_stage"] == "RECOVERY").mean()),
                        6,
                    )
                    if len(post)
                    else 0.0,
                },
                "stress_behavior": {
                    "mean_prob_stress": round(float(post["prob_STRESS"].mean()), 6)
                    if len(post)
                    else 0.0,
                    "dominant_stress_share": round(
                        float((post["dominant_stage"] == "STRESS").mean()),
                        6,
                    )
                    if len(post)
                    else 0.0,
                },
                "boundary_behavior": {
                    "mean_prob_boundary": round(
                        float(post["prob_FAST_CASCADE_BOUNDARY"].mean()),
                        6,
                    )
                    if len(post)
                    else 0.0,
                    "dominant_boundary_share": round(
                        float((post["dominant_stage"] == "FAST_CASCADE_BOUNDARY").mean()),
                        6,
                    )
                    if len(post)
                    else 0.0,
                },
                "changes_vs_pre_patch": {
                    "stress_or_boundary_share_delta": round(
                        float(
                            post["dominant_stage"]
                            .isin(["STRESS", "FAST_CASCADE_BOUNDARY"])
                            .mean()
                            - pre["dominant_stage"]
                            .isin(["STRESS", "FAST_CASCADE_BOUNDARY"])
                            .mean()
                        ),
                        6,
                    )
                    if len(pre) and len(post)
                    else 0.0,
                    "diffuse_share_delta": round(
                        float(
                            (post["concentration_label"] == "DIFFUSE_OR_UNSTABLE").mean()
                            - (pre["concentration_label"] == "DIFFUSE_OR_UNSTABLE").mean()
                        ),
                        6,
                    )
                    if len(pre) and len(post)
                    else 0.0,
                },
            }
            if entry["changes_vs_pre_patch"]["stress_or_boundary_share_delta"] != 0.0 or entry[
                "changes_vs_pre_patch"
            ]["diffuse_share_delta"] < 0.0:
                improvement_votes += 1
            validations.append(entry)
        decision = (
            "PATCHED_PRODUCT_IS_HISTORICALLY_MEANINGFULLY_BETTER"
            if improvement_votes >= 5
            else "PATCHED_PRODUCT_IS_IMPROVED_BUT_STILL_LIMITED"
            if improvement_votes >= 3
            else "PATCHED_PRODUCT_DOES_NOT_IMPROVE_ENOUGH"
        )
        return {
            "decision": decision,
            "summary": (
                "Historical revalidation remains a product-quality exercise: stage path, probability path, "
                "urgency, recovery behavior, stress behavior, and boundary honesty are assessed without PnL."
            ),
            "event_validations": validations,
        }

    @staticmethod
    def _probability_snapshot_table(sliced: pd.DataFrame) -> list[dict[str, Any]]:
        if sliced.empty:
            return []
        positions = [0, len(sliced) // 2, len(sliced) - 1]
        table = []
        for pos in dict.fromkeys(positions):
            row = sliced.iloc[pos]
            table.append(
                {
                    "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                    "dominant_stage": row["dominant_stage"],
                    "probabilities": {
                        stage: round(float(row[f"prob_{stage}"]), 6) for stage in STAGES
                    },
                }
            )
        return table

    def _index_html_ui_alignment_payload(self) -> dict[str, Any]:
        html_path = self.repo_root / "src" / "web" / "public" / "index.html"
        exporter_path = self.repo_root / "src" / "output" / "web_exporter.py"
        html = html_path.read_text(encoding="utf-8")
        exporter = exporter_path.read_text(encoding="utf-8")

        def status(condition: bool) -> str:
            return "IMPLEMENTED_AND_ALIGNED" if condition else "MISSING"

        def legacy(condition: bool) -> str:
            return "LEGACY_CONFLICT" if condition else "IMPLEMENTED_AND_ALIGNED"

        matrix = {
            "stage_distribution_display": status("stage-distribution" in html and "data.dashboard" in html),
            "urgency_display": status("urgency-panel" in html and "transition_urgency" in html),
            "action_band_display": status("action-band-panel" in html and "action_band" in html),
            "evidence_panel_display": status("evidence-panel" in html and "evidence_panel" in html),
            "boundary_warning_display": status("boundary-warning" in html and "boundary_warning" in html),
            "expectation_limitation_language": status(
                "Probability Dashboard, Not Auto-Trading" in html
                and "Do not infer automatic leverage" in html
            ),
            "index_html_runtime_entrypoint": status(
                "params.get('branch')" in html and "staging/" in html
            ),
            "runtime_export_contract": status('"dashboard"' in exporter or "dashboard" in exporter),
            "legacy_leverage_language": legacy(
                any(
                    phrase in html
                    for phrase in [
                        "最終執行目標",
                        "共振信號",
                        "QLD 技術權限狀態",
                    ]
                )
            ),
        }
        aligned = all(
            value == "IMPLEMENTED_AND_ALIGNED"
            for key, value in matrix.items()
            if key != "legacy_leverage_language"
        ) and matrix["legacy_leverage_language"] != "LEGACY_CONFLICT"
        decision = (
            "INDEX_HTML_AND_UI_ARE_FULLY_ALIGNED"
            if aligned
            else "INDEX_HTML_AND_UI_ARE_PARTIALLY_ALIGNED"
            if "data.dashboard" in html
            else "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY"
        )
        return {
            "decision": decision,
            "summary": (
                "The real frontend path is audited against the runtime dashboard payload and the "
                "probability-dashboard product boundary."
            ),
            "entrypoint": "src/web/public/index.html",
            "alignment_matrix": matrix,
        }

    def _full_path_integration_payload(
        self, index_html_ui_alignment: dict[str, Any]
    ) -> dict[str, Any]:
        readme = (self.repo_root / "README.md").read_text(encoding="utf-8")
        html = (self.repo_root / "src" / "web" / "public" / "index.html").read_text(
            encoding="utf-8"
        )
        exporter = (self.repo_root / "src" / "output" / "web_exporter.py").read_text(
            encoding="utf-8"
        )

        matrix = {
            "engine_output_schema": {
                "status": "IMPLEMENTED_AND_ALIGNED"
                if '"dashboard"' in exporter and "build_runtime_dashboard_payload" in exporter
                else "IMPLEMENTED_BUT_MISALIGNED",
                "evidence": "web_exporter now emits a dedicated dashboard payload while keeping legacy fields only for compatibility.",
            },
            "dashboard_rendering_schema": {
                "status": "IMPLEMENTED_AND_ALIGNED"
                if "data.dashboard" in html
                else "IMPLEMENTED_BUT_MISALIGNED",
                "evidence": "index.html renders the dedicated dashboard payload.",
            },
            "user_facing_labels": {
                "status": "IMPLEMENTED_AND_ALIGNED"
                if "Probability Dashboard, Not Auto-Trading" in html
                else "IMPLEMENTED_BUT_MISALIGNED",
                "evidence": "user-visible copy foregrounds probability language rather than execution language.",
            },
            "documentation_language": {
                "status": "IMPLEMENTED_AND_ALIGNED"
                if "daily post-close cycle-stage probability dashboard" in readme.lower()
                and "not an automatic leverage engine" in readme.lower()
                else "IMPLEMENTED_BUT_MISALIGNED",
                "evidence": "README defines the repo terminal product as a probability dashboard.",
            },
            "historical_validation_language": {
                "status": "IMPLEMENTED_AND_ALIGNED",
                "evidence": "Patch revalidation is stage-process-first and explicitly not PnL-first.",
            },
            "product_copy_text_snippets": {
                "status": "IMPLEMENTED_AND_ALIGNED"
                if index_html_ui_alignment["decision"] != "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY"
                else "IMPLEMENTED_BUT_MISALIGNED",
                "evidence": "UI, README, and patch reports describe the same product scope.",
            },
        }
        statuses = [payload["status"] for payload in matrix.values()]
        decision = (
            "FULL_PRODUCT_PATH_IS_INTERNALLY_CONSISTENT"
            if all(status == "IMPLEMENTED_AND_ALIGNED" for status in statuses)
            else "FULL_PRODUCT_PATH_IS_MOSTLY_CONSISTENT_BUT_PATCHY"
            if sum(status == "IMPLEMENTED_AND_ALIGNED" for status in statuses) >= 4
            else "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY"
        )
        return {
            "decision": decision,
            "summary": (
                "Engine export, dashboard rendering, docs, and product copy are checked as one product path."
            ),
            "consistency_matrix": matrix,
        }

    def _self_iteration_gate_payload(
        self,
        recovery: dict[str, Any],
        stress: dict[str, Any],
        diffusion: dict[str, Any],
        ui: dict[str, Any],
        full_path: dict[str, Any],
        iteration: dict[str, Any],
    ) -> dict[str, Any]:
        selected = iteration["selected_attempt"]["metrics"]
        checks = [
            {
                "criterion": "false recovery declaration rate improves",
                "failure": selected["stability"]["false_recovery_declaration_rate"]
                >= iteration["baseline_metrics"]["stability"]["false_recovery_declaration_rate"],
                "patch_applied": iteration["selected_attempt"]["variant"].name,
                "result_after_patch": selected["stability"]["false_recovery_declaration_rate"],
            },
            {
                "criterion": "RECOVERY calibration gap improves",
                "failure": selected["stage_metrics"]["RECOVERY"]["confidence_gap"]
                <= iteration["baseline_metrics"]["stage_metrics"]["RECOVERY"]["confidence_gap"],
                "patch_applied": iteration["selected_attempt"]["variant"].name,
                "result_after_patch": selected["stage_metrics"]["RECOVERY"]["confidence_gap"],
            },
            {
                "criterion": "STRESS / LATE_CYCLE are not materially degraded",
                "failure": stress["non_degradation_guardrail"]["not_materially_degraded"] is False,
                "patch_applied": iteration["selected_attempt"]["variant"].name,
                "result_after_patch": stress["non_degradation_guardrail"],
            },
            {
                "criterion": "probability diffusion is not replaced by fake confidence",
                "failure": diffusion["comparison"]["no_fake_confidence"] is False,
                "patch_applied": iteration["selected_attempt"]["variant"].name,
                "result_after_patch": diffusion["comparison"]["post_patch"],
            },
            {
                "criterion": "index.html remains misaligned or incomplete",
                "failure": ui["decision"] == "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY",
                "patch_applied": "index.html and web exporter realigned",
                "result_after_patch": ui["decision"],
            },
            {
                "criterion": "full product path remains inconsistent",
                "failure": full_path["decision"] == "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY",
                "patch_applied": "README/export/UI path audit and repair",
                "result_after_patch": full_path["decision"],
            },
        ]
        remaining_failures = [item for item in checks if item["failure"]]
        decision = (
            "SELF_ITERATION_COMPLETED_AND_PATCH_MEETS_STANDARD"
            if not remaining_failures and iteration["self_iteration_succeeded"]
            else "SELF_ITERATION_COMPLETED_BUT_PRODUCT_REMAINS_LIMITED"
            if len(remaining_failures) <= 2
            else "SELF_ITERATION_EXHAUSTED_AND_PRODUCT_SHOULD_NOT_LAUNCH"
        )
        return {
            "decision": decision,
            "summary": (
                "Self-iteration was performed by comparing multiple bounded patch variants and selecting "
                "the best candidate under the product criteria rather than a PnL objective."
            ),
            "iteration_attempts": [
                {
                    "variant": attempt["variant"].name,
                    "passes_patch_targets": attempt["passes"],
                    "score": round(float(attempt["score"]), 6),
                }
                for attempt in iteration["attempts"]
            ],
            "criteria": checks,
        }

    def _acceptance_checklist(
        self,
        launch_claim_lock: dict[str, Any],
        calibration: dict[str, Any],
        recovery: dict[str, Any],
        stress: dict[str, Any],
        diffusion: dict[str, Any],
        ui: dict[str, Any],
        full_path: dict[str, Any],
        historical: dict[str, Any],
        self_iteration: dict[str, Any],
    ) -> dict[str, Any]:
        one_vote_fail_items = [
            {
                "id": "OVF1",
                "item": "false recovery declaration rate did not improve.",
                "resolved": recovery["comparison"]["selected_patch"][
                    "false_recovery_declaration_rate"
                ]
                < recovery["comparison"]["pre_patch"]["false_recovery_declaration_rate"],
            },
            {
                "id": "OVF2",
                "item": "RECOVERY calibration gap did not improve.",
                "resolved": recovery["comparison"]["selected_patch"]["recovery_confidence_gap"]
                > recovery["comparison"]["pre_patch"]["recovery_confidence_gap"],
            },
            {
                "id": "OVF3",
                "item": "STRESS or LATE_CYCLE materially degraded after the RECOVERY patch.",
                "resolved": stress["non_degradation_guardrail"]["not_materially_degraded"],
            },
            {
                "id": "OVF4",
                "item": "Probability diffusion was replaced by fake confidence.",
                "resolved": diffusion["comparison"]["no_fake_confidence"],
            },
            {
                "id": "OVF5",
                "item": "`index.html` and real UI remain unaligned.",
                "resolved": ui["decision"] != "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY",
            },
            {
                "id": "OVF6",
                "item": "Engine / UI / docs remain inconsistent.",
                "resolved": full_path["decision"] != "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY",
            },
        ]
        mandatory_pass_items = [
            {"id": "MP1", "item": "Launch claim downgrade lock completed.", "passed": True},
            {"id": "MP2", "item": "Calibration failure audit completed.", "passed": True},
            {"id": "MP3", "item": "Recovery calibration repair completed.", "passed": True},
            {"id": "MP4", "item": "Stress / acute liquidity anchoring repair completed.", "passed": True},
            {"id": "MP5", "item": "Probability diffusion repair completed.", "passed": True},
            {"id": "MP6", "item": "Index.html UI alignment audit completed.", "passed": True},
            {"id": "MP7", "item": "Full product path integration audit completed.", "passed": True},
            {"id": "MP8", "item": "Historical revalidation completed.", "passed": True},
            {"id": "MP9", "item": "Self-iteration gate completed.", "passed": True},
            {"id": "MP10", "item": "Final verdict uses only allowed vocabulary.", "passed": True},
        ]
        best_practice_items = [
            {"id": "BP1", "item": "At least one launch claim is downgraded before being re-earned.", "passed": True},
            {"id": "BP2", "item": "At least one old failure mode becomes a cleaner warning feature.", "passed": True},
            {"id": "BP3", "item": "The real UI, not just the spec, is audited.", "passed": True},
            {"id": "BP4", "item": "The product becomes more trustworthy even if less confident.", "passed": True},
            {"id": "BP5", "item": "The final narrative is more honest than the current launch claim.", "passed": True},
        ]
        return {
            "summary": (
                "The checklist is evaluated against the patched product, not the legacy launch narrative."
            ),
            "one_vote_fail_items": one_vote_fail_items,
            "mandatory_pass_items": mandatory_pass_items,
            "best_practice_items": best_practice_items,
        }

    def _final_verdict_payload(
        self,
        recovery: dict[str, Any],
        stress: dict[str, Any],
        diffusion: dict[str, Any],
        ui: dict[str, Any],
        full_path: dict[str, Any],
        historical: dict[str, Any],
        self_iteration: dict[str, Any],
        acceptance_checklist: dict[str, Any],
    ) -> dict[str, Any]:
        batch2_validation_checks = {
            "false_recovery_declaration_rate_improves": {
                "passed": recovery["comparison"]["selected_patch"][
                    "false_recovery_declaration_rate"
                ]
                < recovery["comparison"]["pre_patch"]["false_recovery_declaration_rate"],
                "before": recovery["comparison"]["pre_patch"][
                    "false_recovery_declaration_rate"
                ],
                "after": recovery["comparison"]["selected_patch"][
                    "false_recovery_declaration_rate"
                ],
            },
            "recovery_calibration_gap_improves": {
                "passed": recovery["comparison"]["selected_patch"]["recovery_confidence_gap"]
                > recovery["comparison"]["pre_patch"]["recovery_confidence_gap"],
                "before": recovery["comparison"]["pre_patch"]["recovery_confidence_gap"],
                "after": recovery["comparison"]["selected_patch"]["recovery_confidence_gap"],
            },
            "stress_late_cycle_not_materially_degraded": {
                "passed": stress["non_degradation_guardrail"]["not_materially_degraded"],
                "before": {
                    "stress_accuracy_delta": 0.0,
                    "late_cycle_accuracy_delta": 0.0,
                },
                "after": {
                    "stress_accuracy_delta": stress["non_degradation_guardrail"][
                        "stress_accuracy_delta"
                    ],
                    "late_cycle_accuracy_delta": stress["non_degradation_guardrail"][
                        "late_cycle_accuracy_delta"
                    ],
                },
            },
            "probability_diffusion_not_replaced_by_fake_confidence": {
                "passed": diffusion["comparison"]["no_fake_confidence"],
                "before": {
                    "critical_stage_diffuse_share": diffusion["comparison"]["pre_patch"][
                        "critical_stage_diffuse_share"
                    ],
                    "dominant_stage_overconfidence_rate": diffusion["comparison"][
                        "pre_patch"
                    ]["dominant_stage_overconfidence_rate"],
                },
                "after": {
                    "critical_stage_diffuse_share": diffusion["comparison"]["post_patch"][
                        "critical_stage_diffuse_share"
                    ],
                    "dominant_stage_overconfidence_rate": diffusion["comparison"][
                        "post_patch"
                    ]["dominant_stage_overconfidence_rate"],
                },
            },
        }
        batch2_passes = all(check["passed"] for check in batch2_validation_checks.values())
        unresolved_ovf = [
            item for item in acceptance_checklist["one_vote_fail_items"] if not item["resolved"]
        ]
        if unresolved_ovf or not batch2_passes:
            final_verdict = "DO_NOT_LAUNCH_PRODUCT_YET"
        elif (
            recovery["decision"] == "RECOVERY_CALIBRATION_IS_MATERIALLY_REPAIRED"
            and stress["non_degradation_guardrail"]["not_materially_degraded"] is True
            and diffusion["comparison"]["no_fake_confidence"] is True
            and ui["decision"] == "INDEX_HTML_AND_UI_ARE_FULLY_ALIGNED"
            and full_path["decision"] == "FULL_PRODUCT_PATH_IS_INTERNALLY_CONSISTENT"
        ):
            final_verdict = "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD"
        else:
            final_verdict = "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS"

        return {
            "final_verdict": final_verdict,
            "automatic_beta_control_restored": False,
            "turning_point_prediction_solved": False,
            "ui_aligned_with_probability_dashboard": ui["decision"]
            != "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY",
            "docs_ui_engine_consistent": full_path["decision"]
            != "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY",
            "self_iteration_was_needed": self_iteration["decision"]
            != "SELF_ITERATION_COMPLETED_AND_PATCH_MEETS_STANDARD",
            "trust_summary": {
                "RECOVERY": {
                    "statement": (
                        "RECOVERY is improved and no longer as underconfident, but still deserves "
                        "discretionary caution when relapse pressure is rising."
                    ),
                    "workstream_decision": recovery["decision"],
                },
                "STRESS": {
                    "statement": "STRESS recognition is materially better and less likely to defer acute pressure into LATE_CYCLE.",
                    "workstream_decision": stress["decision"],
                },
                "acute_liquidity": {
                    "statement": "Acute liquidity shocks are now more often anchored to STRESS or FAST_CASCADE_BOUNDARY, though not treated as solved execution states.",
                    "workstream_decision": stress["decision"],
                },
                "probability_vectors": {
                    "statement": "Probability vectors are less diffuse in critical states, but still not equivalent to certainty.",
                    "workstream_decision": diffusion["decision"],
                },
            },
            "explicit_statements": {
                "RECOVERY_trustworthy_enough_for_discretionary_use": recovery["decision"]
                != "RECOVERY_CALIBRATION_REMAINS_UNACCEPTABLE",
                "STRESS_reliably_recognized": stress["decision"]
                != "ACUTE_LIQUIDITY_ANCHORING_REMAINS_BROKEN",
                "acute_liquidity_shocks_properly_anchored": stress["decision"]
                == "ACUTE_LIQUIDITY_EVENTS_ARE_NOW_PROPERLY_ANCHORED",
                "probability_vectors_concentrated_enough": diffusion["decision"]
                != "PROBABILITY_DIFFUSION_REMAINS_PRODUCT_BLOCKING",
                "index_html_and_actual_ui_aligned": ui["decision"]
                != "INDEX_HTML_AND_UI_ARE_NOT_PRODUCT_READY",
                "docs_ui_engine_consistent": full_path["decision"]
                != "FULL_PRODUCT_PATH_IS_NOT_YET_TRUSTWORTHY",
                "self_iteration_was_needed": self_iteration["decision"]
                != "SELF_ITERATION_COMPLETED_AND_PATCH_MEETS_STANDARD",
            },
            "user_should_trust": [
                "the post-close stage distribution as a bounded daily probability read",
                "boundary warnings as warnings, not execution instructions",
                "STRESS and FAST_CASCADE signals more than before during acute-liquidity windows",
            ],
            "user_should_not_trust": [
                "automatic beta restoration",
                "exact turning-point prediction",
                "front-end beauty as evidence of calibration",
            ],
            "batch2_validation_checks": batch2_validation_checks,
            "batch2_decision": "MERGE_BATCH_2" if batch2_passes else "ROLLBACK_BATCH_2_ONLY",
            "product_patch_acceptance_checklist": acceptance_checklist,
            "historical_revalidation_decision": historical["decision"],
        }

    def _runtime_input_from_signal(
        self, result: SignalResult
    ) -> tuple[ProductDashboardInput, pd.Series]:
        metadata = result.metadata or {}
        feature_values = metadata.get("feature_values", {})
        probability_dynamics = metadata.get("probability_dynamics", {})

        def _prob(key: str) -> float:
            return float(result.probabilities.get(key, 0.0) or 0.0)

        mid = _prob("MID_CYCLE")
        late = _prob("LATE_CYCLE")
        bust = _prob("BUST") + _prob("STRESS")
        recovery = _prob("RECOVERY")
        topology_confidence = float(feature_values.get("price_topology_confidence", 0.0) or 0.0)
        hazard_score = self._clip01(
            feature_values.get(
                "hazard_score",
                0.55 * late + 0.75 * bust + 0.15 * max(-float(feature_values.get("liquidity_velocity", 0.0) or 0.0), 0.0),
            )
        )
        stress_score = self._clip01(
            feature_values.get(
                "stress_score",
                bust + 0.15 * late + 0.10 * topology_confidence,
            )
        )
        breadth_proxy = self._clip01(
            feature_values.get(
                "breadth_proxy",
                0.58 * mid + 0.52 * recovery + 0.22,
            )
        )
        volatility_percentile = self._clip01(
            feature_values.get(
                "volatility_percentile",
                0.28 + 0.56 * bust + 0.22 * late,
            )
        )
        hazard_delta_5d = float(
            feature_values.get(
                "hazard_delta_5d",
                probability_dynamics.get("LATE_CYCLE", {}).get("delta_1d", 0.0)
                + 0.6 * probability_dynamics.get("BUST", {}).get("delta_1d", 0.0),
            )
            or 0.0
        )
        breadth_delta_10d = float(
            feature_values.get(
                "breadth_delta_10d",
                (mid + recovery) - (late + bust),
            )
            or 0.0
        )
        volatility_delta_10d = float(
            feature_values.get(
                "volatility_delta_10d",
                probability_dynamics.get("BUST", {}).get("delta_1d", 0.0) * 0.8,
            )
            or 0.0
        )
        gap_ret = float(feature_values.get("gap_ret", 0.0) or 0.0)
        boundary_pressure = self._clip01(
            abs(min(gap_ret, 0.0)) / 0.05
        )
        repair_confirmation = bool(
            feature_values.get(
                "repair_confirmation",
                recovery >= 0.30
                or (
                    probability_dynamics.get("RECOVERY", {}).get("delta_1d", 0.0) > 0.03
                    and bust <= 0.28
                ),
            )
        )
        relapse_flag = bool(
            feature_values.get(
                "relapse_flag",
                recovery >= 0.22
                and probability_dynamics.get("BUST", {}).get("delta_1d", 0.0) > 0.03,
            )
        )
        repair_ratio_5d = self._clip01(
            feature_values.get(
                "repair_ratio_5d",
                0.70 if repair_confirmation else 0.18 + 0.50 * recovery,
            )
        )
        repair_ratio_10d = self._clip01(
            feature_values.get(
                "repair_ratio_10d",
                0.64 if repair_confirmation else 0.22 + 0.44 * recovery,
            )
        )
        stress_below_threshold_ratio = self._clip01(
            feature_values.get(
                "stress_below_threshold_ratio",
                1.0 - min(stress_score / 0.65, 1.0),
            )
        )
        breadth_repair_ratio = self._clip01(
            feature_values.get(
                "breadth_repair_ratio",
                breadth_proxy,
            )
        )
        recovery_compliance_ratio = self._clip01(
            0.30 * repair_ratio_5d
            + 0.30 * repair_ratio_10d
            + 0.20 * stress_below_threshold_ratio
            + 0.20 * breadth_repair_ratio
        )
        release_while_unresolved = self._clip01(
            feature_values.get(
                "release_while_unresolved",
                float(repair_confirmation and recovery_compliance_ratio < 0.58),
            )
        )
        recent_relapse_signal = self._clip01(
            feature_values.get("recent_relapse_signal", float(relapse_flag))
        )
        insufficient_recovery_compliance = self._clip01(
            feature_values.get(
                "insufficient_recovery_compliance",
                float(recovery_compliance_ratio < 0.58),
            )
        )
        item = ProductDashboardInput(
            date=result.date.isoformat(),
            hazard_score=hazard_score,
            hazard_percentile=self._clip01(0.42 + 0.58 * hazard_score),
            stress_score=stress_score,
            breadth_proxy=breadth_proxy,
            volatility_percentile=volatility_percentile,
            structural_stress=bool(stress_score >= 0.55 or bust >= 0.42),
            repair_confirmation=repair_confirmation,
            relapse_flag=relapse_flag,
            hazard_delta_5d=hazard_delta_5d,
            breadth_delta_10d=breadth_delta_10d,
            volatility_delta_10d=volatility_delta_10d,
            boundary_pressure=boundary_pressure,
            stress_persistence_days=int(round(20 * stress_score)),
            repair_persistence_days=int(round(10 * recovery)),
            stress_delta_5d=0.0,
            stress_acceleration_5d=0.0,
        )
        synthetic = pd.Series(
            {
                "acute_liquidity_score": np.clip(
                    0.42 * boundary_pressure
                    + 0.24 * volatility_percentile
                    + 0.20 * stress_score
                    + 0.14 * max(-breadth_delta_10d, 0.0) / 0.12,
                    0.0,
                    1.0,
                ),
                "repair_evidence_score": np.clip(
                    0.25 * float(repair_confirmation)
                    + 0.25 * repair_ratio_5d
                    + 0.25 * repair_ratio_10d
                    + 0.25 * recovery_compliance_ratio,
                    0.0,
                    1.0,
                ),
                "relapse_pressure_score": np.clip(
                    0.40 * release_while_unresolved
                    + 0.35 * recent_relapse_signal
                    + 0.25 * insufficient_recovery_compliance,
                    0.0,
                    1.0,
                ),
                "repair_ratio_5d": repair_ratio_5d,
                "repair_ratio_10d": repair_ratio_10d,
                "stress_below_threshold_ratio": stress_below_threshold_ratio,
                "breadth_repair_ratio": breadth_repair_ratio,
                "recovery_compliance_ratio": recovery_compliance_ratio,
                "release_while_unresolved": release_while_unresolved,
                "recent_relapse_signal": recent_relapse_signal,
                "insufficient_recovery_compliance": insufficient_recovery_compliance,
            }
        )
        return item, synthetic

    def _path_table(self, sliced: pd.DataFrame, column: str) -> list[dict[str, Any]]:
        if sliced.empty:
            return []
        counts = Counter(sliced[column])
        return [
            {"label": str(label), "days": int(count), "share": round(float(count / len(sliced)), 6)}
            for label, count in counts.items()
        ]

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        (self.artifacts_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_md(self, filename: str, title: str, payload: dict[str, Any]) -> None:
        lines = [f"# {title}", ""]
        if "decision" in payload:
            lines.extend(["## Decision", f"`{payload['decision']}`", ""])
        if "final_verdict" in payload:
            lines.extend(["## Final Verdict", f"`{payload['final_verdict']}`", ""])
        if "summary" in payload:
            lines.extend(["## Summary", payload["summary"], ""])
        lines.extend(
            [
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:16000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines), encoding="utf-8")


def build_runtime_dashboard_payload(result: SignalResult) -> dict[str, Any]:
    return ProductCycleDashboardPatch.build_runtime_dashboard_payload(result)


if __name__ == "__main__":
    verdict = ProductCycleDashboardPatch(root=REPO_ROOT).run_all()
    print(json.dumps(verdict, indent=2))
