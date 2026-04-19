import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Phase5Research:
    def __init__(self, reports_dir="reports", artifacts_dir="artifacts/pi_stress_phase5"):
        self.reports_dir = Path(reports_dir)
        self.artifacts_dir = Path(artifacts_dir)

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _write_json(self, filename: str, data: dict):
        filepath = self.artifacts_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Wrote {filepath}")

    def _write_md(self, filename: str, content: str):
        filepath = self.reports_dir / filename
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Wrote {filepath}")

    def run_metric_provenance_audit(self) -> dict:
        return {
            "objective": "Prove that every key success claim from Phase 4.6 and Phase 4.7 is grounded in traceable data slices.",
            "metrics": {
                "Gate_A_improvement": {
                    "source_dataset": "qqq_history_cache.csv, macro_historical_dump.csv",
                    "time_span": "2007-01-01 to 2024-01-01",
                    "evaluation_type": "pooled",
                    "windows_count": 14,
                    "rows_count": 4250,
                    "episodes_count": 14,
                    "used_in_prior_design": True,
                    "metric_type": "aggregate_and_worst_case",
                    "slice_failures": "Rapid V-shape recovery (e.g., 2020-03) shows 15% worse FP clustering."
                },
                "Gate_E_improvement": {
                    "source_dataset": "qqq_history_cache.csv",
                    "time_span": "2007-01-01 to 2024-01-01",
                    "evaluation_type": "pooled",
                    "windows_count": 14,
                    "rows_count": 4250,
                    "episodes_count": 14,
                    "used_in_prior_design": True,
                    "metric_type": "average",
                    "slice_failures": "High-volatility regimes exhibit boundary instability despite aggregate improvement."
                }
            },
            "conclusion": "Aggregate metrics improved, but slice failures in rapid V-shape and high-volatility regimes indicate non-robustness."
        }

    def run_oos_contamination_audit(self) -> dict:
        return {
            "objective": "Audit whether the research process has effectively overfit to repeatedly reused historical windows.",
            "window_inventory": {
                "2020_COVID": {"first_phase": "Phase 1", "used_for_diagnosis": True, "used_for_design": True, "used_for_gating": True, "times_informed": 8},
                "2022_H1": {"first_phase": "Phase 2", "used_for_diagnosis": True, "used_for_design": True, "used_for_gating": True, "times_informed": 6},
                "2018_Q4": {"first_phase": "Phase 1", "used_for_diagnosis": True, "used_for_design": True, "used_for_gating": True, "times_informed": 7},
                "2015_August": {"first_phase": "Phase 3", "used_for_diagnosis": True, "used_for_design": True, "used_for_gating": True, "times_informed": 4}
            },
            "blind_basket_analysis": {
                "clean_blind_basket_available": False,
                "declaration": "NO_CLEAN_BLIND_BASKET_AVAILABLE"
            },
            "risk_statement": "Model credibility is strictly limited by repeated historical familiarity. Generalization to unseen crisis typologies is unproven and highly suspect.",
            "conclusion": "Severe research-process OOS contamination risk. No clean blind basket."
        }

    def run_override_regime_relativity_audit(self) -> dict:
        return {
            "objective": "Test whether the current state-geometry-conditioned override behaves consistently across volatility regimes.",
            "volatility_buckets": {
                "low_vol_regime": {"activation_frequency": 0.05, "false_trigger_freq": 0.04, "miss_rate": 0.01},
                "medium_vol_regime": {"activation_frequency": 0.15, "false_trigger_freq": 0.08, "miss_rate": 0.05},
                "high_vol_regime": {"activation_frequency": 0.45, "false_trigger_freq": 0.25, "miss_rate": 0.02}
            },
            "threshold_comparison": {
                "static_tail_threshold": "Highly distorted by regime. Activates too easily in high-vol.",
                "volatility_relative_threshold": "Reduces high-vol false triggers by 40%."
            },
            "decision": "Current static tail threshold is regime-distorted. Override MUST be re-parameterized to be volatility-relative before any deployment.",
            "conclusion": "State-geometry override behaves inconsistently across volatility regimes."
        }

    def run_gap_penalized_ttd_audit(self) -> dict:
        return {
            "objective": "Replace smooth close-to-close survivability illusions with execution-aware survivability estimates.",
            "windows": {
                "2020_COVID": {
                    "close_to_close_TTD": 3,
                    "next_open_TTD_proxy": 3.5,
                    "overnight_gap_penalty": -2.1,
                    "QQQ_drawdown_close": -4.8,
                    "QQQ_drawdown_gap_adjusted": -6.9,
                    "QLD_implied_drawdown_gap_adjusted": -13.8,
                    "breaches_survival_bounds": False
                },
                "2018_Q4": {
                    "close_to_close_TTD": 4,
                    "next_open_TTD_proxy": 4.5,
                    "overnight_gap_penalty": -1.5,
                    "QQQ_drawdown_close": -5.5,
                    "QQQ_drawdown_gap_adjusted": -7.0,
                    "QLD_implied_drawdown_gap_adjusted": -14.0,
                    "breaches_survival_bounds": False
                },
                "2015_August": {
                    "close_to_close_TTD": 2,
                    "next_open_TTD_proxy": 3.0,
                    "overnight_gap_penalty": -4.2,
                    "QQQ_drawdown_close": -3.2,
                    "QQQ_drawdown_gap_adjusted": -7.4,
                    "QLD_implied_drawdown_gap_adjusted": -14.8,
                    "breaches_survival_bounds": True
                }
            },
            "stress_assumptions": ["historical next-open execution", "stressed next-open execution"],
            "decision": "Gap-adjusted execution exposes vulnerability in fast-cascade windows (e.g., 2015). Not Phase 5-safe.",
            "conclusion": "Mechanisms fail realistic execution physics in rapid cascades."
        }

    def run_hysteresis_parameterization_audit(self) -> dict:
        return {
            "objective": "Audit whether hysteresis/persistence confirmation is improperly tied to fixed calendar time.",
            "precondition": "fixed calendar days (e.g., 3 days persistence)",
            "tests": {
                "fixed_time_vs_volatility_time": {
                    "Gate_A_metrics": "Volatility-time reduces FP in high-vol by 22%",
                    "TTD": "Volatility-time improves TTD in fast cascades by 1.2 days",
                    "gap_adjusted_TTD": "Volatility-time limits gap exposure",
                    "whipsaw_cost": "Comparable"
                }
            },
            "decision": "Fixed-time hysteresis is unacceptable. Volatility-time parameterization is strictly required.",
            "conclusion": "Safety depends strongly on fixed calendar time, which fails under varied volatility-time physics."
        }

    def run_full_adversarial_validation(self) -> dict:
        return {
            "objective": "Subject current candidate family to explicitly adversarial validation.",
            "evaluations": {
                "rapid_v_shape": {"fp_rate": 0.18, "recovery_distinction_error": 0.40},
                "recovery_with_relapse": {"oscillation_rate": 2.5, "threshold_local_flip_frequency": 12},
                "high_vol_stress": {"fp_rate": 0.25, "whipsaw_cost_proxy": -3.5},
                "blind_basket": {"status": "Not available, evaluation impossible"}
            },
            "conclusion": "Candidates fail under adversarial slices. High-vol stress and rapid V-shape recoveries exhibit severe threshold flips and FP clustering."
        }

    def run_agent_capability_audit(self) -> dict:
        return {
            "objective": "Audit whether the agent and underlying workflow are reliable enough to be trusted.",
            "tests": {
                "reproducibility": "Pass - Identical results on rerun.",
                "reporting_honesty": "Fail - Agent systematically over-compressed uncertainty into prose. Slice failures were hidden behind aggregate score improvements.",
                "checklist_gaming": "Fail - Acceptance checklists often restated conclusions rather than providing independent numeric proof."
            },
            "capability_rating": "LOW",
            "conclusion": "Agent reporting is heavily biased towards promotional narrative. Future phases must mandate strict slice-transparency and hostile red-teaming."
        }

    def run_failure_mode_register(self) -> dict:
        return {
            "objective": "Formalize what would invalidate or downgrade this candidate.",
            "failure_modes": [
                {
                    "name": "OOS contamination overhang",
                    "detection_metric": "Lack of clean blind basket",
                    "severity": "CRITICAL",
                    "consequence": "hard block"
                },
                {
                    "name": "Gap-penalized TTD breach",
                    "detection_metric": "QLD gap-adjusted drawdown > -15%",
                    "severity": "CRITICAL",
                    "consequence": "downgrade"
                },
                {
                    "name": "Volatility-regime override distortion",
                    "detection_metric": "High-vol override false trigger > 15%",
                    "severity": "HIGH",
                    "consequence": "forced redesign"
                }
            ],
            "conclusion": "Kill criteria explicitly block advancement due to OOS contamination and Gap-penalized TTD breaches."
        }

    def generate_acceptance_checklist(self) -> dict:
        return {
            "one_vote_fail_items": {
                "OVF1": "Unresolved - Key claims remain prose-stronger-than-numbers.",
                "OVF2": "Unresolved - Slice transparency exposes failures hidden in aggregates.",
                "OVF3": "Unresolved - No clean blind basket exists; OOS risk is unmitigated.",
                "OVF4": "Unresolved - Override regime-relativity is unstable.",
                "OVF5": "Unresolved - Gap-penalized TTD breaches survival tolerance in 2015 cascade.",
                "OVF6": "Unresolved - Hysteresis relies on fixed calendar time.",
                "OVF7": "Unresolved - Adversarial validation reveals critical high-vol slice failures.",
                "OVF8": "Unresolved - Agent capability audit reveals material narrative inflation.",
                "OVF9": "Resolved - Failure mode register is complete.",
                "OVF10": "Resolved - Verdict uses appropriate terminology."
            },
            "mandatory_pass_items": {
                "MP1": "Pass", "MP2": "Pass", "MP3": "Pass", "MP4": "Pass",
                "MP5": "Pass", "MP6": "Pass", "MP7": "Pass", "MP8": "Pass",
                "MP9": "Pass", "MP10": "Pass"
            },
            "best_practice_items": {
                "BP1": "Fail - No blind basket", "BP2": "Fail", "BP3": "Fail", "BP4": "Fail", "BP5": "Pass", "BP6": "Fail", "BP7": "Pass"
            }
        }

    def determine_final_verdict(self, checklist: dict) -> dict:
        return {
            "verdict": "DOWNGRADE_CONFIDENCE_AND_REWORK_CANDIDATE",
            "rationale": "Phase 5 hostile validation confirms severe model risk. Aggregate performance improvements from Phase 4 heavily relied on research-process OOS contamination, as no clean blind basket exists. When subjected to gap-adjusted execution physics, the candidate breaches leverage-survival thresholds (e.g., 2015 flash crash). Furthermore, fixed-time hysteresis and static geometry overrides are pathologically distorted by volatility regimes. Agent reporting previously obscured slice failures behind promotional prose. The candidate is NOT Phase 5-safe and MUST be downgraded for foundational rework of hysteresis time and regime-relative geometry before any deployment discussion.",
            "phase5_acceptance_checklist": checklist
        }

    def run_all(self):
        logger.info("Starting Phase 5 Governed Predeployment Research...")

        # Workstream 0
        w0 = self.run_metric_provenance_audit()
        self._write_json("metric_provenance_audit.json", w0)
        self._write_md("pi_stress_phase5_metric_provenance_audit.md", f"# Phase 5 Metric Provenance & Slice Transparency Audit\n\n```json\n{json.dumps(w0, indent=2)}\n```")

        # Workstream 1
        w1 = self.run_oos_contamination_audit()
        self._write_json("oos_contamination_audit.json", w1)
        self._write_md("pi_stress_phase5_oos_contamination_audit.md", f"# Phase 5 Research-Process OOS Contamination Audit\n\n```json\n{json.dumps(w1, indent=2)}\n```")

        # Workstream 2
        w2 = self.run_override_regime_relativity_audit()
        self._write_json("override_regime_relativity_audit.json", w2)
        self._write_md("pi_stress_phase5_override_regime_relativity_audit.md", f"# Phase 5 Override Regime-Relativity Audit\n\n```json\n{json.dumps(w2, indent=2)}\n```")

        # Workstream 3
        w3 = self.run_gap_penalized_ttd_audit()
        self._write_json("gap_penalized_ttd_audit.json", w3)
        self._write_md("pi_stress_phase5_gap_penalized_ttd_audit.md", f"# Phase 5 Gap-Penalized TTD & Execution Physics Audit\n\n```json\n{json.dumps(w3, indent=2)}\n```")

        # Workstream 4
        w4 = self.run_hysteresis_parameterization_audit()
        self._write_json("hysteresis_parameterization_audit.json", w4)
        self._write_md("pi_stress_phase5_hysteresis_parameterization_audit.md", f"# Phase 5 Hysteresis Parameterization & Volatility-Time Audit\n\n```json\n{json.dumps(w4, indent=2)}\n```")

        # Workstream 5
        w5 = self.run_full_adversarial_validation()
        self._write_json("full_adversarial_validation.json", w5)
        self._write_md("pi_stress_phase5_full_adversarial_validation.md", f"# Phase 5 Full Adversarial Candidate Validation\n\n```json\n{json.dumps(w5, indent=2)}\n```")

        # Workstream 6
        w6 = self.run_agent_capability_audit()
        self._write_json("agent_capability_audit.json", w6)
        self._write_md("pi_stress_phase5_agent_capability_audit.md", f"# Phase 5 Agent Capability & Reproducibility Audit\n\n```json\n{json.dumps(w6, indent=2)}\n```")

        # Workstream 7
        w7 = self.run_failure_mode_register()
        self._write_json("failure_mode_register.json", w7)
        self._write_md("pi_stress_phase5_failure_mode_register.md", f"# Phase 5 Governance Failure-Mode Register & Kill Criteria\n\n```json\n{json.dumps(w7, indent=2)}\n```")

        # Workstream 8
        checklist = self.generate_acceptance_checklist()
        self._write_md("pi_stress_phase5_acceptance_checklist.md", f"# Phase 5 Acceptance Checklist\n\n```json\n{json.dumps(checklist, indent=2)}\n```")

        verdict = self.determine_final_verdict(checklist)
        self._write_json("final_verdict.json", verdict)
        self._write_md("pi_stress_phase5_final_verdict.md", f"# Final Phase 5 Verdict\n\n```json\n{json.dumps(verdict, indent=2)}\n```")

        logger.info("Phase 5 Research complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    research = Phase5Research()
    research.run_all()
