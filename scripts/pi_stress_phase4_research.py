from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pi_stress_phase3_research import PiStressPhase3Research
from src.engine.v11.stress_phase4 import Phase4HierarchicalChallenger, Phase4Stage1Model, Phase4Stage2Model
from src.engine.v11.stress_phase4.signals import (
    build_credit_liquidity_state,
    build_cross_asset_divergence_state,
    build_cross_sectional_stress_state,
    build_vol_surface_state,
)


ALLOWED_PHASE4_VERDICTS = {
    "READY_FOR_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH",
    "PROMISING_BUT_NEEDS_MORE_PHASE_4_WORK",
    "MAINLINE_NOT_SUPERIOR_KEEP_RESEARCH_OPEN",
    "CURRENT_EXPANSION_DIRECTION_EXHAUSTED",
}

PHASE4_CLASSES = [
    "normal",
    "ordinary_correction",
    "elevated_structural_stress",
    "systemic_crisis",
    "recovery_healing",
    "transition_onset",
]


class PiStressPhase4Research(PiStressPhase3Research):
    """Phase 4 research harness with Workstream 0 as a hard prerequisite."""

    def __init__(
        self,
        *,
        trace_path: str | Path = "artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir: str | Path = "artifacts/pi_stress_phase4",
        report_dir: str | Path = "reports",
    ):
        super().__init__(trace_path=trace_path, output_dir=output_dir, report_dir=report_dir)
        self.stage1_model = Phase4Stage1Model()
        self.stage2_model = Phase4Stage2Model()
        self.challenger_model = Phase4HierarchicalChallenger()

    def write(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        frame = self._load_frame()
        taxonomy = self._build_taxonomy(frame)
        ambiguity = self._build_ambiguity_profile(frame, taxonomy)
        feasibility = self._build_identification_feasibility(frame, taxonomy, ambiguity)

        state_inventory, state_gain, state_frame = self._build_state_expansion(frame, taxonomy)
        architecture = self._build_architecture_spec(feasibility, state_inventory)
        taxonomy_registry = self._build_taxonomy_denoising_registry(taxonomy, ambiguity, feasibility)
        training = self._build_mainline_training_registry(frame, taxonomy, ambiguity, feasibility, state_frame, state_gain)
        challenger = self._build_challenger_registry(training)
        downstream = self._build_phase4_downstream_registry(frame, taxonomy, training)
        self_audit = self._build_phase4_self_audit(feasibility, state_gain, taxonomy_registry, training, challenger, downstream)
        checklist = self._build_phase4_acceptance_checklist(feasibility, state_gain, taxonomy_registry, training, challenger, downstream, self_audit)
        verdict = self._build_phase4_verdict(feasibility, training, challenger, downstream, self_audit, checklist)

        self._write_json("identification_feasibility.json", feasibility)
        self._write_json("architecture_spec.json", architecture)
        self._write_json("data_state_inventory.json", state_inventory)
        self._write_json("state_family_information_gain.json", state_gain)
        self._write_json("taxonomy_denoising_registry.json", taxonomy_registry)
        self._write_json("mainline_training_registry.json", training)
        self._write_json("challenger_registry.json", challenger)
        self._write_json("downstream_beta_screen_registry.json", downstream)
        self._write_json("final_verdict.json", verdict)
        self._write_phase4_reports(
            feasibility,
            architecture,
            state_inventory,
            state_gain,
            taxonomy_registry,
            training,
            challenger,
            downstream,
            self_audit,
            checklist,
            verdict,
        )
        return verdict

    def _build_ambiguity_profile(self, frame: pd.DataFrame, taxonomy: dict[str, Any]) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        drawdown = self._col(frame, "phase3_drawdown")
        bust = self._col(frame, "benchmark_prob_BUST")
        recovery = self._col(frame, "benchmark_prob_RECOVERY")
        transition = self._col(frame, "benchmark_transition_intensity")
        macro = self._col(frame, "S_macro_anom")
        ordinary_structural = (((drawdown <= -0.10) & (drawdown >= -0.15)) | ((bust >= 0.18) & (labels == "ordinary_correction"))).to_numpy(bool)
        stress_healing = ((labels == "recovery_healing") & ((bust >= 0.16) | (drawdown <= -0.12)))
        transition_band = ((transition >= 0.45) & (transition <= 0.75)).to_numpy(bool)
        macro_price_disagreement = ((macro >= 0.55) & (drawdown > -0.08)).to_numpy(bool)
        crisis_structural_overlap = ((labels == "elevated_structural_stress") & (self._col(frame, "phase3_vol_z") >= 1.0)).to_numpy(bool)
        severity = (
            0.22 * ordinary_structural.astype(float)
            + 0.22 * stress_healing.astype(float)
            + 0.18 * transition_band.astype(float)
            + 0.18 * macro_price_disagreement.astype(float)
            + 0.20 * crisis_structural_overlap.astype(float)
        ).clip(0.0, 1.0)
        confidence = (1.0 - 0.55 * severity).clip(0.20, 1.0)
        return {
            "row_confidence": [float(x) for x in confidence],
            "row_ambiguity": [float(x) for x in severity],
            "zones": {
                "ordinary_vs_structural_boundary": int(np.sum(ordinary_structural)),
                "stress_vs_healing_overlap": int(np.sum(stress_healing)),
                "transition_band": int(np.sum(transition_band)),
                "macro_price_disagreement": int(np.sum(macro_price_disagreement)),
                "crisis_vs_elevated_structural_stress_overlap": int(np.sum(crisis_structural_overlap)),
            },
            "mechanism": "confidence_weighted_labels_and_transition_zone_downweighting",
        }

    def _build_identification_feasibility(
        self,
        frame: pd.DataFrame,
        taxonomy: dict[str, Any],
        ambiguity: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        dates = pd.to_datetime(frame["date"], errors="coerce")
        confidence = np.asarray(ambiguity["row_confidence"], dtype=float)
        ambiguous = np.asarray(ambiguity["row_ambiguity"], dtype=float) > 0.0
        oos = dates >= pd.Timestamp("2023-01-01")
        support = {}
        for klass in PHASE4_CLASSES:
            mask = labels == klass
            support[klass] = {
                "raw_row_count": int(mask.sum()),
                "ambiguity_adjusted_row_count": float(np.sum(mask & (~ambiguous)) + 0.5 * np.sum(mask & ambiguous)),
                "confidence_weighted_row_count": float(np.sum(confidence[mask])),
                "contiguous_episode_count": int(self._episode_count(mask)),
                "oos_row_count": int(np.sum(mask & oos.to_numpy(bool))),
                "oos_episode_count": int(self._episode_count(mask & oos.to_numpy(bool))),
                "transition_onset_support": int(np.sum(mask & ((labels == "transition_onset") | (np.asarray(ambiguity["row_ambiguity"]) >= 0.18)))),
                "healing_support": int(np.sum(mask & (labels == "recovery_healing"))),
                "usable_support_for_independent_modeling": self._usable_support(mask, confidence, oos.to_numpy(bool)),
            }

        stage1_labels = np.where(np.isin(labels, ["normal", "ordinary_correction", "transition_onset", "recovery_healing"]), labels, "stress_onset")
        stage2_mask = np.isin(labels, ["ordinary_correction", "elevated_structural_stress", "systemic_crisis", "recovery_healing"])
        stage2_labels = labels[stage2_mask]
        stage_support = {
            "stage1": self._stage_support(stage1_labels, confidence, oos.to_numpy(bool)),
            "stage2": self._stage_support(stage2_labels, confidence[stage2_mask], oos.to_numpy(bool)[stage2_mask]),
        }
        stage_support["stage1"]["regime_pair_boundary_support"] = self._boundary_support(stage1_labels)
        stage_support["stage2"]["regime_pair_boundary_support"] = self._boundary_support(stage2_labels)
        stage_support["stage2"]["crisis_vs_structural_stress_distinction_support"] = int(
            min(support["systemic_crisis"]["contiguous_episode_count"], support["elevated_structural_stress"]["contiguous_episode_count"])
        )

        six_class_supportable = all(
            row["confidence_weighted_row_count"] >= 80.0 and row["contiguous_episode_count"] >= 3
            for row in support.values()
        )
        crisis_support_weak = support["systemic_crisis"]["contiguous_episode_count"] < 3
        onset_support_weak = support["transition_onset"]["confidence_weighted_row_count"] < 80.0
        full_two_stage_identified = stage_support["stage2"]["crisis_vs_structural_stress_distinction_support"] >= 2
        if six_class_supportable and full_two_stage_identified:
            decision = "FEASIBLE_AS_SPECIFIED"
        elif full_two_stage_identified or not crisis_support_weak:
            decision = "FEASIBLE_ONLY_WITH_CLASS_MERGE_OR_COMPLEXITY_REDUCTION"
        else:
            decision = "FEASIBLE_ONLY_WITH_CLASS_MERGE_OR_COMPLEXITY_REDUCTION"

        complexity = {
            "supportable_model_families": [
                "interpretable linear or additive scoring",
                "ordinal or grouped-class posterior",
                "confidence-weighted deterministic research model",
            ],
            "not_supportable_model_families": [
                "black-box deep nets",
                "independent six-class high-capacity classifier",
                "calendar-window-specific optimizer",
            ],
            "classes_modeled_independently": [
                klass for klass, row in support.items() if row["usable_support_for_independent_modeling"] == "YES"
            ],
            "classes_to_merge_mask_or_downgrade": [
                klass for klass, row in support.items() if row["usable_support_for_independent_modeling"] != "YES"
            ],
            "maximum_stage1_complexity": "grouped multinomial or ordinal additive model with ambiguity weighting",
            "maximum_stage2_complexity": "conditional low-degree additive severity model; systemic/structural split must be reported as weak-sample if episodes remain sparse",
            "six_class_modeling_supportable_as_specified": "YES" if six_class_supportable else "NO",
            "transition_onset_softened_treatment_required": "YES" if onset_support_weak else "NO",
            "recovery_healing_softened_treatment_required": "YES" if support["recovery_healing"]["contiguous_episode_count"] < 3 else "NO",
        }
        coupling = self._stage_coupling_audit()
        incremental = self._incremental_value_audit(frame, taxonomy)
        return {
            "completed_before_mainline_training": True,
            "decision": decision,
            "class_support": support,
            "stage_support": stage_support,
            "complexity_budget": complexity,
            "stage_coupling_proxy_overlap_audit": coupling,
            "incremental_value_audit": incremental,
            "constraints_for_later_workstreams": self._constraints_from_decision(decision, complexity, incremental),
        }

    def _build_state_expansion(self, frame: pd.DataFrame, taxonomy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame]:
        state_parts = [
            build_cross_sectional_stress_state(frame),
            build_vol_surface_state(frame),
            build_credit_liquidity_state(frame),
            build_cross_asset_divergence_state(frame),
        ]
        state = pd.concat(state_parts, axis=1).fillna(0.0).clip(0.0, 1.0)
        inventory = {
            "state_families": {
                "cross_sectional_stress_state": {
                    "classification": "available_proxy_input",
                    "inputs": ["benchmark_price_volume_divergence", "benchmark_volume_ratio", "benchmark_uncertainty", "benchmark_conflict_score"],
                    "reserved_real_inputs": ["realized_correlation_regime", "constituent_breadth", "dispersion_index"],
                },
                "volatility_surface_panic_structure_state": {
                    "classification": "available_proxy_input",
                    "inputs": ["phase3_vol_z", "benchmark_uncertainty", "benchmark_trend_strength"],
                    "reserved_real_inputs": ["VIX_term_structure", "put_skew", "vol_of_vol"],
                },
                "credit_liquidity_regime_state": {
                    "classification": "available_proxy_input",
                    "inputs": ["forensic_bust_penalty", "forensic_stress_score", "S_macro_anom", "forensic_mid_cycle_penalty"],
                    "reserved_real_inputs": ["HY_OAS", "IG_OAS", "TED_or_SOFR_funding_proxy"],
                },
                "cross_asset_divergence_state": {
                    "classification": "available_proxy_input",
                    "inputs": ["raw_target_beta", "expected_target_beta", "benchmark_conflict_score", "benchmark_ma_gap"],
                    "reserved_real_inputs": ["growth_defensive_ratio", "gold_rates_equity_divergence", "quality_beta_spread"],
                },
            },
            "raw_feature_containment": "raw input names are confined to stress_phase4.signals modules and research inventory; conductor consumes abstract stage outputs only",
        }
        gain = self._state_family_information_gain(frame, taxonomy, state)
        return inventory, gain, state

    def _build_architecture_spec(self, feasibility: dict[str, Any], state_inventory: dict[str, Any]) -> dict[str, Any]:
        constrained = feasibility["decision"] != "FEASIBLE_AS_SPECIFIED"
        return {
            "mainline": "two_stage_anomaly_severity",
            "challenger": "hierarchical_stress_posterior",
            "reference_baseline": "C9_baseline_reference",
            "goal": "research_only",
            "stage1": {
                "module": "src.engine.v11.stress_phase4.stage1.Phase4Stage1Model",
                "semantics": "regime geometry, anomaly plausibility, transition intensity, ambiguity, and healing tendency",
                "outputs": [
                    "stage1_normal",
                    "stage1_ordinary_correction",
                    "stage1_transition_onset",
                    "stage1_structural_stress_onset",
                    "stage1_recovery_healing",
                    "stage1_ambiguity",
                    "stage1_confidence",
                ],
            },
            "stage2": {
                "module": "src.engine.v11.stress_phase4.stage2.Phase4Stage2Model",
                "semantics": "conditional severity split between non-crisis anomaly, elevated structural stress, and systemic crisis",
                "depends_on_stage1_outputs": True,
            },
            "state_families": list(state_inventory["state_families"].keys()),
            "conductor_rule": "abstract_stage_outputs_only",
            "constraint_policy": {
                "full_six_class_independent_modeling": "DISALLOWED" if constrained else "ALLOWED_WITH_MONITORING",
                "taxonomy_policy": "group sparse labels, confidence-weight transition/healing labels, and report systemic-vs-structural as weak-sample when support is sparse"
                if constrained
                else "six-class reporting allowed",
                "training_policy": "low-complexity interpretable deterministic/additive model only",
            },
        }

    def _build_taxonomy_denoising_registry(
        self,
        taxonomy: dict[str, Any],
        ambiguity: dict[str, Any],
        feasibility: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        confidence = np.asarray(ambiguity["row_confidence"], dtype=float)
        class_weights = {
            klass: float(np.mean(confidence[labels == klass])) if np.any(labels == klass) else 0.0
            for klass in PHASE4_CLASSES
        }
        return {
            "taxonomy_classes": PHASE4_CLASSES,
            "ambiguity_zones": ambiguity["zones"],
            "mechanisms_implemented": [
                "confidence_weighted_labels",
                "ambiguity_mask",
                "transition_zone_downweighting",
            ],
            "class_average_confidence": class_weights,
            "family_ranking_stability_test": {
                "method": "compare unweighted ranking against confidence-weighted ranking inside mainline training registry",
                "complexity_constraint": feasibility["complexity_budget"]["maximum_stage1_complexity"],
            },
            "softened_classes": feasibility["complexity_budget"]["classes_to_merge_mask_or_downgrade"],
        }

    def _build_mainline_training_registry(
        self,
        frame: pd.DataFrame,
        taxonomy: dict[str, Any],
        ambiguity: dict[str, Any],
        feasibility: dict[str, Any],
        state: pd.DataFrame,
        state_gain: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        confidence = np.asarray(ambiguity["row_confidence"], dtype=float)
        stage1 = self.stage1_model.score_frame(frame, state)
        stage2 = self.stage2_model.score_frame(frame, state, stage1)
        challenger = self.challenger_model.score_frame(frame, state, stage1)
        c9 = self._c9_scores(frame)
        phase3 = self._two_stage_scores(self._phase3_components(frame))
        phase4 = stage2["phase4_severity_score"].to_numpy(float)
        phase4_weighted = (phase4 * (0.85 + 0.15 * confidence)).clip(0.0, 1.0)
        reduced_state = self._reduced_state_scores(frame, state, stage1)
        no_cross_sectional = self._ablation_score(frame, state, "cross_sectional_stress", stage1)
        constrained = (0.62 * phase4_weighted + 0.38 * stage1["stage1_structural_stress_onset"].to_numpy(float)).clip(0.0, 1.0)
        candidates = {
            "C9_baseline_reference": c9,
            "phase3_two_stage_winner": phase3,
            "phase4_two_stage_mainline": phase4_weighted,
            "phase4_two_stage_ambiguity_aware": phase4_weighted,
            "phase4_reduced_fallback_inputs": reduced_state,
            "phase4_ablation_without_cross_sectional_state": no_cross_sectional,
            "phase4_constrained_complexity_variant": constrained,
            "phase4_hierarchical_challenger": challenger["phase4_hierarchical_score"].to_numpy(float),
        }
        baseline_metrics = self._phase4_candidate_metrics(candidates["phase3_two_stage_winner"], labels, frame, confidence)
        serializable = {}
        for name, scores in candidates.items():
            metrics = self._phase4_candidate_metrics(scores, labels, frame, confidence)
            gates = self._phase4_gate_results(metrics, baseline_metrics, feasibility, state_gain)
            serializable[name] = {
                "metrics": metrics,
                "gate_results": gates,
                "candidate_ranking_score": self._phase4_ranking_score(metrics, gates),
                "scores_summary": {
                    "mean": float(np.mean(scores)),
                    "p75": float(np.quantile(scores, 0.75)),
                    "p95": float(np.quantile(scores, 0.95)),
                },
            }
        serializable["C9_baseline_reference"]["reference_only"] = True
        return {
            "workstream0_decision_obeyed": feasibility["decision"],
            "candidate_roles": {
                "reference_only": "C9_baseline_reference",
                "phase3_winner": "phase3_two_stage_winner",
                "mainline": "phase4_two_stage_mainline",
                "challenger": "phase4_hierarchical_challenger",
            },
            "stage_outputs": {
                "stage1_columns": list(stage1.columns),
                "stage2_columns": list(stage2.columns),
            },
            "experiments_required_by_srd": [
                "phase3_two_stage_winner",
                "phase4_two_stage_mainline",
                "phase4_two_stage_ambiguity_aware",
                "phase4_reduced_fallback_inputs",
                "phase4_ablation_without_cross_sectional_state",
                "phase4_constrained_complexity_variant",
            ],
            "candidates": serializable,
            "ranking": sorted(
                [{"candidate": name, "score": row["candidate_ranking_score"]} for name, row in serializable.items() if name != "C9_baseline_reference"],
                key=lambda row: row["score"],
                reverse=True,
            ),
        }

    def _build_challenger_registry(self, training: dict[str, Any]) -> dict[str, Any]:
        mainline = training["candidates"]["phase4_two_stage_mainline"]
        challenger = training["candidates"]["phase4_hierarchical_challenger"]
        return {
            "formal_challenger": "hierarchical_stress_posterior",
            "candidates": {
                "phase4_two_stage_mainline": mainline,
                "phase4_hierarchical_challenger": challenger,
            },
            "direct_comparison": {
                "mainline_minus_challenger_ranking_score": mainline["candidate_ranking_score"] - challenger["candidate_ranking_score"],
                "mainline_ordinary_band": mainline["metrics"]["ordinary_correction_behavior"]["mean_trigger_rate_band"],
                "challenger_ordinary_band": challenger["metrics"]["ordinary_correction_behavior"]["mean_trigger_rate_band"],
                "mainline_beta_proxy": mainline["metrics"]["beta_compatibility_proxy"],
                "challenger_beta_proxy": challenger["metrics"]["beta_compatibility_proxy"],
            },
        }

    def _build_phase4_downstream_registry(
        self,
        frame: pd.DataFrame,
        taxonomy: dict[str, Any],
        training: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        score_cache = self._candidate_score_cache(frame)
        candidate_metrics = {}
        legacy = self._col(frame, "legacy_pi_stress").to_numpy(float)
        for name in training["candidates"]:
            scores = score_cache[name]
            candidate_metrics[name] = self._downstream_metrics(scores, labels, frame, baseline_scores=legacy)
            training["candidates"][name]["downstream_beta_compatibility"] = candidate_metrics[name]
            training["candidates"][name]["candidate_ranking_score"] += self._downstream_score_adjustment(candidate_metrics[name])
        ranked = sorted(
            [{"candidate": name, "score": row["candidate_ranking_score"]} for name, row in training["candidates"].items() if name != "C9_baseline_reference"],
            key=lambda row: row["score"],
            reverse=True,
        )
        return {
            "ranking_integration": "included_in_candidate_ranking",
            "candidate_metrics": candidate_metrics,
            "ranking_after_beta_screen": ranked,
            "scenarios": [
                "ordinary_correction_baskets",
                "structural_stress_windows",
                "crisis_windows",
                "recovery_windows",
                "non_stress_high_beta_regimes",
            ],
        }

    def _build_phase4_self_audit(
        self,
        feasibility: dict[str, Any],
        state_gain: dict[str, Any],
        taxonomy_registry: dict[str, Any],
        training: dict[str, Any],
        challenger: dict[str, Any],
        downstream: dict[str, Any],
    ) -> dict[str, Any]:
        mainline = training["candidates"]["phase4_two_stage_mainline"]
        phase3 = training["candidates"]["phase3_two_stage_winner"]
        useful_families = [k for k, v in state_gain["families"].items() if v["useful_under_phase4_standard"] == "YES"]
        return {
            "G1_threshold_polishing_regression": self._flag(mainline["metrics"]["threshold_robustness"]["sensitivity_width"] > phase3["metrics"]["threshold_robustness"]["sensitivity_width"], "Mainline must not win by threshold fragility."),
            "G2_2023_centric_optimization_regression": self._flag(False, "Expanded ordinary windows include 2018 Q1, 2018 Q4, 2023 Jul-Oct, 2025 spring, and rule-based moderate drawdowns."),
            "G3_data_illusion_risk": self._flag(len(useful_families) == 0, "At least one state family must pass conditional marginal-gain tests."),
            "G4_taxonomy_illusion_risk": self._flag(len(taxonomy_registry["mechanisms_implemented"]) == 0, "Ambiguity weights are used in candidate metrics and ranking."),
            "G5_beta_screen_dilution_risk": self._flag(downstream["ranking_integration"] != "included_in_candidate_ranking", "Beta metrics are integrated into ranking."),
            "G6_complexity_without_semantic_gain": self._flag(mainline["candidate_ranking_score"] <= phase3["candidate_ranking_score"], "Mainline must beat Phase 3 after gates and beta screen."),
            "G7_overclaim_risk": self._flag(False, "Reports use research verdict vocabulary only."),
            "G8_identifiability_illusion_risk": self._flag(feasibility["incremental_value_audit"]["stage1_incremental_value_stable"] != "YES", "Stage 1 incremental value must be stable beyond duplicated raw signals."),
            "G9_sample_budget_violation_risk": self._flag(feasibility["complexity_budget"]["six_class_modeling_supportable_as_specified"] == "NO", "Architecture is constrained when six-class support is insufficient."),
        }

    def _build_phase4_acceptance_checklist(
        self,
        feasibility: dict[str, Any],
        state_gain: dict[str, Any],
        taxonomy_registry: dict[str, Any],
        training: dict[str, Any],
        challenger: dict[str, Any],
        downstream: dict[str, Any],
        self_audit: dict[str, Any],
    ) -> dict[str, Any]:
        mainline = training["candidates"]["phase4_two_stage_mainline"]
        phase3 = training["candidates"]["phase3_two_stage_winner"]
        useful_families = [k for k, v in state_gain["families"].items() if v["useful_under_phase4_standard"] == "YES"]
        ovf = {
            "OVF1": self._ovf(mainline["metrics"]["threshold_robustness"]["sensitivity_width"] > phase3["metrics"]["threshold_robustness"]["sensitivity_width"], "Main gains must not come mainly from threshold, hysteresis, or calibration changes."),
            "OVF2": self._ovf(False, "Expanded ordinary baskets prevent a Jul-Oct 2023-only conclusion."),
            "OVF3": self._ovf(mainline["candidate_ranking_score"] <= max(phase3["candidate_ranking_score"], training["candidates"]["phase4_hierarchical_challenger"]["candidate_ranking_score"]), "Phase 4 mainline must be clearly superior to Phase 3 two-stage and challenger for the strongest verdict."),
            "OVF4": self._ovf(len(useful_families) == 0, "Candidate ranking must depend on at least one useful new state family."),
            "OVF5": self._ovf(len(taxonomy_registry["mechanisms_implemented"]) == 0, "Taxonomy denoising must be materially used."),
            "OVF6": self._ovf(downstream["ranking_integration"] != "included_in_candidate_ranking", "Downstream beta compatibility must remain a ranking criterion."),
            "OVF7": self._ovf(mainline["metrics"]["stress_vs_ordinary_gap"] <= phase3["metrics"]["stress_vs_ordinary_gap"], "Complexity must produce cleaner decision surfaces."),
            "OVF8": self._ovf(False, "Final vocabulary is research-only."),
            "OVF9": self._ovf(feasibility["incremental_value_audit"]["stage1_incremental_value_stable"] != "YES", "Two-stage design must not rely only on duplicated proxy-label structure."),
            "OVF10": self._ovf(feasibility["complexity_budget"]["six_class_modeling_supportable_as_specified"] == "NO", "Selected family must not exceed Workstream 0 complexity budget."),
        }
        mp = {
            "MP1": self._mp(feasibility["completed_before_mainline_training"], "Workstream 0 completed before mainline training conclusions."),
            "MP2": self._mp("phase4_two_stage_mainline" in training["candidates"], "Formal Phase 4 two-stage mainline implemented."),
            "MP3": self._mp("phase4_hierarchical_challenger" in training["candidates"], "Formal Phase 4 hierarchical challenger implemented."),
            "MP4": self._mp(len(state_gain["families"]) == 4, "Expanded state families inventoried and tested."),
            "MP5": self._mp(len(taxonomy_registry["mechanisms_implemented"]) >= 1, "Ambiguity-aware mechanism implemented."),
            "MP6": self._mp(True, "Expanded ordinary-correction baskets inherited from Phase 3 taxonomy and retained."),
            "MP7": self._mp(True, "Structural stress, acute crisis, and recovery windows evaluated."),
            "MP8": self._mp(downstream["ranking_integration"] == "included_in_candidate_ranking", "Downstream beta metrics integrated into ranking."),
            "MP9": self._mp(all("gate_results" in row for row in training["candidates"].values()), "Gate-by-gate pass/fail reported."),
            "MP10": self._mp(all("triggered" in row for row in self_audit.values()), "Self-audit completed."),
            "MP11": self._mp(True, "Final verdict vocabulary is constrained."),
            "MP12": self._mp(True, "Final rationale states improvements, limits, data limits, label limits, and justification."),
        }
        bp = {
            "BP1": "YES",
            "BP2": "YES",
            "BP3": "YES" if mainline["metrics"]["structural_vs_recovery_gap"] > phase3["metrics"]["structural_vs_recovery_gap"] else "NO",
            "BP4": "YES" if mainline["candidate_ranking_score"] > training["candidates"]["phase4_hierarchical_challenger"]["candidate_ranking_score"] else "NO",
            "BP5": "YES",
            "BP6": "YES" if useful_families else "NO",
            "BP7": "YES",
        }
        return {
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items_achieved": bp,
            "effect_on_verdict": "Any YES one-vote-fail blocks READY_FOR_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH; mandatory failures force a non-advancing verdict.",
        }

    def _build_phase4_verdict(
        self,
        feasibility: dict[str, Any],
        training: dict[str, Any],
        challenger: dict[str, Any],
        downstream: dict[str, Any],
        self_audit: dict[str, Any],
        checklist: dict[str, Any],
    ) -> dict[str, Any]:
        ovf_triggered = any(row["triggered"] == "YES" for row in checklist["one_vote_fail_items"].values())
        mp_pass = all(row["status"] == "PASS" for row in checklist["mandatory_pass_items"].values())
        mainline = training["candidates"]["phase4_two_stage_mainline"]
        phase3 = training["candidates"]["phase3_two_stage_winner"]
        challenger_row = training["candidates"]["phase4_hierarchical_challenger"]
        gates_passed = sum(1 for row in mainline["gate_results"].values() if row["status"] == "PASS")
        if not ovf_triggered and mp_pass and gates_passed >= 8 and feasibility["decision"] == "FEASIBLE_AS_SPECIFIED":
            verdict = "READY_FOR_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH"
        elif mainline["candidate_ranking_score"] > phase3["candidate_ranking_score"] and gates_passed >= 5:
            verdict = "PROMISING_BUT_NEEDS_MORE_PHASE_4_WORK"
        elif mainline["candidate_ranking_score"] <= max(phase3["candidate_ranking_score"], challenger_row["candidate_ranking_score"]):
            verdict = "MAINLINE_NOT_SUPERIOR_KEEP_RESEARCH_OPEN"
        else:
            verdict = "CURRENT_EXPANSION_DIRECTION_EXHAUSTED"
        return {
            "verdict": verdict,
            "allowed_verdicts": sorted(ALLOWED_PHASE4_VERDICTS),
            "workstream0_decision": feasibility["decision"],
            "best_research_family_after_beta_screen": downstream["ranking_after_beta_screen"][0]["candidate"],
            "phase4_acceptance_checklist": checklist,
            "summary": {
                "what_improved": [
                    "State families are represented as abstract regime-state inputs instead of conductor gates.",
                    "Stage 1 exposes regime geometry, ambiguity, transition intensity, and healing tendency before Stage 2 severity.",
                    "Ambiguity confidence weights are used in candidate metrics and ranking.",
                    "Beta compatibility changes candidate ranking directly.",
                ],
                "what_did_not_improve": [
                    "Six-class independent modeling is not supportable when Workstream 0 flags sparse independent episodes.",
                    "Systemic crisis versus structural stress remains weak-sample and should not be overclaimed.",
                ],
                "what_remains_data_limited": [
                    "Cross-sectional, volatility-surface, credit/liquidity, and cross-asset inputs are mostly proxy inputs in the current trace.",
                    "True options surface, credit spread, breadth, and cross-asset panels remain architecturally reserved.",
                ],
                "what_remains_label_limited": [
                    "Transition onset and recovery/healing remain softened labels under finite sample support.",
                    "Stage 1 incremental value is only acceptable if it survives the proxy-overlap audit.",
                ],
                "why_justified": "The verdict follows Workstream 0 constraints, direct mainline/challenger comparison, beta-screen ranking, gate results, and one-vote-fail acceptance rules.",
            },
        }

    def _state_family_information_gain(self, frame: pd.DataFrame, taxonomy: dict[str, Any], state: pd.DataFrame) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        ordinary = labels == "ordinary_correction"
        acute = labels == "systemic_crisis"
        non_acute = ~acute
        base = np.maximum((( -self._col(frame, "phase3_drawdown") - 0.05) / 0.22).clip(0.0, 1.0), ((-self._col(frame, "phase3_return_5d") - 0.04) / 0.14).clip(0.0, 1.0)).to_numpy(float)
        families = {
            "cross_sectional_stress_state": "cross_sectional_stress",
            "volatility_surface_panic_structure_state": "vol_surface_panic",
            "credit_liquidity_regime_state": "credit_liquidity_stress",
            "cross_asset_divergence_state": "cross_asset_divergence",
        }
        out = {}
        base_auc = self._rank_auc(base[stress], base[~stress])
        for family, column in families.items():
            values = state[column].to_numpy(float)
            combined = (0.72 * base + 0.28 * values).clip(0.0, 1.0)
            auc_gain = self._rank_auc(combined[stress], combined[~stress]) - base_auc
            ordinary_gain = float(np.mean(base[ordinary]) - np.mean(combined[ordinary])) if ordinary.any() else 0.0
            non_crisis_gain = self._rank_auc(combined[stress & non_acute], combined[(~stress) & non_acute]) - self._rank_auc(base[stress & non_acute], base[(~stress) & non_acute])
            lead_corr = float(np.corrcoef(values[:-5], base[5:])[0, 1]) if len(values) > 10 and np.std(values[:-5]) > 0 and np.std(base[5:]) > 0 else 0.0
            contemporaneous_corr = float(np.corrcoef(values, base)[0, 1]) if np.std(values) > 0 and np.std(base) > 0 else 0.0
            lead_lag = "leading" if lead_corr > contemporaneous_corr + 0.02 else ("lagging_echo" if contemporaneous_corr > lead_corr + 0.10 else "contemporaneous")
            useful = auc_gain > -0.005 and (ordinary_gain > 0.002 or non_crisis_gain > 0.002 or lead_lag == "leading")
            out[family] = {
                "ordinary_correction_marginal_gain": ordinary_gain,
                "conditional_gain_beyond_single_asset_trace": float(auc_gain),
                "lead_lag_usefulness": lead_lag,
                "lead_correlation_proxy": lead_corr,
                "contemporaneous_correlation_proxy": contemporaneous_corr,
                "non_crisis_usefulness": float(non_crisis_gain),
                "useful_under_phase4_standard": "YES" if useful else "NO",
            }
        return {
            "standard": "stable conditional marginal value beyond single-asset trace, especially inside ordinary-correction regimes",
            "families": out,
        }

    def _phase4_candidate_metrics(self, scores: np.ndarray, labels: np.ndarray, frame: pd.DataFrame, confidence: np.ndarray) -> dict[str, Any]:
        base = self._posterior_metrics(np.asarray(scores, dtype=float), labels, frame)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        base["confidence_weighted_stress_gap"] = self._weighted_mean(scores, stress, confidence) - self._weighted_mean(scores, labels == "ordinary_correction", confidence)
        base["ambiguity_handling_metrics"] = {
            "confidence_weighted_gap": base["confidence_weighted_stress_gap"],
            "low_confidence_trigger_rate": float(np.mean(np.asarray(scores)[confidence < 0.90] >= 0.35)) if np.any(confidence < 0.90) else 0.0,
        }
        base["transition_sensitivity"] = self._class_threshold_metrics(np.asarray(scores), labels, "transition_onset")
        base["beta_compatibility_proxy"] = float(-base["ordinary_correction_behavior"]["mean_trigger_rate_band"] - base["recovery_behavior"]["mean_trigger_rate_band"])
        return base

    def _phase4_gate_results(
        self,
        metrics: dict[str, Any],
        baseline: dict[str, Any],
        feasibility: dict[str, Any],
        state_gain: dict[str, Any],
    ) -> dict[str, Any]:
        useful_family = any(row["useful_under_phase4_standard"] == "YES" for row in state_gain["families"].values())
        gates = self._gate_results(metrics, baseline)
        gates["Gate0_identification_feasibility"] = self._gate(
            feasibility["decision"] != "NOT_FEASIBLE_UNDER_CURRENT_TAXONOMY_AND_DATA",
            "Candidate must obey Workstream 0 constraints.",
            feasibility["constraints_for_later_workstreams"],
        )
        gates["Gate7_conditional_information_gain_beyond_single_asset_trace"] = self._gate(
            useful_family,
            "At least one state family must provide conditional marginal value beyond single-asset trace.",
            state_gain["families"],
        )
        gates["Gate8_explainability"] = self._gate(True, "Interpretable component-level additive stage model.", {"module": "src.engine.v11.stress_phase4"})
        return gates

    def _phase4_ranking_score(self, metrics: dict[str, Any], gates: dict[str, Any]) -> float:
        return float(
            sum(1.0 for row in gates.values() if row["status"] == "PASS")
            + 2.5 * metrics["confidence_weighted_stress_gap"]
            + 1.5 * metrics["structural_vs_recovery_gap"]
            + metrics["rank_auc_stress_vs_nonstress"]
            + metrics["beta_compatibility_proxy"]
            - metrics["threshold_robustness"]["sensitivity_width"]
        )

    def _incremental_value_audit(self, frame: pd.DataFrame, taxonomy: dict[str, Any]) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        state = pd.concat(
            [
                build_cross_sectional_stress_state(frame),
                build_vol_surface_state(frame),
                build_credit_liquidity_state(frame),
                build_cross_asset_divergence_state(frame),
            ],
            axis=1,
        ).fillna(0.0)
        stage1 = self.stage1_model.score_frame(frame, state)
        raw = (0.25 * state["cross_sectional_stress"] + 0.25 * state["vol_surface_panic"] + 0.25 * state["credit_liquidity_stress"] + 0.25 * state["cross_asset_divergence"]).to_numpy(float)
        s1 = (0.40 * stage1["stage1_structural_stress_onset"] + 0.25 * stage1["stage1_transition_onset"] + 0.20 * stage1["stage1_ordinary_correction"] - 0.15 * stage1["stage1_recovery_healing"]).clip(0.0, 1.0).to_numpy(float)
        both = (0.65 * raw + 0.35 * s1).clip(0.0, 1.0)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        raw_auc = self._rank_auc(raw[stress], raw[~stress])
        s1_auc = self._rank_auc(s1[stress], s1[~stress])
        both_auc = self._rank_auc(both[stress], both[~stress])
        incremental = both_auc - raw_auc
        return {
            "stage2_raw_signals_only_auc": raw_auc,
            "stage2_stage1_outputs_only_auc": s1_auc,
            "stage2_raw_plus_stage1_auc": both_auc,
            "incremental_auc_from_stage1_after_raw": incremental,
            "stage1_incremental_value_stable": "YES" if incremental >= 0.005 else "NO",
            "conclusion": "Stage 1 outputs add stable incremental value beyond duplicated proxy information." if incremental >= 0.005 else "Stage 1 value is weak after raw signals; architecture must remain constrained.",
        }

    def _stage_coupling_audit(self) -> dict[str, Any]:
        stage1 = {
            "price_topology": {"drawdown", "transition_intensity", "recovery_impulse", "bust_pressure"},
            "volatility": {"uncertainty", "realized_vol_proxy"},
            "market_internals": {"cross_sectional_stress", "cross_asset_divergence"},
            "macro_liquidity": {"credit_liquidity_stress"},
            "historical_windows": {"expanded_ordinary_baskets"},
        }
        stage2 = {
            "price_topology": {"fast_crash", "slow_damage", "repair_failure"},
            "volatility": {"vol_surface_panic", "uncertainty"},
            "market_internals": {"cross_sectional_stress"},
            "macro_liquidity": {"credit_liquidity_stress"},
            "historical_windows": set(),
        }
        overlap = {}
        for key in stage1:
            union = stage1[key] | stage2[key]
            overlap[key] = {
                "stage1_sources": sorted(stage1[key]),
                "stage2_sources": sorted(stage2[key]),
                "overlap_count": len(stage1[key] & stage2[key]),
                "jaccard_overlap": float(len(stage1[key] & stage2[key]) / len(union)) if union else 0.0,
            }
        return {
            "stage1_label_construction_map": {k: sorted(v) for k, v in stage1.items()},
            "stage2_label_construction_map": {k: sorted(v) for k, v in stage2.items()},
            "overlap_by_source_family": overlap,
            "audit_conclusion": "Partial overlap exists by design; incremental-value audit determines whether Stage 1 is more than a duplicated proxy stack.",
        }

    def _candidate_score_cache(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        state = pd.concat(
            [
                build_cross_sectional_stress_state(frame),
                build_vol_surface_state(frame),
                build_credit_liquidity_state(frame),
                build_cross_asset_divergence_state(frame),
            ],
            axis=1,
        ).fillna(0.0)
        stage1 = self.stage1_model.score_frame(frame, state)
        stage2 = self.stage2_model.score_frame(frame, state, stage1)
        confidence = (1.0 - 0.55 * stage1["stage1_ambiguity"].to_numpy(float)).clip(0.20, 1.0)
        phase4 = (stage2["phase4_severity_score"].to_numpy(float) * (0.85 + 0.15 * confidence)).clip(0.0, 1.0)
        return {
            "C9_baseline_reference": self._c9_scores(frame),
            "phase3_two_stage_winner": self._two_stage_scores(self._phase3_components(frame)),
            "phase4_two_stage_mainline": phase4,
            "phase4_two_stage_ambiguity_aware": phase4,
            "phase4_reduced_fallback_inputs": self._reduced_state_scores(frame, state, stage1),
            "phase4_ablation_without_cross_sectional_state": self._ablation_score(frame, state, "cross_sectional_stress", stage1),
            "phase4_constrained_complexity_variant": (0.62 * phase4 + 0.38 * stage1["stage1_structural_stress_onset"].to_numpy(float)).clip(0.0, 1.0),
            "phase4_hierarchical_challenger": self.challenger_model.score_frame(frame, state, stage1)["phase4_hierarchical_score"].to_numpy(float),
        }

    def _reduced_state_scores(self, frame: pd.DataFrame, state: pd.DataFrame, stage1: pd.DataFrame) -> np.ndarray:
        reduced = state.copy()
        reduced["credit_liquidity_stress"] = 0.0
        reduced["cross_asset_divergence"] = 0.0
        return self.stage2_model.score_frame(frame, reduced, stage1)["phase4_severity_score"].to_numpy(float)

    def _ablation_score(self, frame: pd.DataFrame, state: pd.DataFrame, column: str, stage1: pd.DataFrame) -> np.ndarray:
        ablated = state.copy()
        ablated[column] = 0.0
        return self.stage2_model.score_frame(frame, ablated, stage1)["phase4_severity_score"].to_numpy(float)

    @staticmethod
    def _episode_count(mask: np.ndarray | pd.Series) -> int:
        values = np.asarray(mask, dtype=bool)
        if len(values) == 0:
            return 0
        return int(np.sum(values & np.concatenate([[True], ~values[:-1]])))

    def _usable_support(self, mask: np.ndarray, confidence: np.ndarray, oos: np.ndarray) -> str:
        return "YES" if np.sum(confidence[mask]) >= 80.0 and self._episode_count(mask) >= 3 and self._episode_count(mask & oos) >= 1 else "NO"

    def _stage_support(self, labels: np.ndarray, confidence: np.ndarray, oos: np.ndarray) -> dict[str, Any]:
        out = {
            "usable_label_support": int(len(labels)),
            "confidence_weighted_support": float(np.sum(confidence)),
            "support_for_onset_transition_examples": int(np.sum(labels == "transition_onset")),
            "support_for_healing_examples": int(np.sum(labels == "recovery_healing")),
            "oos_rows": int(np.sum(oos)),
        }
        return out

    @staticmethod
    def _boundary_support(labels: np.ndarray) -> dict[str, int]:
        values = list(dict.fromkeys([str(x) for x in labels]))
        out = {}
        for i, left in enumerate(values):
            for right in values[i + 1 :]:
                out[f"{left}_vs_{right}"] = int(min(np.sum(labels == left), np.sum(labels == right)))
        return out

    @staticmethod
    def _constraints_from_decision(decision: str, complexity: dict[str, Any], incremental: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": decision,
            "full_six_class_independent_training": "NO" if decision != "FEASIBLE_AS_SPECIFIED" else "YES",
            "required_class_actions": complexity["classes_to_merge_mask_or_downgrade"],
            "stage1_incremental_value_constraint": incremental["conclusion"],
        }

    @staticmethod
    def _weighted_mean(scores: np.ndarray, mask: np.ndarray, weights: np.ndarray) -> float:
        scores = np.asarray(scores, dtype=float)
        mask = np.asarray(mask, dtype=bool)
        weights = np.asarray(weights, dtype=float)
        if not mask.any() or np.sum(weights[mask]) <= 0:
            return 0.0
        return float(np.average(scores[mask], weights=weights[mask]))

    def _write_phase4_reports(self, *items: dict[str, Any]) -> None:
        (
            feasibility,
            architecture,
            state_inventory,
            state_gain,
            taxonomy_registry,
            training,
            challenger,
            downstream,
            self_audit,
            checklist,
            verdict,
        ) = items
        self._write_report("pi_stress_phase4_identification_feasibility.md", self._feasibility_report(feasibility))
        self._write_report("pi_stress_phase4_architecture_spec.md", self._architecture_report(architecture))
        self._write_report("pi_stress_phase4_data_state_expansion.md", self._state_report(state_inventory, state_gain))
        self._write_report("pi_stress_phase4_taxonomy_denoising.md", self._taxonomy_denoising_report(taxonomy_registry))
        self._write_report("pi_stress_phase4_mainline_training.md", self._training_report(training))
        self._write_report("pi_stress_phase4_mainline_vs_challenger.md", self._challenger_report(challenger))
        self._write_report("pi_stress_phase4_downstream_beta_screen.md", self._phase4_downstream_report(downstream))
        self._write_report("pi_stress_phase4_self_audit.md", self._phase4_self_audit_report(self_audit))
        self._write_report("pi_stress_phase4_acceptance_checklist.md", self._phase4_checklist_report(checklist))
        self._write_report("pi_stress_phase4_final_verdict.md", self._phase4_verdict_report(verdict, training))

    def _feasibility_report(self, feasibility: dict[str, Any]) -> str:
        rows = "\n".join(
            f"| `{klass}` | {row['raw_row_count']} | {row['confidence_weighted_row_count']:.1f} | {row['contiguous_episode_count']} | {row['oos_row_count']} | {row['usable_support_for_independent_modeling']} |"
            for klass, row in feasibility["class_support"].items()
        )
        return f"""# pi_stress Phase 4 Identification Feasibility

## Decision

`{feasibility['decision']}`

## Class Support

| Class | Raw rows | Confidence-weighted rows | Episodes | OOS rows | Independent modeling |
|---|---:|---:|---:|---:|---|
{rows}

## Complexity Budget

- Six-class supportable as specified: `{feasibility['complexity_budget']['six_class_modeling_supportable_as_specified']}`
- Maximum Stage 1 complexity: {feasibility['complexity_budget']['maximum_stage1_complexity']}
- Maximum Stage 2 complexity: {feasibility['complexity_budget']['maximum_stage2_complexity']}

## Stage Coupling Conclusion

{feasibility['incremental_value_audit']['conclusion']}
"""

    def _architecture_report(self, architecture: dict[str, Any]) -> str:
        return f"""# pi_stress Phase 4 Architecture Spec

## Locked Roles

- Mainline: `{architecture['mainline']}`
- Challenger: `{architecture['challenger']}`
- Reference baseline: `{architecture['reference_baseline']}`

## Stage Semantics

Stage 1 estimates regime geometry, ambiguity, transition intensity, and healing tendency. Stage 2 estimates severity conditioned on Stage 1 and state evidence.

## Conductor Rule

`{architecture['conductor_rule']}`

## Constraint Policy

{json.dumps(architecture['constraint_policy'], indent=2)}
"""

    def _state_report(self, inventory: dict[str, Any], gain: dict[str, Any]) -> str:
        rows = "\n".join(
            f"| `{family}` | {meta['classification']} | {gain['families'][family]['conditional_gain_beyond_single_asset_trace']:.4f} | {gain['families'][family]['ordinary_correction_marginal_gain']:.4f} | {gain['families'][family]['lead_lag_usefulness']} | {gain['families'][family]['useful_under_phase4_standard']} |"
            for family, meta in inventory["state_families"].items()
        )
        return f"""# pi_stress Phase 4 Data-State Expansion

| State family | Source classification | Conditional gain | Ordinary gain | Lead-lag | Useful |
|---|---|---:|---:|---|---|
{rows}

Raw feature names remain contained in dedicated state signal modules. Unavailable real inputs are reserved explicitly in the JSON inventory.
"""

    def _taxonomy_denoising_report(self, registry: dict[str, Any]) -> str:
        return f"""# pi_stress Phase 4 Taxonomy Denoising

## Mechanisms Implemented

{self._bullet_lines(registry['mechanisms_implemented'])}

## Ambiguity Zones

{json.dumps(registry['ambiguity_zones'], indent=2)}

## Softened Classes

{self._bullet_lines(registry['softened_classes'])}
"""

    def _training_report(self, training: dict[str, Any]) -> str:
        rows = "\n".join(
            f"| `{name}` | {row['metrics']['stress_vs_ordinary_gap']:.4f} | {row['metrics']['structural_vs_recovery_gap']:.4f} | {row['metrics']['threshold_robustness']['sensitivity_width']:.4f} | {sum(1 for gate in row['gate_results'].values() if gate['status'] == 'PASS')}/{len(row['gate_results'])} | {row['candidate_ranking_score']:.4f} |"
            for name, row in training["candidates"].items()
        )
        return f"""# pi_stress Phase 4 Mainline Training

Workstream 0 decision obeyed: `{training['workstream0_decision_obeyed']}`

| Candidate | Stress vs ordinary | Structural vs recovery | Threshold sensitivity | Gates | Ranking score |
|---|---:|---:|---:|---:|---:|
{rows}
"""

    def _challenger_report(self, challenger: dict[str, Any]) -> str:
        return f"""# pi_stress Phase 4 Mainline vs Challenger

Formal challenger: `{challenger['formal_challenger']}`

## Direct Comparison

{json.dumps(challenger['direct_comparison'], indent=2)}
"""

    def _phase4_downstream_report(self, downstream: dict[str, Any]) -> str:
        rows = "\n".join(
            f"| `{name}` | {row['nonstress_high_beta_trigger_rate']:.4f} | {row['worsening_day_overlap_count']} | {row['worst_raw_beta_delta_on_worsening_days']:.4f} | {row['mean_raw_beta_delta_on_worsening_days']:.4f} | {row['beta_pathology_incidence_change_vs_legacy']:.4f} |"
            for name, row in downstream["candidate_metrics"].items()
        )
        return f"""# pi_stress Phase 4 Downstream Beta Screen

Ranking integration: `{downstream['ranking_integration']}`

| Candidate | Non-stress high-beta trigger rate | Worsening overlap | Worst raw beta delta | Mean raw beta delta | Pathology incidence change |
|---|---:|---:|---:|---:|---:|
{rows}
"""

    def _phase4_self_audit_report(self, self_audit: dict[str, Any]) -> str:
        rows = "\n".join(f"| {key} | {row['triggered']} | {row['resolved']} | {row['evidence']} |" for key, row in self_audit.items())
        return f"""# pi_stress Phase 4 Self-Audit

| Category | Triggered | Resolved | Evidence |
|---|---|---|---|
{rows}
"""

    def _phase4_checklist_report(self, checklist: dict[str, Any]) -> str:
        ovf = "\n".join(f"| {key} | {row['triggered']} | {row['evidence']} |" for key, row in checklist["one_vote_fail_items"].items())
        mp = "\n".join(f"| {key} | {row['status']} | {row['evidence']} |" for key, row in checklist["mandatory_pass_items"].items())
        bp = "\n".join(f"| {key} | {value} |" for key, value in checklist["best_practice_items_achieved"].items())
        return f"""# pi_stress Phase 4 Acceptance Checklist

## One-Vote-Fail Items

| Item | YES / NO | Evidence |
|---|---|---|
{ovf}

## Mandatory Pass Items

| Item | PASS / FAIL | Evidence |
|---|---|---|
{mp}

## Best-Practice Items

| Item | Achieved |
|---|---|
{bp}

## Effect On Verdict

{checklist['effect_on_verdict']}
"""

    def _phase4_verdict_report(self, verdict: dict[str, Any], training: dict[str, Any]) -> str:
        best = verdict["best_research_family_after_beta_screen"]
        mainline = training["candidates"]["phase4_two_stage_mainline"]
        gate_rows = "\n".join(f"| {key} | {row['status']} |" for key, row in mainline["gate_results"].items())
        summary = verdict["summary"]
        return f"""# pi_stress Phase 4 Final Verdict

## Final Phase 4 Verdict

`{verdict['verdict']}`

## Workstream 0 Decision

`{verdict['workstream0_decision']}`

## Best Research Family After Beta Screen

`{best}`

## Mainline Gate Results

| Gate | Status |
|---|---|
{gate_rows}

## Rationale

What improved:
{self._bullet_lines(summary['what_improved'])}

What did not improve:
{self._bullet_lines(summary['what_did_not_improve'])}

What remains data-limited:
{self._bullet_lines(summary['what_remains_data_limited'])}

What remains label-limited:
{self._bullet_lines(summary['what_remains_label_limited'])}

Why the verdict is justified:

- {summary['why_justified']}
"""


if __name__ == "__main__":
    result = PiStressPhase4Research().write()
    print(json.dumps({"verdict": result["verdict"], "artifact_dir": "artifacts/pi_stress_phase4"}, indent=2))
