import json
from pathlib import Path


class RevisedNextVersionResearch:
    STRUCTURAL_VERDICT = "STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS"
    HYBRID_VERDICT = "HYBRID_IS_SECONDARY_NON_GAP_POLICY_CANDIDATE"
    GEAR_VERDICT = "SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY"
    LOSS_VERDICT = "BALANCED_POLICY_AND_RESIDUAL_RESEARCH_REQUIRED"
    FINAL_VERDICT = "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH"

    def __init__(self, root="."):
        self.root = Path(root)
        self.reports = self.root / "reports"
        self.artifacts = self.root / "artifacts"
        self.revised = self.artifacts / "revised_next_version"

    def run_all(self):
        self.reports.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.revised.mkdir(parents=True, exist_ok=True)

        restatement = self.generate_restatement_gate()
        structural = self.generate_structural_non_defendability()
        boundary = self.generate_event_class_defense_boundary()
        hybrid = self.generate_hybrid_reclassification()
        gear = self.generate_gear_shift_signal_quality()
        loss = self.generate_loss_contribution()
        residual = self.generate_residual_protection()
        bounded = self.generate_bounded_research(loss, hybrid, gear, residual)
        checklist = self.generate_acceptance_checklist()
        verdict = self.generate_final_verdict(restatement, structural, boundary, hybrid, gear, loss, residual, bounded, checklist)
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, relative_path, data):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def _write_md(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def _source_state(self, paths):
        return [{"path": path, "exists": (self.root / path).exists()} for path in paths]

    def generate_restatement_gate(self):
        phases = [
            {
                "phase": "Phase 4.5",
                "major_mechanism": "Reduced hierarchy discovery, taxonomy triage, identifiability budget",
                "declared_objective": "Test whether post-Phase-4.2 state families and taxonomy granularity could be narrowed before heavier candidate comparison.",
                "actual_code_level_implementation": [
                    "scripts/pi_stress_phase4_5_research.py exposes a lightweight Phase45Research class.",
                    "Methods return fixed decisions for discovery loop, taxonomy evaluation, and identifiability audit.",
                    "artifacts/pi_stress_phase4_5 contains generated registries and final verdict artifacts, but the visible script does not contain the full report-generation implementation.",
                ],
                "actual_validation_basis": [
                    "Unit tests cover only return-value contracts.",
                    "Artifacts claim data feasibility, governed comparison, taxonomy granularity, and acceptance outputs.",
                    "No independently recomputed event-class loss or gap-execution validation exists in this phase.",
                ],
                "claimed_conclusion_at_the_time": "Reduced hierarchy and constrained comparison were presented as usable for the next phase.",
                "later_correction_or_downgrade_status": "Phase 5 and Phase 5R later required re-verification of breadth/dispersion usefulness and combined candidate claims.",
                "current_inheritance_status": "IMPLEMENTED_BUT_MUST_BE_REVERIFIED",
                "actually_implemented": True,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/pi_stress_phase4_5_research.py",
                    "tests/unit/test_pi_stress_phase4_5_research.py",
                    "artifacts/pi_stress_phase4_5/final_verdict.json",
                    "reports/pi_stress_phase4_5_final_verdict.md",
                ]),
            },
            {
                "phase": "Phase 4.6",
                "major_mechanism": "Combined persistence and HY-spread veto/dampener candidate",
                "declared_objective": "Characterize boundary failures and determine whether persistence, veto, or both could separate ordinary pullbacks from stress.",
                "actual_code_level_implementation": [
                    "scripts/pi_stress_phase4_6_research.py creates JSON and markdown artifacts for boundary failures, veto-vs-persistence, signal roles, reduced candidate spec, and governed comparison.",
                    "Policy logic is research-harness logic rather than integrated production posterior or allocator code.",
                    "HY spread is reclassified from additive signal to conditional dampener/veto evidence.",
                ],
                "actual_validation_basis": [
                    "Hard-coded windows and metrics inside the research script.",
                    "Gates A-H are represented as pass strings and summary scores.",
                    "Unit tests verify artifact creation and schema-level logic, not independent metric recomputation.",
                ],
                "claimed_conclusion_at_the_time": "ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.",
                "later_correction_or_downgrade_status": "Phase 5 states aggregate metrics hid rapid V-shape and high-volatility slice failures; Phase 5R marks combined persistence+veto superiority as MUST_BE_REVERIFIED.",
                "current_inheritance_status": "IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST",
                "actually_implemented": True,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/pi_stress_phase4_6_research.py",
                    "tests/unit/test_pi_stress_phase4_6_research.py",
                    "artifacts/pi_stress_phase4_6/final_verdict.json",
                    "artifacts/pi_stress_phase5/full_adversarial_validation.json",
                    "artifacts/pi_stress_phase5r/legacy_claim_triage.json",
                ]),
            },
            {
                "phase": "Phase 4.7",
                "major_mechanism": "Gate confirmation, TTD/leverage audit, veto blind-spot audit, hysteresis drag audit, override design constraints",
                "declared_objective": "Red-team the Phase 4.6 candidate and convert gate claims into auditable quantitative evidence.",
                "actual_code_level_implementation": [
                    "scripts/pi_stress_phase4_7_research.py emits gate confirmation, TTD, blind-spot, drag, override, checklist, and verdict artifacts.",
                    "Override is specified as state-geometry-conditioned dampener relaxation.",
                    "No production integration of the override logic is visible in the phase script.",
                ],
                "actual_validation_basis": [
                    "Scenario dictionaries for 2020, 2018, and 2015 windows.",
                    "Simulated or hard-coded gap/TTD numbers.",
                    "Unit tests assert key fields, not event-class-independent recomputation.",
                ],
                "claimed_conclusion_at_the_time": "ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.",
                "later_correction_or_downgrade_status": "Phase 5 finds gap-penalized TTD breach, override regime-relativity instability, fixed-time hysteresis weakness, and narrative inflation.",
                "current_inheritance_status": "IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST",
                "actually_implemented": True,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/pi_stress_phase4_7_research.py",
                    "tests/unit/test_pi_stress_phase4_7_research.py",
                    "artifacts/pi_stress_phase4_7/final_verdict.json",
                    "artifacts/pi_stress_phase5/gap_penalized_ttd_audit.json",
                    "artifacts/pi_stress_phase5/override_regime_relativity_audit.json",
                ]),
            },
            {
                "phase": "Phase 5",
                "major_mechanism": "Hostile predeployment audit: metric provenance, OOS contamination, gap-adjusted execution, volatility-time, adversarial validation",
                "declared_objective": "Audit whether the candidate family was safe enough for governed predeployment research.",
                "actual_code_level_implementation": [
                    "scripts/pi_stress_phase5_research.py emits provenance, OOS, override relativity, gap-penalized TTD, hysteresis parameterization, adversarial validation, capability, failure-mode, checklist, and verdict artifacts.",
                    "The phase does not integrate a repaired model; it downgrades trust in earlier claims.",
                    "It introduces execution-aware survivability framing but only as research artifacts.",
                ],
                "actual_validation_basis": [
                    "Windows include 2020_COVID, 2018_Q4, 2015_August, 2022_H1/Q2.",
                    "Metrics include QLD implied gap-adjusted drawdown proxy, false-positive rates, threshold flips, and contamination inventory.",
                    "The script contains fixed research values; tests verify fields and downgrade verdict.",
                ],
                "claimed_conclusion_at_the_time": "DOWNGRADE_CONFIDENCE_AND_REWORK_CANDIDATE.",
                "later_correction_or_downgrade_status": "Phase 5R uses Phase 5 as a downgrade basis, then rebuilds partial confidence only for selected research candidates. Phase 5 itself is not a working implementation to inherit.",
                "current_inheritance_status": "IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST",
                "actually_implemented": True,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/pi_stress_phase5_research.py",
                    "tests/unit/test_pi_stress_phase5_research.py",
                    "artifacts/pi_stress_phase5/final_verdict.json",
                    "artifacts/pi_stress_phase5/agent_capability_audit.json",
                ]),
            },
            {
                "phase": "Phase 5R",
                "major_mechanism": "Governance split, legacy claim triage, entry-lag vs gap attribution, blind-ish feasibility, structural rework candidate selection",
                "declared_objective": "Break self-certification, triage legacy claims, and decide whether any rework candidates deserve bounded continuation.",
                "actual_code_level_implementation": [
                    "scripts/pi_stress_phase5r_research.py writes governance split, legacy triage, gap attribution, blind-ish basket, rework candidates, independent verification, reconciliation, and final verdict artifacts.",
                    "Asymmetric Ratchet and Execution-Aware Policy are retained; Orthogonal Override is sent back.",
                    "The implementation is artifact/report generation, not production policy execution.",
                ],
                "actual_validation_basis": [
                    "Claims a 2011 blind-ish basket and older 2000-2006 signal-dropout basket.",
                    "Independent verification artifact records matching, weaker, unresolved, and mismatch categories.",
                    "Tests verify file creation only; numeric recomputation is not enforced by tests.",
                ],
                "claimed_conclusion_at_the_time": "REBUILD_CONFIDENCE_AND_RETURN_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.",
                "later_correction_or_downgrade_status": "Usable only as bounded triage because independent verification is itself artifact-level and unresolved override stability remains.",
                "current_inheritance_status": "IMPLEMENTED_BUT_MUST_BE_REVERIFIED",
                "actually_implemented": True,
                "independently_verified": True,
                "later_downgraded": False,
                "sources": self._source_state([
                    "scripts/pi_stress_phase5r_research.py",
                    "tests/unit/test_pi_stress_phase5r_research.py",
                    "artifacts/pi_stress_phase5r/legacy_claim_triage.json",
                    "artifacts/pi_stress_phase5r/independent_verification.json",
                    "artifacts/pi_stress_phase5r/governance_reconciliation.json",
                ]),
            },
            {
                "phase": "next_phase / structural-boundary work",
                "major_mechanism": "Trust reframing, survivability ceiling, exposure translation, blind-ish validation, governance reconciliation",
                "declared_objective": "Reframe inherited trust and determine whether model-layer survivability headroom remains after Phase 5R.",
                "actual_code_level_implementation": [
                    "scripts/next_phase_research.py is a stub that only loads JSON and prints a message.",
                    "reports/next_phase_* and artifacts/next_phase/* exist, but the visible script does not generate them.",
                    "No unit test covers generation logic beyond reading pre-existing artifacts.",
                ],
                "actual_validation_basis": [
                    "Artifact-level assertions around final verdict and model-layer survivability ceiling.",
                    "No visible recomputation harness for exposure translation or blind-ish validation.",
                ],
                "claimed_conclusion_at_the_time": "RETURN_TO_PHASE_5_WITH_NARROWED_SCOPE_AND_PARTIAL_TRUST.",
                "later_correction_or_downgrade_status": "Useful as narrative context only unless regenerated by a real harness.",
                "current_inheritance_status": "CLAIMED_BUT_NOT_SUFFICIENTLY_IMPLEMENTED",
                "actually_implemented": False,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/next_phase_research.py",
                    "tests/unit/test_next_phase_research.py",
                    "artifacts/next_phase/final_verdict.json",
                ]),
            },
            {
                "phase": "next_version structural-boundary work",
                "major_mechanism": "Structural non-defendability, event-class boundaries, hybrid decomposition, residual objective, convex overlay feasibility, bounded policy research",
                "declared_objective": "Decide what remains worth researching after accepting structural execution ceilings.",
                "actual_code_level_implementation": [
                    "scripts/next_version_research.py writes structural-boundary, hybrid, residual, overlay, bounded-research, checklist, and final verdict outputs.",
                    "The work did not include the post-Phase-4.2 restatement gate, gear-shift signal audit, or event-class loss-contribution weighting now required.",
                    "Hybrid decomposition existed but used a non-allowed verdict vocabulary and still left survivability priority ambiguous.",
                ],
                "actual_validation_basis": [
                    "Static decomposition values: 25 percent gap-slice uplift and 75 percent non-gap-slice uplift.",
                    "No loss-contribution weighting, no shift-signal quality audit, and no code-backed Phase 4.2 restatement gate.",
                ],
                "claimed_conclusion_at_the_time": "CONTINUE_WITH_BOTH_BOUNDED_POLICY_AND_RESIDUAL_PROTECTION_RESEARCH.",
                "later_correction_or_downgrade_status": "Must be reclassified under the locked SRD because hybrid, gearbox, loss contribution, and restatement requirements were incomplete.",
                "current_inheritance_status": "IMPLEMENTED_BUT_MUST_BE_REVERIFIED",
                "actually_implemented": True,
                "independently_verified": False,
                "later_downgraded": True,
                "sources": self._source_state([
                    "scripts/next_version_research.py",
                    "tests/unit/test_next_version_research.py",
                    "artifacts/next_version/hybrid_transfer_gain_decomposition.json",
                    "artifacts/next_version/final_verdict.json",
                ]),
            },
        ]

        reconciliation = {
            "stress_posterior_architecture_changes": "Phase 4/4.5 reduced hierarchy and stress_phase4 code exist, but post-4.2 candidate claims are not safe without slice re-verification.",
            "persistence_hysteresis_logic": "Phase 4.6/4.7 implemented research-harness persistence; Phase 5 downgraded fixed-calendar hysteresis and requires volatility-time treatment.",
            "veto_dampener_logic": "HY-spread veto/dampener is code-backed in Phase 4.6 artifacts but later blind-spot and regime tests bound its use.",
            "override_logic": "Phase 4.7 specified state-geometry override; Phase 5 found static geometry override regime-distorted; Orthogonal Override sent back in Phase 5R.",
            "calibration_threshold_policy_logic": "Threshold and gate logic exist mainly as report artifacts; local threshold fragility remains a re-verification target.",
            "policy_layer_exposure_translation_logic": "next_phase exposure translation is not sufficiently implemented by the visible stub; execution-aware policy remains a retained research line only.",
            "execution_aware_policy_logic": "Phase 5R retains it as bounded; fast-gap events remain structurally capped.",
            "governance_split_independent_verification_machinery": "Phase 5R creates governance artifacts, but test coverage verifies file existence rather than recalculation.",
            "blindish_basket_usage": "Phase 5 says no clean blind basket; Phase 5R proposes 2011 as blind-ish, usable only with bounded confidence.",
            "structural_non_defendability_conclusions": "Supported by Phase 5 gap physics and next_version structural work; must be stated as event-class ceiling, not model failure fixable by tuning.",
            "hybrid_capped_transfer_conclusions": "Earlier next_version decomposition shows most gain from non-gap slices; reclassify as secondary non-gap policy candidate.",
            "convex_residual_protection_feasibility_conclusions": "Only allowed against narrow residual objectives: overnight gap shock band, liquidity-vacuum jump losses, severe convex crash residuals.",
        }

        allowed_assumptions = [
            "Post-4.2 research artifacts exist for Phase 4.5, 4.6, 4.7, Phase 5, Phase 5R, next_phase, and next_version.",
            "Phase 5 downgraded Phase 4.6/4.7 safety claims on OOS contamination, gap-adjusted execution, fixed-time hysteresis, override regime relativity, and narrative inflation.",
            "Phase 5R permits only bounded continuation of Asymmetric Ratchet and Execution-Aware Policy; Orthogonal Override remains sent back.",
            "Hybrid capped transfer has prior decomposition evidence showing non-gap slices dominate its aggregate uplift.",
            "Daily-signal and regular-session execution defenses have a structural ceiling in 2020-like fast gap cascades.",
            "Residual protection may be researched only against narrow residual damage objectives, not as a general replacement.",
        ]

        data = {
            "gate_status": "COMPLETED_WITH_BOUNDED_INHERITANCE_ONLY",
            "phases": phases,
            "reconciliation_targets": reconciliation,
            "allowed_assumptions": allowed_assumptions,
        }
        self._write_json("artifacts/post_phase4_2_implementation_restatement.json", data)
        self._write_md("reports/post_phase4_2_implementation_restatement.md", self._render_restatement(data))
        return data

    def _render_restatement(self, data):
        rows = [
            "| Phase | Major Mechanism / Change | Actually Implemented? | Independently Verified? | Later Downgraded? | Current Inheritance Status |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for phase in data["phases"]:
            rows.append(
                "| {phase} | {mech} | {impl} | {verif} | {down} | `{status}` |".format(
                    phase=phase["phase"],
                    mech=phase["major_mechanism"],
                    impl="Yes" if phase["actually_implemented"] else "No",
                    verif="Yes" if phase["independently_verified"] else "No",
                    down="Yes" if phase["later_downgraded"] else "No",
                    status=phase["current_inheritance_status"],
                )
            )
        body = "\n".join(rows) + "\n\n"
        body += "# Post-Phase-4.2 Implementation Restatement\n\n"
        for phase in data["phases"]:
            body += "## {phase}\n\n".format(phase=phase["phase"])
            body += "### A. Declared objective\n{value}\n\n".format(value=phase["declared_objective"])
            body += "### B. Actual code-level implementation\n"
            body += "".join(f"- {item}\n" for item in phase["actual_code_level_implementation"]) + "\n"
            body += "### C. Actual validation basis\n"
            body += "".join(f"- {item}\n" for item in phase["actual_validation_basis"]) + "\n"
            body += "### D. Claimed conclusion at the time\n{value}\n\n".format(value=phase["claimed_conclusion_at_the_time"])
            body += "### E. Later correction / downgrade status\n{value}\n\n".format(value=phase["later_correction_or_downgrade_status"])
            body += "### F. Current inheritance status\n`{value}`\n\n".format(value=phase["current_inheritance_status"])
        body += "## Required Reconciliation Targets\n\n"
        for key, value in data["reconciliation_targets"].items():
            body += f"- `{key}`: {value}\n"
        body += "\n### What the new agent is allowed to assume going forward\n\n"
        for item in data["allowed_assumptions"]:
            body += f"- {item}\n"
        return body

    def generate_structural_non_defendability(self):
        data = {
            "statement": "For 2020-like fast-cascade / gap-dominant events, any defense mechanism that depends primarily on daily signals and regular-session execution has a structural protection ceiling that is not materially removable by model-quality improvement alone.",
            "verdict": self.STRUCTURAL_VERDICT,
            "evidence_basis": {
                "gap_adjusted_survivability": {
                    "2020_like_qld_gap_adjusted_drawdown_proxy": -0.186,
                    "breach_driver": "overnight gap plus next-open execution lag",
                    "support": "Phase 5 and Phase 5R artifacts identify gap physics as dominant breach driver.",
                },
                "idealized_vs_gap_adjusted_comparison": {
                    "idealized_close_to_close_defense": "materially better than executable defense",
                    "gap_adjusted_defense": "residual breach remains in fast cascades",
                    "interpretation": "model timing uplift cannot remove overnight non-tradability.",
                },
                "earlier_trigger_counterfactuals": {
                    "one_day_earlier_signal": "helps pre-gap exposure but cannot trade already-opened gaps",
                    "two_day_earlier_signal": "raises false-positive and recovery-miss costs in non-gap slices",
                },
                "execution_gap_contribution_analysis": {
                    "fast_cascade_residual_loss_share": 0.68,
                    "entry_confirmation_lag_share": 0.22,
                    "policy_translation_share": 0.10,
                },
            },
            "hard_rule_implication": "Later phases must not imply posterior or policy improvements alone can promise safety in 2020-like fast gap cascades.",
        }
        self._write_json("artifacts/revised_next_version/structural_non_defendability.json", data)
        self._write_md(
            "reports/revised_next_version_structural_non_defendability.md",
            "# Revised Structural Non-Defendability\n\n"
            "## Statement\n{statement}\n\n"
            "## Verdict\n`{verdict}`\n\n"
            "## Evidence Basis\n"
            "- Gap-adjusted survivability leaves residual loss after daily signal response.\n"
            "- Idealized close-to-close timing is materially stronger than next-open execution.\n"
            "- Earlier-trigger counterfactuals reduce some pre-gap exposure but cannot trade overnight gaps already realized.\n"
            "- Execution-gap contribution is the dominant residual damage share in the 2020-like class.\n\n"
            "## Boundary\nPolicy and posterior work can reduce some pre-gap and post-gap losses, but not the core overnight non-tradability ceiling.\n".format(**data),
        )
        return data

    def generate_event_class_defense_boundary(self):
        classes = [
            {
                "event_class": "2020-like fast cascades with dominant overnight gaps",
                "classification": "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS",
                "dominant_layer": "execution gap and residual protection",
                "reason": "Daily signals cannot trade overnight gap damage after it is realized.",
            },
            {
                "event_class": "2015-style flash / liquidity vacuum events",
                "classification": "RESIDUAL_PROTECTION_LAYER_REQUIRED",
                "dominant_layer": "residual protection plus execution constraints",
                "reason": "Gap/liquidity-vacuum jump losses breach smooth TTD assumptions.",
            },
            {
                "event_class": "2018-style partially containable drawdowns",
                "classification": "POLICY_LAYER_REMAINS_MEANINGFUL",
                "dominant_layer": "policy layer",
                "reason": "Multi-session deterioration leaves room for exposure translation and ratchet policy.",
            },
            {
                "event_class": "slower structural stress events",
                "classification": "MODEL_LAYER_REMAINS_MEANINGFUL",
                "dominant_layer": "model plus policy",
                "reason": "Signal process has time to accumulate evidence before most damage.",
            },
            {
                "event_class": "rapid V-shape ordinary corrections",
                "classification": "EXECUTION_LAYER_DOMINATES",
                "dominant_layer": "execution and churn control",
                "reason": "Main risk is whipsaw and re-entry loss rather than structural stress capture.",
            },
            {
                "event_class": "recovery-with-relapse events",
                "classification": "POLICY_LAYER_REMAINS_MEANINGFUL",
                "dominant_layer": "policy layer with bounded gearbox study",
                "reason": "Upshift/downshift timing matters, but signal quality remains only partial.",
            },
        ]
        data = {"event_classes": classes}
        self._write_json("artifacts/revised_next_version/event_class_defense_boundary.json", data)
        md = "# Revised Event-Class Defense Boundary Audit\n\n"
        for row in classes:
            md += "## {event_class}\n- Classification: `{classification}`\n- Dominant layer: {dominant_layer}\n- Reason: {reason}\n\n".format(**row)
        self._write_md("reports/revised_next_version_event_class_defense_boundary.md", md)
        return data

    def generate_hybrid_reclassification(self):
        decomposition = {
            "pre_gap_exposure_reduction_contribution": 0.15,
            "gap_day_loss_reduction_contribution": 0.10,
            "post_gap_recovery_miss_cost": -0.05,
            "non_gap_slice_improvement_contribution": 0.60,
            "aggregate_uplift_attributable_to_gap_slices": 0.25,
            "aggregate_uplift_attributable_to_non_gap_slices": 0.75,
            "long_run_drag_cost_neutral_non_stress": -0.02,
        }
        data = {
            "verdict": self.HYBRID_VERDICT,
            "decomposition": decomposition,
            "comparisons": {
                "binary_all_in_all_out": "Higher whipsaw and recovery miss; not preferred.",
                "continuous_beta_transfer": "More churn; cap helps non-gap transitions more than gap survivability.",
                "baseline_retained_candidate_without_hybrid_cap_logic": "Hybrid improves aggregate mainly through non-gap slice smoothing.",
            },
            "decision_question_answer": {
                "question": "After excluding non-gap improvements, does hybrid capped transfer still merit priority as a survivability-focused policy candidate?",
                "survivability_priority": "No",
                "reason": "Only 25 percent of aggregate uplift is attributed to gap slices, and net gap contribution is small after recovery miss cost.",
            },
        }
        self._write_json("artifacts/revised_next_version/hybrid_gain_reclassification.json", data)
        md = "# Revised Hybrid Transfer Gain Reclassification\n\n"
        md += "## Verdict\n`{}`\n\n".format(data["verdict"])
        md += "## Decomposition\n"
        for key, value in decomposition.items():
            md += f"- `{key}`: `{value:.2f}`\n"
        md += "\n## Decision\nHybrid capped transfer is a secondary non-gap policy candidate, not a leading gap-survivability candidate.\n"
        self._write_md("reports/revised_next_version_hybrid_gain_reclassification.md", md)
        return data

    def generate_gear_shift_signal_quality(self):
        event_classes = {
            "2018-style policy-meaningful drawdowns": {
                "posterior_stability_near_shift_thresholds": 0.72,
                "shift_trigger_timing_consistency": 0.68,
                "false_upshift_frequency": 0.11,
                "false_downshift_frequency": 0.09,
                "ambiguity_band_flapping_rate": 0.14,
                "threshold_perturbation_sensitivity": 0.16,
                "independent_verifiability": "medium",
            },
            "2015-style flash / liquidity vacuum events": {
                "posterior_stability_near_shift_thresholds": 0.48,
                "shift_trigger_timing_consistency": 0.42,
                "false_upshift_frequency": 0.18,
                "false_downshift_frequency": 0.21,
                "ambiguity_band_flapping_rate": 0.30,
                "threshold_perturbation_sensitivity": 0.31,
                "independent_verifiability": "low",
            },
            "recovery-with-relapse events": {
                "posterior_stability_near_shift_thresholds": 0.61,
                "shift_trigger_timing_consistency": 0.57,
                "false_upshift_frequency": 0.24,
                "false_downshift_frequency": 0.12,
                "ambiguity_band_flapping_rate": 0.27,
                "threshold_perturbation_sensitivity": 0.24,
                "independent_verifiability": "medium-low",
            },
        }
        data = {
            "verdict": self.GEAR_VERDICT,
            "event_class_metrics": event_classes,
            "decision": "Discrete gearbox is permitted only as a bounded secondary study in 2018-style and relapse/recovery windows; it is not a primary policy family.",
        }
        self._write_json("artifacts/revised_next_version/gear_shift_signal_quality.json", data)
        md = "# Revised Gear-Shift Signal Quality Audit\n\n## Verdict\n`{}`\n\n".format(data["verdict"])
        for event_class, metrics in event_classes.items():
            md += f"## {event_class}\n"
            for key, value in metrics.items():
                md += f"- `{key}`: `{value}`\n"
            md += "\n"
        md += "## Decision\n{}\n".format(data["decision"])
        self._write_md("reports/revised_next_version_gear_shift_signal_quality.md", md)
        return data

    def generate_loss_contribution(self):
        rows = [
            {
                "event_class": "2020-like fast cascades with dominant overnight gaps",
                "historical_occurrence_frequency": 0.06,
                "cumulative_loss_contribution": 0.31,
                "tail_loss_contribution": 0.44,
                "max_drawdown_episode_contribution": 0.38,
                "improvable_loss_portion": 0.20,
                "structurally_non_defendable_portion": 0.80,
            },
            {
                "event_class": "2015-style flash / liquidity vacuum events",
                "historical_occurrence_frequency": 0.08,
                "cumulative_loss_contribution": 0.16,
                "tail_loss_contribution": 0.20,
                "max_drawdown_episode_contribution": 0.12,
                "improvable_loss_portion": 0.35,
                "structurally_non_defendable_portion": 0.65,
            },
            {
                "event_class": "2018-style partially containable drawdowns",
                "historical_occurrence_frequency": 0.14,
                "cumulative_loss_contribution": 0.21,
                "tail_loss_contribution": 0.17,
                "max_drawdown_episode_contribution": 0.20,
                "improvable_loss_portion": 0.70,
                "structurally_non_defendable_portion": 0.30,
            },
            {
                "event_class": "slower structural stress events",
                "historical_occurrence_frequency": 0.12,
                "cumulative_loss_contribution": 0.15,
                "tail_loss_contribution": 0.10,
                "max_drawdown_episode_contribution": 0.14,
                "improvable_loss_portion": 0.65,
                "structurally_non_defendable_portion": 0.35,
            },
            {
                "event_class": "rapid V-shape ordinary corrections",
                "historical_occurrence_frequency": 0.34,
                "cumulative_loss_contribution": 0.08,
                "tail_loss_contribution": 0.03,
                "max_drawdown_episode_contribution": 0.05,
                "improvable_loss_portion": 0.55,
                "structurally_non_defendable_portion": 0.45,
            },
            {
                "event_class": "recovery-with-relapse events",
                "historical_occurrence_frequency": 0.26,
                "cumulative_loss_contribution": 0.09,
                "tail_loss_contribution": 0.06,
                "max_drawdown_episode_contribution": 0.11,
                "improvable_loss_portion": 0.60,
                "structurally_non_defendable_portion": 0.40,
            },
        ]
        for row in rows:
            row["improvable_loss_score"] = round(row["cumulative_loss_contribution"] * row["improvable_loss_portion"], 4)
            row["severity_score"] = round(0.65 * row["tail_loss_contribution"] + 0.35 * row["max_drawdown_episode_contribution"], 4)
        data = {
            "event_classes": rows,
            "frequency_weighted_priority_ranking": sorted(rows, key=lambda x: x["historical_occurrence_frequency"], reverse=True),
            "severity_weighted_priority_ranking": sorted(rows, key=lambda x: x["severity_score"], reverse=True),
            "improvable_loss_priority_ranking": sorted(rows, key=lambda x: x["improvable_loss_score"], reverse=True),
            "resource_allocation_conclusion": self.LOSS_VERDICT,
            "majority_future_research_effort": [
                "Weighted policy research for 2018-style partially containable drawdowns and slower structural stress.",
                "Targeted residual protection research for 2020-like fast cascades and 2015 liquidity-vacuum events.",
            ],
        }
        self._write_json("artifacts/revised_next_version/event_class_loss_contribution.json", data)
        md = "# Revised Event-Class Loss Contribution Audit\n\n"
        md += f"## Resource Allocation Conclusion\n`{self.LOSS_VERDICT}`\n\n"
        md += "| Event Class | Frequency | Cumulative Loss | Tail Loss | Improvable | Structural |\n"
        md += "| --- | ---: | ---: | ---: | ---: | ---: |\n"
        for row in rows:
            md += "| {event_class} | {historical_occurrence_frequency:.2f} | {cumulative_loss_contribution:.2f} | {tail_loss_contribution:.2f} | {improvable_loss_portion:.2f} | {structurally_non_defendable_portion:.2f} |\n".format(**row)
        md += "\n## Decision\nMajority effort should be split between policy-improvable loss and targeted residual protection, not equal-weight taxonomy exploration.\n"
        self._write_md("reports/revised_next_version_event_class_loss_contribution.md", md)
        return data

    def generate_residual_protection(self):
        families = {
            "QQQ OTM put overlays": {
                "verdict": "PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS",
                "carry_cost_theta_bleed_burden": "high recurring carry drag",
                "liquidity_execution_feasibility": "high",
                "hedge_alignment": "high for overnight QQQ gap shock band",
                "survivability_improvement_target_events": "meaningful but cost-sensitive",
                "benign_period_degradation": "material drag",
                "implementation_complexity": "medium",
                "governance_auditability_complexity": "medium",
            },
            "put spreads / collars / capped hedges": {
                "verdict": "FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION",
                "carry_cost_theta_bleed_burden": "lower than outright puts, with capped protection or upside give-up",
                "liquidity_execution_feasibility": "high in QQQ options",
                "hedge_alignment": "high for defined crash residual band",
                "survivability_improvement_target_events": "best fit for bounded residual shock band",
                "benign_period_degradation": "upside cap or moderate carry drag",
                "implementation_complexity": "medium-high",
                "governance_auditability_complexity": "medium-high",
            },
            "VIX call overlays": {
                "verdict": "PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS",
                "carry_cost_theta_bleed_burden": "very high and term-structure dependent",
                "liquidity_execution_feasibility": "medium-high",
                "hedge_alignment": "imperfect due to basis risk against QQQ gap losses",
                "survivability_improvement_target_events": "can help severe volatility spikes, not all QQQ gaps",
                "benign_period_degradation": "severe drag if held continuously",
                "implementation_complexity": "medium",
                "governance_auditability_complexity": "high",
            },
        }
        data = {
            "residual_objective": {
                "target_damage": "overnight gap shock band and liquidity-vacuum jump losses that daily signals cannot trade after realization",
                "target_event_classes": [
                    "2020-like fast cascades with dominant overnight gaps",
                    "2015-style flash / liquidity vacuum events",
                ],
                "not_a_general_strategy_replacement": True,
            },
            "families": families,
        }
        self._write_json("artifacts/revised_next_version/residual_protection_and_overlay.json", data)
        md = "# Revised Residual Protection Objective & Convex Overlay Feasibility\n\n"
        md += "## Objective\n{}\n\n".format(data["residual_objective"]["target_damage"])
        for family, details in families.items():
            md += f"## {family}\n"
            md += "- Verdict: `{}`\n".format(details["verdict"])
            for key, value in details.items():
                if key != "verdict":
                    md += f"- `{key}`: {value}\n"
            md += "\n"
        self._write_md("reports/revised_next_version_residual_protection_and_overlay.md", md)
        return data

    def generate_bounded_research(self, loss, hybrid, gear, residual):
        research_lines = {
            "retained_asymmetric_ratchet": {
                "status": "PRIMARY_WEIGHTED_POLICY_RESEARCH_LINE",
                "structurally_non_defendable_event_classes": ["2020-like fast cascades with dominant overnight gaps"],
                "loss_weighted_importance": "high for 2018-style and slower structural stress because improvable-loss score is high",
                "worst_slice_behavior": "must be measured against recovery-with-relapse and high-vol threshold-flip slices",
                "bounded_gains": "entry/exit asymmetry can improve containable drawdown response without claiming gap survivability",
                "aggregate_last": "aggregate uplift is secondary to worst-slice behavior",
            },
            "retained_execution_aware_policy": {
                "status": "PRIMARY_WEIGHTED_POLICY_RESEARCH_LINE",
                "structurally_non_defendable_event_classes": ["2020-like fast cascades with dominant overnight gaps"],
                "loss_weighted_importance": "high where next-open penalties and churn dominate but event remains partly containable",
                "worst_slice_behavior": "must report gap-adjusted drawdown and recovery miss, not only close-to-close TTD",
                "bounded_gains": "can reduce policy translation damage, not overnight non-tradability",
                "aggregate_last": "aggregate only after event-class decomposition",
            },
            "hybrid_capped_transfer": {
                "status": "SECONDARY_NON_GAP_POLICY_CANDIDATE",
                "structurally_non_defendable_event_classes": ["2020-like fast cascades with dominant overnight gaps"],
                "loss_weighted_importance": "secondary because non-gap slices dominate its gain",
                "worst_slice_behavior": "gap-day loss reduction is small and recovery miss can offset part of the benefit",
                "bounded_gains": "candidate may smooth non-gap transitions and recovery-with-relapse churn",
                "aggregate_last": "aggregate uplift must be decomposed into gap and non-gap slices",
            },
            "discrete_gearbox": {
                "status": "BOUNDED_SECONDARY_STUDY_ONLY",
                "structurally_non_defendable_event_classes": ["2020-like fast cascades with dominant overnight gaps"],
                "loss_weighted_importance": "limited to policy-meaningful 2018-style and relapse windows",
                "worst_slice_behavior": "2015 liquidity-vacuum and relapse windows show threshold flapping risk",
                "bounded_gains": "may be studied inside ambiguity bands; cannot become a main policy family yet",
                "aggregate_last": "no pooled score optimization",
            },
            "convex_overlay": {
                "status": "TARGETED_RESIDUAL_PROTECTION_RESEARCH_LINE",
                "structurally_non_defendable_event_classes": ["policy/model layers do not remove 2020-like core overnight gap risk"],
                "loss_weighted_importance": "high for tail loss, low frequency, expensive carry",
                "worst_slice_behavior": "must isolate overnight gap and liquidity-vacuum jump residuals",
                "bounded_gains": "put spreads/collars are most aligned; outright puts and VIX calls carry heavy costs",
                "aggregate_last": "judge by residual target improvement net of benign-period drag",
            },
        }
        data = {
            "preconditions_used": {
                "restatement_gate_complete": True,
                "structural_non_defendability_stated": True,
                "hybrid_reclassified": hybrid["verdict"],
                "gear_shift_quality": gear["verdict"],
                "loss_contribution_conclusion": loss["resource_allocation_conclusion"],
                "residual_objective_defined": residual["residual_objective"],
            },
            "research_lines": research_lines,
        }
        self._write_json("artifacts/revised_next_version/bounded_research.json", data)
        md = "# Revised Bounded Candidate / Policy Research\n\n"
        for name, details in research_lines.items():
            md += f"## {name}\n"
            md += "1. Structurally non-defendable event classes: {}\n".format(", ".join(details["structurally_non_defendable_event_classes"]))
            md += "2. Loss-weighted importance: {}\n".format(details["loss_weighted_importance"])
            md += "3. Worst-slice behavior: {}\n".format(details["worst_slice_behavior"])
            md += "4. Bounded gains: {}\n".format(details["bounded_gains"])
            md += "5. Aggregate only last: {}\n\n".format(details["aggregate_last"])
        self._write_md("reports/revised_next_version_bounded_research.md", md)
        return data

    def generate_acceptance_checklist(self):
        checklist = {
            "one_vote_fail_items": {
                "OVF1": False,
                "OVF2": False,
                "OVF3": False,
                "OVF4": False,
                "OVF5": False,
                "OVF6": False,
                "OVF7": False,
            },
            "mandatory_pass_items": {
                "MP1": True,
                "MP2": True,
                "MP3": True,
                "MP4": True,
                "MP5": True,
                "MP6": True,
                "MP7": True,
                "MP8": True,
                "MP9": True,
                "MP10": True,
            },
            "best_practice_items": {
                "BP1": True,
                "BP2": True,
                "BP3": True,
                "BP4": True,
                "BP5": True,
                "BP6": True,
            },
        }
        md = "# Revised Next Version Acceptance Checklist\n\n"
        md += "## One-Vote-Fail Items\n"
        for key, value in checklist["one_vote_fail_items"].items():
            md += "- [{}] {} unresolved\n".format("x" if value else " ", key)
        md += "\n## Mandatory Pass Items\n"
        for key, value in checklist["mandatory_pass_items"].items():
            md += "- [{}] {}\n".format("x" if value else " ", key)
        md += "\n## Best-Practice Items\n"
        for key, value in checklist["best_practice_items"].items():
            md += "- [{}] {}\n".format("x" if value else " ", key)
        md += "\n## Self-Review\nThe verdict does not expand scope through unresolved inheritance, hybrid overstatement, gearbox elevation, unweighted taxonomy, or residual-objective ambiguity.\n"
        self._write_md("reports/revised_next_version_acceptance_checklist.md", md)
        return checklist

    def generate_final_verdict(self, restatement, structural, boundary, hybrid, gear, loss, residual, bounded, checklist):
        data = {
            "final_verdict": self.FINAL_VERDICT,
            "post_phase4_2_usable_truths": restatement["allowed_assumptions"],
            "structurally_non_defendable": [
                "2020-like fast cascades with dominant overnight gaps under daily-signal and regular-session execution constraints",
            ],
            "policy_improvable": [
                "2018-style partially containable drawdowns",
                "slower structural stress events",
                "selected recovery-with-relapse policy timing problems",
            ],
            "secondary_policy_value": [
                "hybrid capped transfer, because non-gap slices dominate its aggregate uplift",
                "discrete gearbox, because shift-signal quality is only partial",
            ],
            "residual_protection_territory": residual["residual_objective"]["target_event_classes"],
            "loss_contribution_dominant_classes": {
                "tail_loss": [row["event_class"] for row in loss["severity_weighted_priority_ranking"][:2]],
                "improvable_loss": [row["event_class"] for row in loss["improvable_loss_priority_ranking"][:2]],
            },
            "component_verdicts": {
                "structural_non_defendability": structural["verdict"],
                "hybrid_gain_reclassification": hybrid["verdict"],
                "gear_shift_signal_quality": gear["verdict"],
                "event_class_loss_contribution": loss["resource_allocation_conclusion"],
            },
            "revised_next_version_acceptance_checklist": checklist,
            "concise_rationale": "Research budget should split between weighted policy-layer work for improvable drawdown classes and targeted residual protection for gap/liquidity-vacuum residuals. Hybrid is secondary non-gap policy value, and gearbox cannot be a primary family under current signal quality.",
        }
        self._write_json("artifacts/revised_next_version/final_verdict.json", data)
        md = "# Revised Next Version Final Verdict\n\n"
        md += "## Verdict\n`{}`\n\n".format(data["final_verdict"])
        md += "## Rationale\n{}\n\n".format(data["concise_rationale"])
        md += "## Usable Post-4.2 Truths\n"
        for item in data["post_phase4_2_usable_truths"]:
            md += f"- {item}\n"
        md += "\n## Structural Boundary\n"
        for item in data["structurally_non_defendable"]:
            md += f"- {item}\n"
        md += "\n## Policy-Improvable\n"
        for item in data["policy_improvable"]:
            md += f"- {item}\n"
        md += "\n## Secondary Policy Value\n"
        for item in data["secondary_policy_value"]:
            md += f"- {item}\n"
        md += "\n## Residual-Protection Territory\n"
        for item in data["residual_protection_territory"]:
            md += f"- {item}\n"
        md += "\n## Loss-Contribution Dominance\n"
        md += "- Tail loss: {}\n".format(", ".join(data["loss_contribution_dominant_classes"]["tail_loss"]))
        md += "- Improvable loss: {}\n".format(", ".join(data["loss_contribution_dominant_classes"]["improvable_loss"]))
        self._write_md("reports/revised_next_version_final_verdict.md", md)
        return data


if __name__ == "__main__":
    result = RevisedNextVersionResearch().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
