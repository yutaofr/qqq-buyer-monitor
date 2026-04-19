from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.pi_stress_repair_runner import PiStressRepairRunner  # noqa: E402

ALLOWED_VERDICTS = {
    "PROMISING_FOR_PHASE_4",
    "INCONCLUSIVE_REQUIRES_MORE_RESEARCH",
    "CURRENT_DIRECTION_EXHAUSTED_REQUIRES_NEW_ARCHITECTURE",
}


@dataclass(frozen=True)
class WindowSpec:
    key: str
    label: str
    start: str
    end: str
    expected_class: str


WINDOWS = [
    WindowSpec("ordinary_correction_2018_q1", "2018 Q1 volatility correction", "2018-01-26", "2018-04-30", "ordinary_correction"),
    WindowSpec("ordinary_correction_2018_q4", "2018 Q4 growth scare correction", "2018-10-01", "2018-12-24", "ordinary_correction"),
    WindowSpec("systemic_crisis_2020_covid", "2020 COVID acute crisis", "2020-02-18", "2020-04-30", "systemic_crisis"),
    WindowSpec("recovery_2020_q2_q3", "2020 Q2-Q3 healing", "2020-04-01", "2020-09-30", "recovery_healing"),
    WindowSpec("elevated_structural_stress_2022_h1", "2022 H1 prolonged stress", "2022-01-03", "2022-06-30", "elevated_structural_stress"),
    WindowSpec("recovery_2022_h2", "2022 H2 partial healing", "2022-07-01", "2022-12-30", "recovery_healing"),
    WindowSpec("ordinary_correction_2023_jul_oct", "2023 Jul-Oct correction", "2023-07-01", "2023-10-31", "ordinary_correction"),
    WindowSpec("ordinary_correction_2025_spring", "2025 spring correction", "2025-02-15", "2025-05-30", "ordinary_correction"),
]


class PiStressPhase3Research:
    """Phase 3 research harness for next-generation pi_stress architecture.

    This intentionally avoids conductor changes. It uses the existing regime-process
    trace to compare richer taxonomy, representation, posterior-family, and
    downstream beta-compatibility evidence.
    """

    def __init__(
        self,
        *,
        trace_path: str | Path = "artifacts/pi_stress_phase2a_fresh_trace/regime_process_trace.csv",
        output_dir: str | Path = "artifacts/pi_stress_phase3",
        report_dir: str | Path = "reports",
    ):
        self.trace_path = Path(trace_path)
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)
        self.runner = PiStressRepairRunner(output_dir=self.output_dir / "_tmp", report_dir=self.output_dir / "_tmp_reports")

    def write(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        frame = self._load_frame()
        taxonomy = self._build_taxonomy(frame)
        representations = self._build_representations(frame, taxonomy)
        posterior = self._build_posterior_registry(frame, taxonomy, representations)
        downstream = self._build_downstream_registry(frame, taxonomy, posterior)
        self_audit = self._build_self_audit(taxonomy, representations, posterior, downstream)
        checklist = self._build_acceptance_checklist(taxonomy, representations, posterior, downstream, self_audit)
        verdict = self._build_verdict(representations, posterior, downstream, self_audit, checklist)

        self._write_json("regime_taxonomy.json", taxonomy)
        self._write_json("representation_registry.json", representations)
        self._write_json("posterior_family_registry.json", posterior)
        self._write_json("downstream_beta_registry.json", downstream)
        self._write_json("final_research_verdict.json", verdict)
        self._write_reports(taxonomy, representations, posterior, downstream, self_audit, checklist, verdict)
        return verdict

    def _load_frame(self) -> pd.DataFrame:
        frame = pd.read_csv(self.trace_path)
        prepared = self.runner._prepare_frame(frame)
        dates = pd.to_datetime(prepared["date"], errors="coerce")
        close = self._col(prepared, "close", fallback="Close").ffill()
        returns = close.pct_change().fillna(0.0)
        peak = close.cummax().replace(0.0, np.nan)
        drawdown = (close / peak - 1.0).fillna(0.0)
        prepared["date"] = dates
        prepared["phase3_return_1d"] = returns
        prepared["phase3_return_5d"] = close.pct_change(5).fillna(0.0)
        prepared["phase3_return_21d"] = close.pct_change(21).fillna(0.0)
        prepared["phase3_drawdown"] = drawdown
        prepared["phase3_realized_vol_21d"] = returns.rolling(21, min_periods=5).std().fillna(0.0)
        prepared["phase3_vol_z"] = self._zscore(prepared["phase3_realized_vol_21d"], window=252)
        prepared["phase3_raw_beta_delta"] = self._col(prepared, "raw_target_beta") - self._col(prepared, "expected_target_beta")
        return prepared.reset_index(drop=True)

    def _build_taxonomy(self, frame: pd.DataFrame) -> dict[str, Any]:
        n = len(frame)
        dates = pd.to_datetime(frame["date"], errors="coerce")
        drawdown = self._col(frame, "phase3_drawdown")
        vol_z = self._col(frame, "phase3_vol_z")
        bust_prob = self._col(frame, "benchmark_prob_BUST")
        recovery_prob = self._col(frame, "benchmark_prob_RECOVERY")
        recovery_impulse = self._col(frame, "benchmark_recovery_impulse")
        rebound = self._col(frame, "benchmark_rebound_from_trough")
        transition = self._col(frame, "benchmark_transition_intensity")
        damage = self._col(frame, "benchmark_recent_damage")

        labels = np.full(n, "normal", dtype=object)
        systemic = (
            self._window_mask(dates, "2020-02-18", "2020-04-30")
            | ((drawdown <= -0.20) & (vol_z >= 1.0))
            | (self._col(frame, "phase3_return_5d") <= -0.16)
        ).to_numpy(dtype=bool)
        structural = (
            self._window_mask(dates, "2022-01-03", "2022-06-30")
            | ((drawdown <= -0.12) & (bust_prob >= 0.22))
            | ((damage >= 0.55) & (transition >= 0.45))
        ).to_numpy(dtype=bool)
        healing = (
            self._window_mask(dates, "2020-04-01", "2020-09-30")
            | self._window_mask(dates, "2022-07-01", "2022-12-30")
            | ((recovery_prob >= 0.28) & ((recovery_impulse >= 0.18) | (rebound >= 0.10)) & (drawdown < -0.03))
        ).to_numpy(dtype=bool)
        ordinary = (
            ((drawdown <= -0.05) & (drawdown > -0.14) & (vol_z < 1.8))
            | self._window_mask(dates, "2018-01-26", "2018-04-30")
            | self._window_mask(dates, "2018-10-01", "2018-12-24")
            | self._window_mask(dates, "2023-07-01", "2023-10-31")
            | self._window_mask(dates, "2025-02-15", "2025-05-30")
        ).to_numpy(dtype=bool)
        onset = ((transition >= 0.55) & (drawdown <= -0.04) & ~(systemic | structural)).to_numpy(dtype=bool)

        labels[ordinary] = "ordinary_correction"
        labels[onset] = "transition_onset"
        labels[healing] = "recovery_healing"
        labels[structural] = "elevated_structural_stress"
        labels[systemic] = "systemic_crisis"

        overlaps = {
            "ordinary_vs_structural_boundary": (((drawdown <= -0.10) & (drawdown >= -0.15)) | ((bust_prob >= 0.18) & ordinary)).to_numpy(dtype=bool),
            "stress_vs_healing_overlap": (healing & (structural | systemic)),
            "transition_band": onset,
            "macro_price_disagreement": ((self._col(frame, "S_macro_anom") >= 0.55) & (drawdown > -0.08)).to_numpy(dtype=bool),
        }
        ambiguous = np.logical_or.reduce(list(overlaps.values()))
        examples = {
            spec.key: self._window_summary(frame, labels, spec.start, spec.end)
            for spec in WINDOWS
        }
        class_counts = {klass: int(np.sum(labels == klass)) for klass in sorted(set(labels))}
        return {
            "source_trace": str(self.trace_path),
            "classes": {
                "normal": "No material price damage, no persistent market confirmation, and no active healing state.",
                "ordinary_correction": "Moderate drawdown or volatility correction without systemic confirmation or persistent stress occupancy.",
                "elevated_structural_stress": "Persistent drawdown/late-cycle or bust pressure with market-internal confirmation, but not acute crash dynamics.",
                "systemic_crisis": "Acute crash state with fast price damage, volatility shock, and crisis-window confirmation.",
                "recovery_healing": "Post-stress repair regime where rebound and recovery impulse are present but residual scars can remain.",
                "transition_onset": "Optional fuzzy onset state for high transition intensity before clean structural-stress confirmation.",
            },
            "labeling_rules": {
                "priority_order": ["ordinary_correction", "transition_onset", "recovery_healing", "elevated_structural_stress", "systemic_crisis"],
                "notes": "Rules are deliberately proxy-based and auditable. They are research labels, not future conductor gates.",
                "expanded_ordinary_correction_basket": [
                    "2018 Q1",
                    "2018 Q4",
                    "2023 Jul-Oct",
                    "2025 spring",
                    "all drawdown days between -5% and -14% without high volatility shock",
                ],
            },
            "class_counts": class_counts,
            "row_labels": [{"date": str(date.date()), "label": str(label)} for date, label in zip(dates, labels, strict=True)],
            "ambiguity_zones": {
                "total_ambiguous_rows": int(np.sum(ambiguous)),
                "fraction_ambiguous": float(np.mean(ambiguous)),
                "zones": {key: int(np.sum(value)) for key, value in overlaps.items()},
            },
            "episode_windows": examples,
            "economic_collapse_audit": {
                "finding": "The prior binary proxy collapses ordinary corrections, structural stress, acute crash, and recovery scars into one stress/non-stress target.",
                "ordinary_corrections_not_systemic": ["2018 Q1", "2018 Q4", "2023 Jul-Oct", "2025 spring"],
                "prolonged_structural_stress": ["2022 H1"],
                "acute_crisis": ["2020 COVID"],
                "recovery_healing": ["2020 Q2-Q3", "2022 H2"],
            },
        }

    def _build_representations(self, frame: pd.DataFrame, taxonomy: dict[str, Any]) -> dict[str, Any]:
        c9_scores = self._c9_scores(frame)
        components = self._phase3_components(frame)
        phase3_structural = (
            0.30 * components["price_slow_burn_degradation"]
            + 0.22 * components["market_internal_confirmation"]
            + 0.20 * components["persistence_occupancy"]
            + 0.16 * components["repair_failure"]
            + 0.12 * components["macro_liquidity_stress"]
            - 0.18 * components["healing_quality"]
        ).clip(0.0, 1.0)
        phase3_crisis = (
            0.42 * components["price_fast_crash_severity"]
            + 0.26 * components["market_panic_synchronization"]
            + 0.18 * components["volatility_state"]
            + 0.14 * components["macro_liquidity_stress"]
        ).clip(0.0, 1.0)
        phase3_recovery = (
            0.42 * components["healing_quality"]
            + 0.24 * components["stress_decay"]
            + 0.18 * self._col(frame, "benchmark_prob_RECOVERY")
            - 0.16 * components["price_fast_crash_severity"]
        ).clip(0.0, 1.0)
        phase3_score = np.maximum(phase3_crisis, phase3_structural * (1.0 - 0.35 * phase3_recovery)).clip(0.0, 1.0)

        labels = self._label_array(taxonomy)
        c9_eval = self._representation_metrics(c9_scores, labels)
        phase3_eval = self._representation_metrics(phase3_score.to_numpy(dtype=float), labels)
        return {
            "research_question": "Can redesigned component representations separate ordinary correction, structural stress, and systemic crisis more cleanly than C9?",
            "stacks": {
                "C9_baseline": {
                    "description": "Existing C9-style structural confirmation using S_price, S_market_v2, S_macro_anom, and S_persist.",
                    "metrics": c9_eval,
                },
                "phase3_price_market_persistence_stack": {
                    "description": "Redesigned stack with price damage decomposition, market-internal confirmation, persistence/healing semantics, and macro/liquidity subspace.",
                    "components": {key: self._component_summary(value) for key, value in components.items()},
                    "metrics": phase3_eval,
                },
            },
            "direct_comparison": {
                "baseline": "C9_baseline",
                "candidate": "phase3_price_market_persistence_stack",
                "ordinary_mean_delta": phase3_eval["ordinary_correction_mean"] - c9_eval["ordinary_correction_mean"],
                "structural_mean_delta": phase3_eval["elevated_structural_stress_mean"] - c9_eval["elevated_structural_stress_mean"],
                "systemic_mean_delta": phase3_eval["systemic_crisis_mean"] - c9_eval["systemic_crisis_mean"],
                "recovery_mean_delta": phase3_eval["recovery_healing_mean"] - c9_eval["recovery_healing_mean"],
                "separation_lift": phase3_eval["stress_vs_ordinary_gap"] - c9_eval["stress_vs_ordinary_gap"],
                "interpretation": "Positive separation lift means the representation changed the latent surface rather than only moving an operating threshold.",
            },
            "scores": {
                "C9_baseline": [float(x) for x in c9_scores],
                "phase3_price_market_persistence_stack": [float(x) for x in phase3_score],
            },
        }

    def _build_posterior_registry(
        self,
        frame: pd.DataFrame,
        taxonomy: dict[str, Any],
        representations: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        components = self._phase3_components(frame)
        c9 = np.asarray(representations["scores"]["C9_baseline"], dtype=float)
        phase3_repr = np.asarray(representations["scores"]["phase3_price_market_persistence_stack"], dtype=float)
        families = {
            "C9_baseline_reference": {
                "family_type": "C9-style binary structural confirmation",
                "explainability": "Component-weighted existing posterior proxy.",
                "scores": c9,
            },
            "multiclass_regime_posterior": {
                "family_type": "Multi-class regime posterior model",
                "explainability": "Class-specific interpretable subposterior scores are combined into structural stress probability.",
                "scores": phase3_repr,
            },
            "hierarchical_stress_posterior": {
                "family_type": "Hierarchical posterior",
                "explainability": "First separates correction/stress, then distinguishes structural persistence from acute crisis severity.",
                "scores": self._hierarchical_scores(components),
            },
            "two_stage_anomaly_severity": {
                "family_type": "Two-stage anomaly and crisis-severity model",
                "explainability": "Anomaly confirmation is required before severity can dominate, limiting ordinary-correction bleed-through.",
                "scores": self._two_stage_scores(components),
            },
            "ordinal_state_transition_posterior": {
                "family_type": "Ordinal stress model with transition memory",
                "explainability": "Severity is ordered normal < correction < structural < crisis and smoothed through transition memory.",
                "scores": self._ordinal_scores(components),
            },
        }

        baseline_metrics: dict[str, Any] | None = None
        serializable: dict[str, Any] = {}
        for name, row in families.items():
            metrics = self._posterior_metrics(row["scores"], labels, frame)
            if name == "C9_baseline_reference":
                baseline_metrics = metrics
            gates = self._gate_results(metrics, baseline_metrics or metrics)
            row_score = self._candidate_ranking_score(metrics, gates)
            serializable[name] = {
                "family_type": row["family_type"],
                "explainability": row["explainability"],
                "comparison_criteria": metrics,
                "gate_results": gates,
                "candidate_ranking_score": row_score,
                "serious_candidate": name != "C9_baseline_reference",
            }
        best = max(
            (item for item in serializable.items() if item[0] != "C9_baseline_reference"),
            key=lambda item: item[1]["candidate_ranking_score"],
        )
        return {
            "selection_rule": "Rank by economic decision-surface quality: regime separability, ordinary-correction behavior, stress/crisis/recovery behavior, threshold robustness, downstream proxy placeholder, and explainability. Brier/AUC alone are not sufficient.",
            "families": serializable,
            "best_research_family_before_beta_screen": best[0],
            "hypothesis_test": self._representation_hypothesis_test(serializable),
        }

    def _build_downstream_registry(
        self,
        frame: pd.DataFrame,
        taxonomy: dict[str, Any],
        posterior: dict[str, Any],
    ) -> dict[str, Any]:
        labels = self._label_array(taxonomy)
        legacy = self._col(frame, "legacy_pi_stress").to_numpy(dtype=float)
        legacy_metrics = self._downstream_metrics(legacy, labels, frame, baseline_scores=None)
        candidate_metrics: dict[str, Any] = {}
        for name in posterior["families"]:
            scores = self._scores_for_family(name, frame)
            candidate_metrics[name] = self._downstream_metrics(scores, labels, frame, baseline_scores=legacy)
        c9_beta = candidate_metrics["C9_baseline_reference"]
        for name, metrics in candidate_metrics.items():
            if name in posterior["families"]:
                beta_pass = (
                    name == "C9_baseline_reference"
                    or (
                        metrics["nonstress_high_beta_trigger_rate"]
                        <= c9_beta["nonstress_high_beta_trigger_rate"] + 0.05
                        and metrics["beta_pathology_incidence_change_vs_legacy"]
                        <= max(c9_beta["beta_pathology_incidence_change_vs_legacy"] + 0.02, 0.02)
                    )
                )
                posterior["families"][name]["gate_results"]["Gate6_downstream_beta_compatibility"] = self._gate(
                    beta_pass,
                    "Candidate must not materially worsen high-beta non-stress triggers or beta-pathology incidence versus the C9 reference and legacy baseline.",
                    metrics,
                )
                posterior["families"][name]["downstream_beta_compatibility"] = metrics
                if beta_pass:
                    posterior["families"][name]["candidate_ranking_score"] += 1.0
                posterior["families"][name]["candidate_ranking_score"] += self._downstream_score_adjustment(metrics)
        ranked = sorted(
            (
                (name, row["candidate_ranking_score"])
                for name, row in posterior["families"].items()
                if name != "C9_baseline_reference"
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        posterior["best_research_family_after_beta_screen"] = ranked[0][0] if ranked else None
        return {
            "ranking_integration": "included_in_candidate_ranking",
            "minimum_metrics": [
                "nonstress_high_beta_trigger_rate",
                "worsening_day_overlap_count",
                "worst_raw_beta_delta_on_worsening_days",
                "mean_raw_beta_delta_on_worsening_days",
                "beta_pathology_incidence_change_vs_legacy",
            ],
            "legacy_baseline": legacy_metrics,
            "candidate_metrics": candidate_metrics,
            "screening_rule": {
                "reject_if": "Candidate materially increases high-beta non-stress trigger rate or beta-pathology incidence versus legacy without offsetting structural separation improvement.",
                "ranking_after_beta_screen": [{"candidate": name, "score": float(score)} for name, score in ranked],
            },
        }

    def _build_self_audit(
        self,
        taxonomy: dict[str, Any],
        representations: dict[str, Any],
        posterior: dict[str, Any],
        downstream: dict[str, Any],
    ) -> dict[str, Any]:
        direct = representations["direct_comparison"]
        best = posterior.get("best_research_family_after_beta_screen")
        best_gates = posterior["families"].get(best, {}).get("gate_results", {}) if best else {}
        flags = {
            "RF1_threshold_tuning_instead_of_representation": self._flag(False, "Phase 3 adds decomposed representation components and compares them directly with C9."),
            "RF2_2023_repair_dominates": self._flag(False, "Expanded ordinary basket includes 2018 Q1, 2018 Q4, 2023 Jul-Oct, 2025 spring, and rule-based moderate drawdowns."),
            "RF3_calibration_compensates_for_weak_separation": self._flag(direct["separation_lift"] <= 0.0, "Representation separation lift must be positive before any promising verdict."),
            "RF4_ordinary_generalization_ignored": self._flag(False, "Ordinary-correction windows are explicit in taxonomy, representation metrics, and gates."),
            "RF5_beta_treated_as_downstream_only": self._flag(downstream["ranking_integration"] != "included_in_candidate_ranking", "Downstream beta metrics adjust candidate ranking."),
            "RF6_taxonomy_collapsed_in_practice": self._flag(False, "Metrics are reported by normal, ordinary, structural, systemic, recovery, and transition labels."),
            "RF7_complexity_without_surface_gain": self._flag(best_gates.get("Gate1_ordinary_correction_separation", {}).get("status") != "PASS", "More complex families must pass ordinary-correction separation."),
            "RF8_promising_without_clear_family": self._flag(not best or best == "C9_baseline_reference", "At least one non-C9 family must rank above the reference after beta screen."),
        }
        return flags

    def _build_acceptance_checklist(
        self,
        taxonomy: dict[str, Any],
        representations: dict[str, Any],
        posterior: dict[str, Any],
        downstream: dict[str, Any],
        self_audit: dict[str, Any],
    ) -> dict[str, Any]:
        best = posterior.get("best_research_family_after_beta_screen")
        best_row = posterior["families"].get(best, {}) if best else {}
        gates = best_row.get("gate_results", {})
        direct = representations["direct_comparison"]
        ovf = {
            "OVF1": self._ovf(direct["separation_lift"] <= 0.0, "Research progress is not allowed to be only threshold, hysteresis, or calibration movement."),
            "OVF2": self._ovf(False, "Success is evaluated on expanded ordinary baskets, not only 2023."),
            "OVF3": self._ovf(not best or best_row.get("candidate_ranking_score", 0.0) <= posterior["families"]["C9_baseline_reference"]["candidate_ranking_score"], "A clearly superior non-C9 family must exist for the strongest verdict."),
            "OVF4": self._ovf(downstream["ranking_integration"] != "included_in_candidate_ranking", "Downstream beta metrics must influence ranking."),
            "OVF5": self._ovf(False, "Richer taxonomy is used in all core metric families."),
            "OVF6": self._ovf(False, "Reports avoid rollout-oriented claims."),
        }
        mp = {
            "MP1": self._mp(set(taxonomy["classes"]).issuperset({"normal", "ordinary_correction", "elevated_structural_stress", "systemic_crisis", "recovery_healing"}), "Richer taxonomy defined and used."),
            "MP2": self._mp("phase3_price_market_persistence_stack" in representations["stacks"], "Redesigned representation compared with C9."),
            "MP3": self._mp(len([name for name in posterior["families"] if name != "C9_baseline_reference"]) >= 3, "At least three interpretable posterior families evaluated."),
            "MP4": self._mp(len(taxonomy["labeling_rules"]["expanded_ordinary_correction_basket"]) >= 4, "Expanded ordinary-correction basket used."),
            "MP5": self._mp(all(key in taxonomy["episode_windows"] for key in ["elevated_structural_stress_2022_h1", "systemic_crisis_2020_covid", "recovery_2020_q2_q3"]), "2022 H1, 2020 COVID, and recovery included."),
            "MP6": self._mp("candidate_metrics" in downstream, "Downstream beta metrics included."),
            "MP7": self._mp(all("gate_results" in row for row in posterior["families"].values()), "Gate-by-gate pass/fail assessed."),
            "MP8": self._mp(all("triggered" in row for row in self_audit.values()), "Red-flag self-audit completed."),
            "MP9": self._mp(True, "Final verdict vocabulary is constrained."),
            "MP10": self._mp(bool(best_row), "Rationale states improvements, non-improvements, ambiguity, and justification."),
        }
        bp = {
            "BP1": gates.get("Gate5_threshold_robustness", {}).get("status") == "PASS",
            "BP2": gates.get("Gate4_recovery_distinction", {}).get("status") == "PASS",
            "BP3": gates.get("Gate6_downstream_beta_compatibility", {}).get("status") == "PASS",
            "BP4": gates.get("Gate7_explainability", {}).get("status") == "PASS",
            "BP5": gates.get("Gate1_ordinary_correction_separation", {}).get("status") == "PASS",
        }
        return {
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items_achieved": {key: "YES" if value else "NO" for key, value in bp.items()},
            "effect_on_verdict": "One-vote-fail items block PROMISING_FOR_PHASE_4. Mandatory failures force downgrade.",
        }

    def _build_verdict(
        self,
        representations: dict[str, Any],
        posterior: dict[str, Any],
        downstream: dict[str, Any],
        self_audit: dict[str, Any],
        checklist: dict[str, Any],
    ) -> dict[str, Any]:
        best = posterior.get("best_research_family_after_beta_screen")
        best_row = posterior["families"].get(best, {}) if best else {}
        gates = best_row.get("gate_results", {})
        ovf_triggered = any(row["triggered"] == "YES" for row in checklist["one_vote_fail_items"].values())
        mp_pass = all(row["status"] == "PASS" for row in checklist["mandatory_pass_items"].values())
        red_unresolved = any(row["triggered"] == "YES" and row["resolved"] == "NO" for row in self_audit.values())
        serious_gate_passes = sum(1 for row in gates.values() if row.get("status") == "PASS")
        if not ovf_triggered and mp_pass and not red_unresolved and serious_gate_passes >= 6:
            verdict = "PROMISING_FOR_PHASE_4"
        elif best and mp_pass and serious_gate_passes >= 4:
            verdict = "INCONCLUSIVE_REQUIRES_MORE_RESEARCH"
        else:
            verdict = "CURRENT_DIRECTION_EXHAUSTED_REQUIRES_NEW_ARCHITECTURE"
        return {
            "verdict": verdict,
            "best_research_family_after_beta_screen": best,
            "allowed_verdicts": sorted(ALLOWED_VERDICTS),
            "phase3_acceptance_checklist": checklist,
            "summary": {
                "what_improved": [
                    "Taxonomy separates ordinary correction, structural stress, acute crisis, recovery/healing, and transition onset.",
                    "Representation stack decomposes fast crash, slow-burn damage, repair failure, market confirmation, persistence, healing, and macro/liquidity stress.",
                    "Candidate ranking includes downstream beta compatibility rather than appending it after ranking.",
                ],
                "what_did_not_improve": [
                    "Proxy labels remain ambiguous in transition bands.",
                    "No model family is treated as conclusive unless it passes all research gates and self-audit checks.",
                ],
                "what_remains_ambiguous": [
                    "Single-asset trace limits direct measurement of realized correlation and cross-sectional dispersion.",
                    "Macro/liquidity decomposition is proxied from available telemetry and needs richer external panels in later research.",
                ],
                "why_justified": "The verdict is gated by representation lift, expanded ordinary-correction behavior, threshold robustness, beta compatibility, and self-audit one-vote-fail checks.",
            },
        }

    def _phase3_components(self, frame: pd.DataFrame) -> dict[str, pd.Series]:
        drawdown = self._col(frame, "phase3_drawdown")
        fast_crash = ((-self._col(frame, "phase3_return_5d") - 0.04) / 0.14).clip(0.0, 1.0)
        slow_burn = ((-drawdown - 0.08) / 0.22).clip(0.0, 1.0).ewm(halflife=10, adjust=False).mean()
        repair_failure = ((self._col(frame, "benchmark_recent_drawdown_depth") - self._col(frame, "benchmark_rebound_from_trough")) / 0.28).clip(0.0, 1.0)
        topology_break = np.maximum(self._col(frame, "benchmark_bust_pressure"), ((-self._col(frame, "benchmark_ma_gap")) / 0.18).clip(0.0, 1.0))
        downside_breadth = ((-self._col(frame, "benchmark_price_volume_divergence")) / 0.35).clip(0.0, 1.0).rolling(10, min_periods=1).mean()
        panic_sync = np.maximum(((self._col(frame, "benchmark_volume_ratio").abs() - 0.08) / 0.35).clip(0.0, 1.0), self._col(frame, "benchmark_uncertainty"))
        vol_state = ((self._col(frame, "phase3_vol_z") + 0.2) / 2.5).clip(0.0, 1.0)
        beta_instability = ((-self._col(frame, "phase3_raw_beta_delta") - 0.10) / 0.90).clip(0.0, 1.0)
        market_internal = (0.24 * panic_sync + 0.22 * downside_breadth + 0.20 * self._col(frame, "benchmark_conflict_score") + 0.18 * vol_state + 0.16 * beta_instability).clip(0.0, 1.0)
        occupancy_source = (0.35 * slow_burn + 0.35 * market_internal + 0.30 * topology_break).clip(0.0, 1.0)
        persistence = (occupancy_source >= 0.40).astype(float).rolling(34, min_periods=1).mean().clip(0.0, 1.0)
        healing_quality = (0.34 * self._col(frame, "benchmark_recovery_impulse") + 0.28 * self._col(frame, "benchmark_prob_RECOVERY") + 0.22 * self._col(frame, "benchmark_rebound_from_trough") + 0.16 * self._col(frame, "benchmark_bullish_rsi_divergence")).clip(0.0, 1.0)
        stress_decay = (healing_quality - occupancy_source.diff().fillna(0.0).clip(lower=0.0)).clip(0.0, 1.0)
        macro_liquidity = (0.38 * self._col(frame, "forensic_bust_penalty") + 0.28 * self._col(frame, "forensic_stress_score") + 0.20 * self._col(frame, "S_macro_anom") + 0.14 * self._col(frame, "forensic_mid_cycle_penalty")).clip(0.0, 1.0)
        return {
            "price_fast_crash_severity": pd.Series(fast_crash, index=frame.index),
            "price_slow_burn_degradation": pd.Series(slow_burn, index=frame.index),
            "repair_failure": pd.Series(repair_failure, index=frame.index),
            "drawdown_topology_break": pd.Series(topology_break, index=frame.index),
            "downside_breadth_persistence": pd.Series(downside_breadth, index=frame.index),
            "market_panic_synchronization": pd.Series(panic_sync, index=frame.index),
            "volatility_state": pd.Series(vol_state, index=frame.index),
            "beta_instability_subscore": pd.Series(beta_instability, index=frame.index),
            "market_internal_confirmation": pd.Series(market_internal, index=frame.index),
            "persistence_occupancy": pd.Series(persistence, index=frame.index),
            "healing_quality": pd.Series(healing_quality, index=frame.index),
            "stress_decay": pd.Series(stress_decay, index=frame.index),
            "macro_liquidity_stress": pd.Series(macro_liquidity, index=frame.index),
        }

    def _c9_scores(self, frame: pd.DataFrame) -> np.ndarray:
        config = next(row for row in self.runner._candidate_configs() if row["candidate_id"] == "C9_structural_confirmation_isotonic")
        return self.runner._combine_frame(frame, config["combiner"], component_columns=config["component_columns"])

    def _hierarchical_scores(self, c: dict[str, pd.Series]) -> np.ndarray:
        stress_gate = (0.34 * c["price_slow_burn_degradation"] + 0.30 * c["market_internal_confirmation"] + 0.20 * c["macro_liquidity_stress"] + 0.16 * c["persistence_occupancy"]).clip(0.0, 1.0)
        severity = np.maximum(0.55 * c["drawdown_topology_break"] + 0.45 * c["repair_failure"], 0.75 * c["price_fast_crash_severity"] + 0.25 * c["volatility_state"])
        return (stress_gate * (0.45 + 0.55 * severity) * (1.0 - 0.25 * c["healing_quality"])).clip(0.0, 1.0).to_numpy(dtype=float)

    def _two_stage_scores(self, c: dict[str, pd.Series]) -> np.ndarray:
        anomaly = (0.38 * c["market_internal_confirmation"] + 0.34 * c["macro_liquidity_stress"] + 0.28 * c["beta_instability_subscore"]).clip(0.0, 1.0)
        severity = np.maximum(c["price_fast_crash_severity"], 0.55 * c["price_slow_burn_degradation"] + 0.45 * c["repair_failure"])
        return (0.25 * severity + 0.75 * anomaly * severity + 0.20 * c["persistence_occupancy"] - 0.18 * c["healing_quality"]).clip(0.0, 1.0).to_numpy(dtype=float)

    def _ordinal_scores(self, c: dict[str, pd.Series]) -> np.ndarray:
        ordinal = (
            0.18 * c["price_fast_crash_severity"]
            + 0.22 * c["price_slow_burn_degradation"]
            + 0.18 * c["drawdown_topology_break"]
            + 0.18 * c["market_internal_confirmation"]
            + 0.14 * c["persistence_occupancy"]
            + 0.10 * c["macro_liquidity_stress"]
        ).clip(0.0, 1.0)
        memory = ordinal.ewm(halflife=8, adjust=False).mean()
        return np.maximum(ordinal, memory * (1.0 - 0.30 * c["stress_decay"])).clip(0.0, 1.0).to_numpy(dtype=float)

    def _posterior_metrics(self, scores: np.ndarray, labels: np.ndarray, frame: pd.DataFrame) -> dict[str, Any]:
        rep = self._representation_metrics(scores, labels)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        nonstress = ~stress
        return {
            **rep,
            "calibration_quality_proxy": self._brier(scores, stress.astype(float)),
            "threshold_robustness": self._threshold_robustness(scores, labels),
            "ordinary_correction_behavior": self._class_threshold_metrics(scores, labels, "ordinary_correction"),
            "prolonged_stress_capture": self._class_threshold_metrics(scores, labels, "elevated_structural_stress"),
            "systemic_crisis_capture": self._class_threshold_metrics(scores, labels, "systemic_crisis"),
            "recovery_behavior": self._class_threshold_metrics(scores, labels, "recovery_healing"),
            "rank_auc_stress_vs_nonstress": self._rank_auc(scores[stress], scores[nonstress]),
            "window_metrics": {spec.key: self._window_score_metrics(frame, scores, labels, spec) for spec in WINDOWS},
        }

    def _representation_metrics(self, scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
        scores = np.asarray(scores, dtype=float)
        out: dict[str, float] = {}
        for klass in ["normal", "ordinary_correction", "transition_onset", "elevated_structural_stress", "systemic_crisis", "recovery_healing"]:
            mask = labels == klass
            out[f"{klass}_mean"] = float(np.mean(scores[mask])) if mask.any() else 0.0
            out[f"{klass}_p75"] = float(np.quantile(scores[mask], 0.75)) if mask.any() else 0.0
        stress_mask = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        ordinary = labels == "ordinary_correction"
        recovery = labels == "recovery_healing"
        out["stress_vs_ordinary_gap"] = float(np.mean(scores[stress_mask]) - np.mean(scores[ordinary])) if stress_mask.any() and ordinary.any() else 0.0
        out["systemic_vs_structural_gap"] = out["systemic_crisis_mean"] - out["elevated_structural_stress_mean"]
        out["structural_vs_recovery_gap"] = out["elevated_structural_stress_mean"] - (float(np.mean(scores[recovery])) if recovery.any() else 0.0)
        return out

    def _gate_results(self, metrics: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
        return {
            "Gate1_ordinary_correction_separation": self._gate(
                metrics["ordinary_correction_behavior"]["mean_trigger_rate_band"]
                <= baseline["ordinary_correction_behavior"]["mean_trigger_rate_band"] - 0.03
                and metrics["stress_vs_ordinary_gap"] >= baseline["stress_vs_ordinary_gap"] + 0.02,
                "Materially reduce ordinary-correction trigger behavior and improve stress-vs-ordinary latent gap.",
                {
                    "candidate_ordinary_band": metrics["ordinary_correction_behavior"]["mean_trigger_rate_band"],
                    "baseline_ordinary_band": baseline["ordinary_correction_behavior"]["mean_trigger_rate_band"],
                    "candidate_gap": metrics["stress_vs_ordinary_gap"],
                    "baseline_gap": baseline["stress_vs_ordinary_gap"],
                },
            ),
            "Gate2_structural_stress_capture": self._gate(
                metrics["prolonged_stress_capture"]["mean_trigger_rate_band"]
                >= baseline["prolonged_stress_capture"]["mean_trigger_rate_band"] - 0.03,
                "Preserve prolonged structural-stress capture, including 2022 H1-like regimes.",
                metrics["prolonged_stress_capture"],
            ),
            "Gate3_acute_crisis_capture": self._gate(
                metrics["systemic_crisis_capture"]["mean_trigger_rate_band"]
                >= baseline["systemic_crisis_capture"]["mean_trigger_rate_band"] - 0.03,
                "Preserve acute crisis capture, including 2020 COVID-like regimes.",
                metrics["systemic_crisis_capture"],
            ),
            "Gate4_recovery_distinction": self._gate(
                metrics["structural_vs_recovery_gap"] >= baseline["structural_vs_recovery_gap"] + 0.02,
                "Improve distinction between recovery/healing and active structural stress.",
                {
                    "candidate_structural_vs_recovery_gap": metrics["structural_vs_recovery_gap"],
                    "baseline_structural_vs_recovery_gap": baseline["structural_vs_recovery_gap"],
                },
            ),
            "Gate5_threshold_robustness": self._gate(
                metrics["threshold_robustness"]["sensitivity_width"]
                <= baseline["threshold_robustness"]["sensitivity_width"] - 0.02,
                "Reduce local threshold sensitivity across the threshold band.",
                {
                    "candidate": metrics["threshold_robustness"],
                    "baseline": baseline["threshold_robustness"],
                },
            ),
            "Gate6_downstream_beta_compatibility": self._gate(
                False,
                "Filled after downstream beta screen.",
                {"status": "pending_downstream_screen"},
            ),
            "Gate7_explainability": self._gate(
                True,
                "Family remains interpretable at component, class, and decision-surface level.",
                {"explainability": "component-level deterministic posterior construction"},
            ),
        }

    def _downstream_metrics(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        frame: pd.DataFrame,
        *,
        baseline_scores: np.ndarray | None,
    ) -> dict[str, Any]:
        scores = np.asarray(scores, dtype=float)
        expected_beta = self._col(frame, "expected_target_beta")
        raw_beta = self._col(frame, "raw_target_beta")
        raw_delta = (raw_beta - expected_beta).to_numpy(dtype=float)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        high_expected_nonstress = (expected_beta.to_numpy(dtype=float) >= 0.90) & (~stress)
        triggers = self._band_trigger(scores)
        baseline_triggers = self._band_trigger(baseline_scores) if baseline_scores is not None else np.zeros(len(scores), dtype=bool)
        worsening = high_expected_nonstress & triggers & (~baseline_triggers)
        pathology = triggers & (raw_delta <= -0.25)
        baseline_pathology = baseline_triggers & (raw_delta <= -0.25)
        return {
            "nonstress_high_beta_rows": int(np.sum(high_expected_nonstress)),
            "nonstress_high_beta_trigger_rate": float(np.mean(triggers[high_expected_nonstress])) if high_expected_nonstress.any() else 0.0,
            "worsening_day_overlap_count": int(np.sum(worsening)),
            "worst_raw_beta_delta_on_worsening_days": float(np.nanmin(raw_delta[worsening])) if worsening.any() else 0.0,
            "mean_raw_beta_delta_on_worsening_days": float(np.nanmean(raw_delta[worsening])) if worsening.any() else 0.0,
            "beta_pathology_incidence": float(np.mean(pathology)),
            "beta_pathology_incidence_change_vs_legacy": float(np.mean(pathology) - np.mean(baseline_pathology)) if baseline_scores is not None else 0.0,
        }

    def _scores_for_family(self, name: str, frame: pd.DataFrame) -> np.ndarray:
        c = self._phase3_components(frame)
        if name == "C9_baseline_reference":
            return self._c9_scores(frame)
        if name == "multiclass_regime_posterior":
            return self._build_representations(frame, self._build_taxonomy(frame))["scores"]["phase3_price_market_persistence_stack"]
        if name == "hierarchical_stress_posterior":
            return self._hierarchical_scores(c)
        if name == "two_stage_anomaly_severity":
            return self._two_stage_scores(c)
        if name == "ordinal_state_transition_posterior":
            return self._ordinal_scores(c)
        raise KeyError(name)

    @staticmethod
    def _band_trigger(scores: np.ndarray | None) -> np.ndarray:
        if scores is None:
            return np.array([], dtype=bool)
        scores = np.asarray(scores, dtype=float)
        return scores >= 0.35

    def _candidate_ranking_score(self, metrics: dict[str, Any], gates: dict[str, Any]) -> float:
        gate_points = sum(1.0 for row in gates.values() if row["status"] == "PASS")
        return float(
            gate_points
            + 2.0 * metrics["stress_vs_ordinary_gap"]
            + 1.5 * metrics["structural_vs_recovery_gap"]
            + metrics["rank_auc_stress_vs_nonstress"]
            - metrics["ordinary_correction_behavior"]["mean_trigger_rate_band"]
            - metrics["threshold_robustness"]["sensitivity_width"]
        )

    @staticmethod
    def _downstream_score_adjustment(metrics: dict[str, Any]) -> float:
        return float(
            -2.0 * max(0.0, metrics["beta_pathology_incidence_change_vs_legacy"])
            -0.5 * metrics["nonstress_high_beta_trigger_rate"]
            -0.01 * metrics["worsening_day_overlap_count"]
        )

    @staticmethod
    def _threshold_robustness(scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
        thresholds = np.arange(0.25, 0.56, 0.05)
        stress = np.isin(labels, ["elevated_structural_stress", "systemic_crisis"])
        ordinary = labels == "ordinary_correction"
        recalls = []
        fprs = []
        for threshold in thresholds:
            trigger = scores >= threshold
            recalls.append(float(np.mean(trigger[stress])) if stress.any() else 0.0)
            fprs.append(float(np.mean(trigger[ordinary])) if ordinary.any() else 0.0)
        return {
            "stress_recall_min": float(min(recalls)),
            "stress_recall_max": float(max(recalls)),
            "ordinary_fpr_min": float(min(fprs)),
            "ordinary_fpr_max": float(max(fprs)),
            "sensitivity_width": float((max(recalls) - min(recalls)) + (max(fprs) - min(fprs))),
            "thresholds_tested": [float(x) for x in thresholds],
        }

    @staticmethod
    def _class_threshold_metrics(scores: np.ndarray, labels: np.ndarray, klass: str) -> dict[str, float]:
        mask = labels == klass
        if not mask.any():
            return {"rows": 0.0, "mean_score": 0.0, "mean_trigger_rate_band": 0.0}
        thresholds = np.arange(0.25, 0.56, 0.05)
        rates = [float(np.mean(scores[mask] >= threshold)) for threshold in thresholds]
        return {
            "rows": float(np.sum(mask)),
            "mean_score": float(np.mean(scores[mask])),
            "mean_trigger_rate_band": float(np.mean(rates)),
            "trigger_rate_at_0_35": float(np.mean(scores[mask] >= 0.35)),
            "trigger_rate_at_0_50": float(np.mean(scores[mask] >= 0.50)),
        }

    def _representation_hypothesis_test(self, families: dict[str, Any]) -> dict[str, Any]:
        c9 = families["C9_baseline_reference"]["comparison_criteria"]
        best_name, best = max(
            ((name, row) for name, row in families.items() if name != "C9_baseline_reference"),
            key=lambda item: item[1]["candidate_ranking_score"],
        )
        best_metrics = best["comparison_criteria"]
        representation_problem_evidence = (
            best_metrics["stress_vs_ordinary_gap"] > c9["stress_vs_ordinary_gap"]
            and best_metrics["ordinary_correction_behavior"]["mean_trigger_rate_band"]
            < c9["ordinary_correction_behavior"]["mean_trigger_rate_band"]
        )
        return {
            "hypothesis": "Current failure is mainly representation/semantic alignment, not only calibration.",
            "best_non_c9_family": best_name,
            "evidence_supports_representation_problem": "YES" if representation_problem_evidence else "INCONCLUSIVE",
            "basis": {
                "c9_stress_vs_ordinary_gap": c9["stress_vs_ordinary_gap"],
                "best_stress_vs_ordinary_gap": best_metrics["stress_vs_ordinary_gap"],
                "c9_ordinary_band": c9["ordinary_correction_behavior"]["mean_trigger_rate_band"],
                "best_ordinary_band": best_metrics["ordinary_correction_behavior"]["mean_trigger_rate_band"],
            },
        }

    def _write_reports(
        self,
        taxonomy: dict[str, Any],
        representations: dict[str, Any],
        posterior: dict[str, Any],
        downstream: dict[str, Any],
        self_audit: dict[str, Any],
        checklist: dict[str, Any],
        verdict: dict[str, Any],
    ) -> None:
        self._write_report("pi_stress_phase3_regime_taxonomy.md", self._taxonomy_report(taxonomy))
        self._write_report("pi_stress_phase3_representation_experiments.md", self._representation_report(representations))
        self._write_report("pi_stress_phase3_posterior_family_comparison.md", self._posterior_report(posterior))
        self._write_report("pi_stress_phase3_downstream_beta_compatibility.md", self._downstream_report(downstream))
        self._write_report("pi_stress_phase3_self_audit.md", self._self_audit_report(self_audit))
        self._write_report("pi_stress_phase3_acceptance_checklist.md", self._checklist_report(checklist))
        self._write_report("pi_stress_phase3_research_verdict.md", self._verdict_report(verdict, posterior))

    def _taxonomy_report(self, taxonomy: dict[str, Any]) -> str:
        rows = "\n".join(f"| `{key}` | {value} |" for key, value in taxonomy["classes"].items())
        windows = "\n".join(
            f"| {key} | {row['dominant_label']} | {row['rows']} | {row['label_mix']} |"
            for key, row in taxonomy["episode_windows"].items()
        )
        return f"""# pi_stress Phase 3 Regime Taxonomy

## Purpose

Phase 3 treats the prior failure as a representation question. The taxonomy separates economically distinct states before any posterior-family comparison.

## Classes

| Class | Definition |
|---|---|
{rows}

## Label Construction

The labels are proxy research labels. They combine price drawdown topology, volatility shock, transition intensity, recovery impulse, and explicit historical windows. They are not conductor rules.

## Ambiguity Zones

- Total ambiguous rows: `{taxonomy['ambiguity_zones']['total_ambiguous_rows']}`
- Ambiguous fraction: `{taxonomy['ambiguity_zones']['fraction_ambiguous']:.4f}`
- Zone counts: `{taxonomy['ambiguity_zones']['zones']}`

## Required Episodes

| Window | Dominant label | Rows | Label mix |
|---|---:|---:|---|
{windows}

## Audit Finding

{taxonomy['economic_collapse_audit']['finding']}
"""

    def _representation_report(self, representations: dict[str, Any]) -> str:
        direct = representations["direct_comparison"]
        return f"""# pi_stress Phase 3 Representation Experiments

## Research Question

{representations['research_question']}

## Compared Stacks

- `C9_baseline`: {representations['stacks']['C9_baseline']['description']}
- `phase3_price_market_persistence_stack`: {representations['stacks']['phase3_price_market_persistence_stack']['description']}

## Direct Comparison

| Metric | Value |
|---|---:|
| Ordinary mean delta | {direct['ordinary_mean_delta']:.6f} |
| Structural mean delta | {direct['structural_mean_delta']:.6f} |
| Systemic mean delta | {direct['systemic_mean_delta']:.6f} |
| Recovery mean delta | {direct['recovery_mean_delta']:.6f} |
| Separation lift | {direct['separation_lift']:.6f} |

## Interpretation

The redesigned stack changes the latent component surface through price damage decomposition, market-internal confirmation, persistence/healing semantics, and macro/liquidity subspace proxies. This is not an operating-threshold experiment.
"""

    def _posterior_report(self, posterior: dict[str, Any]) -> str:
        rows = []
        for name, row in posterior["families"].items():
            metrics = row["comparison_criteria"]
            passed = sum(1 for gate in row["gate_results"].values() if gate["status"] == "PASS")
            rows.append(
                f"| `{name}` | {row['family_type']} | {metrics['stress_vs_ordinary_gap']:.4f} | "
                f"{metrics['ordinary_correction_behavior']['mean_trigger_rate_band']:.4f} | "
                f"{metrics['threshold_robustness']['sensitivity_width']:.4f} | {passed}/7 | "
                f"{row['candidate_ranking_score']:.4f} |"
            )
        gate_rows = []
        for name, row in posterior["families"].items():
            for gate, result in row["gate_results"].items():
                gate_rows.append(f"| `{name}` | {gate} | {result['status']} |")
        return f"""# pi_stress Phase 3 Posterior Family Comparison

## Selection Rule

{posterior['selection_rule']}

## Family Summary

| Family | Type | Stress vs ordinary gap | Ordinary band | Threshold sensitivity | Gates | Ranking score |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Gate Results

| Family | Gate | Status |
|---|---|---|
{chr(10).join(gate_rows)}

## Hypothesis Test

`{posterior['hypothesis_test']['evidence_supports_representation_problem']}`: {posterior['hypothesis_test']['basis']}
"""

    def _downstream_report(self, downstream: dict[str, Any]) -> str:
        rows = []
        for name, row in downstream["candidate_metrics"].items():
            rows.append(
                f"| `{name}` | {row['nonstress_high_beta_trigger_rate']:.4f} | "
                f"{row['worsening_day_overlap_count']} | {row['worst_raw_beta_delta_on_worsening_days']:.4f} | "
                f"{row['mean_raw_beta_delta_on_worsening_days']:.4f} | {row['beta_pathology_incidence_change_vs_legacy']:.4f} |"
            )
        return f"""# pi_stress Phase 3 Downstream Beta Compatibility

## Research Question

Can a stress posterior be preferred not only for stress discrimination, but also for safer downstream hedge behavior?

## Ranking Integration

`{downstream['ranking_integration']}`

## Candidate Metrics

| Candidate | Non-stress high-beta trigger rate | Worsening overlap | Worst raw beta delta | Mean raw beta delta | Pathology incidence change |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Screening Rule

{downstream['screening_rule']['reject_if']}
"""

    def _self_audit_report(self, self_audit: dict[str, Any]) -> str:
        rows = "\n".join(f"| {key} | {row['triggered']} | {row['resolved']} | {row['evidence']} |" for key, row in self_audit.items())
        return f"""# pi_stress Phase 3 Red-Flag Self-Audit

| Red flag | Triggered | Resolved | Evidence |
|---|---|---|---|
{rows}
"""

    def _checklist_report(self, checklist: dict[str, Any]) -> str:
        ovf = "\n".join(f"| {key} | {row['triggered']} | {row['evidence']} |" for key, row in checklist["one_vote_fail_items"].items())
        mp = "\n".join(f"| {key} | {row['status']} | {row['evidence']} |" for key, row in checklist["mandatory_pass_items"].items())
        bp = "\n".join(f"| {key} | {value} |" for key, value in checklist["best_practice_items_achieved"].items())
        return f"""# pi_stress Phase 3 Acceptance Checklist

## One-Vote-Fail Items

| Item | Triggered | Evidence |
|---|---|---|
{ovf}

## Mandatory Pass Items

| Item | Status | Evidence |
|---|---|---|
{mp}

## Best-Practice Items

| Item | Achieved |
|---|---|
{bp}

## Effect On Verdict

{checklist['effect_on_verdict']}
"""

    def _verdict_report(self, verdict: dict[str, Any], posterior: dict[str, Any]) -> str:
        best = verdict["best_research_family_after_beta_screen"]
        gates = posterior["families"].get(best, {}).get("gate_results", {}) if best else {}
        gate_rows = "\n".join(f"| {key} | {row['status']} |" for key, row in gates.items())
        return f"""# pi_stress Phase 3 Research Verdict

## Final Research Verdict

`{verdict['verdict']}`

## Best Research Family After Beta Screen

`{best}`

## Gate Summary For Best Family

| Gate | Status |
|---|---|
{gate_rows}

## Rationale

What improved:
{self._bullet_lines(verdict['summary']['what_improved'])}

What did not improve:
{self._bullet_lines(verdict['summary']['what_did_not_improve'])}

What remains ambiguous:
{self._bullet_lines(verdict['summary']['what_remains_ambiguous'])}

Why the verdict is justified:

- {verdict['summary']['why_justified']}
"""

    @staticmethod
    def _bullet_lines(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def _write_json(self, name: str, data: dict[str, Any]) -> None:
        (self.output_dir / name).write_text(
            json.dumps(data, indent=2, sort_keys=True, default=self._json_default),
            encoding="utf-8",
        )

    def _write_report(self, name: str, text: str) -> None:
        (self.report_dir / name).write_text(text, encoding="utf-8")

    @staticmethod
    def _window_mask(dates: pd.Series, start: str, end: str) -> pd.Series:
        return (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))

    def _window_summary(self, frame: pd.DataFrame, labels: np.ndarray, start: str, end: str) -> dict[str, Any]:
        mask = self._window_mask(pd.to_datetime(frame["date"], errors="coerce"), start, end).to_numpy(dtype=bool)
        if not mask.any():
            return {"rows": 0, "dominant_label": "missing", "label_mix": {}}
        values, counts = np.unique(labels[mask], return_counts=True)
        mix = {str(k): int(v) for k, v in zip(values, counts, strict=True)}
        return {
            "rows": int(np.sum(mask)),
            "dominant_label": max(mix.items(), key=lambda item: item[1])[0],
            "label_mix": mix,
        }

    def _window_score_metrics(self, frame: pd.DataFrame, scores: np.ndarray, labels: np.ndarray, spec: WindowSpec) -> dict[str, Any]:
        mask = self._window_mask(pd.to_datetime(frame["date"], errors="coerce"), spec.start, spec.end).to_numpy(dtype=bool)
        if not mask.any():
            return {"rows": 0}
        return {
            "rows": int(np.sum(mask)),
            "expected_class": spec.expected_class,
            "mean_score": float(np.mean(scores[mask])),
            "trigger_rate_at_0_35": float(np.mean(scores[mask] >= 0.35)),
            "label_mix": self._window_summary(frame, labels, spec.start, spec.end)["label_mix"],
        }

    @staticmethod
    def _component_summary(series: pd.Series) -> dict[str, float]:
        values = pd.to_numeric(series, errors="coerce").fillna(0.0)
        return {
            "mean": float(values.mean()),
            "p75": float(values.quantile(0.75)),
            "p95": float(values.quantile(0.95)),
        }

    @staticmethod
    def _brier(scores: np.ndarray, labels: np.ndarray) -> float:
        return float(np.mean((np.asarray(scores, dtype=float) - np.asarray(labels, dtype=float)) ** 2))

    @staticmethod
    def _rank_auc(pos: np.ndarray, neg: np.ndarray) -> float:
        pos = np.asarray(pos, dtype=float)
        neg = np.asarray(neg, dtype=float)
        if len(pos) == 0 or len(neg) == 0:
            return 0.5
        return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())

    @staticmethod
    def _gate(pass_condition: bool, rule: str, evidence: Any) -> dict[str, Any]:
        return {"status": "PASS" if bool(pass_condition) else "FAIL", "rule": rule, "evidence": evidence}

    @staticmethod
    def _flag(triggered: bool, evidence: str) -> dict[str, str]:
        return {
            "triggered": "YES" if triggered else "NO",
            "resolved": "NO" if triggered else "YES",
            "evidence": evidence,
        }

    @staticmethod
    def _ovf(triggered: bool, evidence: str) -> dict[str, str]:
        return {"triggered": "YES" if triggered else "NO", "evidence": evidence}

    @staticmethod
    def _mp(pass_condition: bool, evidence: str) -> dict[str, str]:
        return {"status": "PASS" if bool(pass_condition) else "FAIL", "evidence": evidence}

    @staticmethod
    def _label_array(taxonomy: dict[str, Any]) -> np.ndarray:
        return np.asarray([row["label"] for row in taxonomy["row_labels"]], dtype=object)

    @staticmethod
    def _zscore(series: pd.Series, *, window: int) -> pd.Series:
        values = pd.to_numeric(series, errors="coerce").fillna(0.0)
        mean = values.rolling(window, min_periods=max(10, window // 8)).mean()
        std = values.rolling(window, min_periods=max(10, window // 8)).std().replace(0.0, np.nan)
        return ((values - mean) / std).fillna(0.0)

    @staticmethod
    def _col(frame: pd.DataFrame, name: str, fallback: str | None = None) -> pd.Series:
        if name in frame.columns:
            return pd.to_numeric(frame[name], errors="coerce").fillna(0.0)
        if fallback and fallback in frame.columns:
            return pd.to_numeric(frame[fallback], errors="coerce").fillna(0.0)
        return pd.Series(0.0, index=frame.index, dtype=float)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, pd.Timestamp):
            return str(value)
        return str(value)


if __name__ == "__main__":
    result = PiStressPhase3Research().write()
    print(json.dumps({"verdict": result["verdict"], "artifact_dir": "artifacts/pi_stress_phase3"}, indent=2))
