| Phase | Major Mechanism / Change | Actually Implemented? | Independently Verified? | Later Downgraded? | Current Inheritance Status |
| --- | --- | --- | --- | --- | --- |
| Phase 4.5 | Reduced hierarchy discovery, taxonomy triage, identifiability budget | Yes | No | Yes | `IMPLEMENTED_BUT_MUST_BE_REVERIFIED` |
| Phase 4.6 | Combined persistence and HY-spread veto/dampener candidate | Yes | No | Yes | `IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST` |
| Phase 4.7 | Gate confirmation, TTD/leverage audit, veto blind-spot audit, hysteresis drag audit, override design constraints | Yes | No | Yes | `IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST` |
| Phase 5 | Hostile predeployment audit: metric provenance, OOS contamination, gap-adjusted execution, volatility-time, adversarial validation | Yes | No | Yes | `IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST` |
| Phase 5R | Governance split, legacy claim triage, entry-lag vs gap attribution, blind-ish feasibility, structural rework candidate selection | Yes | Yes | No | `IMPLEMENTED_BUT_MUST_BE_REVERIFIED` |
| next_phase / structural-boundary work | Trust reframing, survivability ceiling, exposure translation, blind-ish validation, governance reconciliation | No | No | Yes | `CLAIMED_BUT_NOT_SUFFICIENTLY_IMPLEMENTED` |
| next_version structural-boundary work | Structural non-defendability, event-class boundaries, hybrid decomposition, residual objective, convex overlay feasibility, bounded policy research | Yes | No | Yes | `IMPLEMENTED_BUT_MUST_BE_REVERIFIED` |

# Post-Phase-4.2 Implementation Restatement

## Phase 4.5

### A. Declared objective
Test whether post-Phase-4.2 state families and taxonomy granularity could be narrowed before heavier candidate comparison.

### B. Actual code-level implementation
- scripts/pi_stress_phase4_5_research.py exposes a lightweight Phase45Research class.
- Methods return fixed decisions for discovery loop, taxonomy evaluation, and identifiability audit.
- artifacts/pi_stress_phase4_5 contains generated registries and final verdict artifacts, but the visible script does not contain the full report-generation implementation.

### C. Actual validation basis
- Unit tests cover only return-value contracts.
- Artifacts claim data feasibility, governed comparison, taxonomy granularity, and acceptance outputs.
- No independently recomputed event-class loss or gap-execution validation exists in this phase.

### D. Claimed conclusion at the time
Reduced hierarchy and constrained comparison were presented as usable for the next phase.

### E. Later correction / downgrade status
Phase 5 and Phase 5R later required re-verification of breadth/dispersion usefulness and combined candidate claims.

### F. Current inheritance status
`IMPLEMENTED_BUT_MUST_BE_REVERIFIED`

## Phase 4.6

### A. Declared objective
Characterize boundary failures and determine whether persistence, veto, or both could separate ordinary pullbacks from stress.

### B. Actual code-level implementation
- scripts/pi_stress_phase4_6_research.py creates JSON and markdown artifacts for boundary failures, veto-vs-persistence, signal roles, reduced candidate spec, and governed comparison.
- Policy logic is research-harness logic rather than integrated production posterior or allocator code.
- HY spread is reclassified from additive signal to conditional dampener/veto evidence.

### C. Actual validation basis
- Hard-coded windows and metrics inside the research script.
- Gates A-H are represented as pass strings and summary scores.
- Unit tests verify artifact creation and schema-level logic, not independent metric recomputation.

### D. Claimed conclusion at the time
ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.

### E. Later correction / downgrade status
Phase 5 states aggregate metrics hid rapid V-shape and high-volatility slice failures; Phase 5R marks combined persistence+veto superiority as MUST_BE_REVERIFIED.

### F. Current inheritance status
`IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST`

## Phase 4.7

### A. Declared objective
Red-team the Phase 4.6 candidate and convert gate claims into auditable quantitative evidence.

### B. Actual code-level implementation
- scripts/pi_stress_phase4_7_research.py emits gate confirmation, TTD, blind-spot, drag, override, checklist, and verdict artifacts.
- Override is specified as state-geometry-conditioned dampener relaxation.
- No production integration of the override logic is visible in the phase script.

### C. Actual validation basis
- Scenario dictionaries for 2020, 2018, and 2015 windows.
- Simulated or hard-coded gap/TTD numbers.
- Unit tests assert key fields, not event-class-independent recomputation.

### D. Claimed conclusion at the time
ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.

### E. Later correction / downgrade status
Phase 5 finds gap-penalized TTD breach, override regime-relativity instability, fixed-time hysteresis weakness, and narrative inflation.

### F. Current inheritance status
`IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST`

## Phase 5

### A. Declared objective
Audit whether the candidate family was safe enough for governed predeployment research.

### B. Actual code-level implementation
- scripts/pi_stress_phase5_research.py emits provenance, OOS, override relativity, gap-penalized TTD, hysteresis parameterization, adversarial validation, capability, failure-mode, checklist, and verdict artifacts.
- The phase does not integrate a repaired model; it downgrades trust in earlier claims.
- It introduces execution-aware survivability framing but only as research artifacts.

### C. Actual validation basis
- Windows include 2020_COVID, 2018_Q4, 2015_August, 2022_H1/Q2.
- Metrics include QLD implied gap-adjusted drawdown proxy, false-positive rates, threshold flips, and contamination inventory.
- The script contains fixed research values; tests verify fields and downgrade verdict.

### D. Claimed conclusion at the time
DOWNGRADE_CONFIDENCE_AND_REWORK_CANDIDATE.

### E. Later correction / downgrade status
Phase 5R uses Phase 5 as a downgrade basis, then rebuilds partial confidence only for selected research candidates. Phase 5 itself is not a working implementation to inherit.

### F. Current inheritance status
`IMPLEMENTED_BUT_LATER_REVOKED_FOR_TRUST`

## Phase 5R

### A. Declared objective
Break self-certification, triage legacy claims, and decide whether any rework candidates deserve bounded continuation.

### B. Actual code-level implementation
- scripts/pi_stress_phase5r_research.py writes governance split, legacy triage, gap attribution, blind-ish basket, rework candidates, independent verification, reconciliation, and final verdict artifacts.
- Asymmetric Ratchet and Execution-Aware Policy are retained; Orthogonal Override is sent back.
- The implementation is artifact/report generation, not production policy execution.

### C. Actual validation basis
- Claims a 2011 blind-ish basket and older 2000-2006 signal-dropout basket.
- Independent verification artifact records matching, weaker, unresolved, and mismatch categories.
- Tests verify file creation only; numeric recomputation is not enforced by tests.

### D. Claimed conclusion at the time
REBUILD_CONFIDENCE_AND_RETURN_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH.

### E. Later correction / downgrade status
Usable only as bounded triage because independent verification is itself artifact-level and unresolved override stability remains.

### F. Current inheritance status
`IMPLEMENTED_BUT_MUST_BE_REVERIFIED`

## next_phase / structural-boundary work

### A. Declared objective
Reframe inherited trust and determine whether model-layer survivability headroom remains after Phase 5R.

### B. Actual code-level implementation
- scripts/next_phase_research.py is a stub that only loads JSON and prints a message.
- reports/next_phase_* and artifacts/next_phase/* exist, but the visible script does not generate them.
- No unit test covers generation logic beyond reading pre-existing artifacts.

### C. Actual validation basis
- Artifact-level assertions around final verdict and model-layer survivability ceiling.
- No visible recomputation harness for exposure translation or blind-ish validation.

### D. Claimed conclusion at the time
RETURN_TO_PHASE_5_WITH_NARROWED_SCOPE_AND_PARTIAL_TRUST.

### E. Later correction / downgrade status
Useful as narrative context only unless regenerated by a real harness.

### F. Current inheritance status
`CLAIMED_BUT_NOT_SUFFICIENTLY_IMPLEMENTED`

## next_version structural-boundary work

### A. Declared objective
Decide what remains worth researching after accepting structural execution ceilings.

### B. Actual code-level implementation
- scripts/next_version_research.py writes structural-boundary, hybrid, residual, overlay, bounded-research, checklist, and final verdict outputs.
- The work did not include the post-Phase-4.2 restatement gate, gear-shift signal audit, or event-class loss-contribution weighting now required.
- Hybrid decomposition existed but used a non-allowed verdict vocabulary and still left survivability priority ambiguous.

### C. Actual validation basis
- Static decomposition values: 25 percent gap-slice uplift and 75 percent non-gap-slice uplift.
- No loss-contribution weighting, no shift-signal quality audit, and no code-backed Phase 4.2 restatement gate.

### D. Claimed conclusion at the time
CONTINUE_WITH_BOTH_BOUNDED_POLICY_AND_RESIDUAL_PROTECTION_RESEARCH.

### E. Later correction / downgrade status
Must be reclassified under the locked SRD because hybrid, gearbox, loss contribution, and restatement requirements were incomplete.

### F. Current inheritance status
`IMPLEMENTED_BUT_MUST_BE_REVERIFIED`

## Required Reconciliation Targets

- `stress_posterior_architecture_changes`: Phase 4/4.5 reduced hierarchy and stress_phase4 code exist, but post-4.2 candidate claims are not safe without slice re-verification.
- `persistence_hysteresis_logic`: Phase 4.6/4.7 implemented research-harness persistence; Phase 5 downgraded fixed-calendar hysteresis and requires volatility-time treatment.
- `veto_dampener_logic`: HY-spread veto/dampener is code-backed in Phase 4.6 artifacts but later blind-spot and regime tests bound its use.
- `override_logic`: Phase 4.7 specified state-geometry override; Phase 5 found static geometry override regime-distorted; Orthogonal Override sent back in Phase 5R.
- `calibration_threshold_policy_logic`: Threshold and gate logic exist mainly as report artifacts; local threshold fragility remains a re-verification target.
- `policy_layer_exposure_translation_logic`: next_phase exposure translation is not sufficiently implemented by the visible stub; execution-aware policy remains a retained research line only.
- `execution_aware_policy_logic`: Phase 5R retains it as bounded; fast-gap events remain structurally capped.
- `governance_split_independent_verification_machinery`: Phase 5R creates governance artifacts, but test coverage verifies file existence rather than recalculation.
- `blindish_basket_usage`: Phase 5 says no clean blind basket; Phase 5R proposes 2011 as blind-ish, usable only with bounded confidence.
- `structural_non_defendability_conclusions`: Supported by Phase 5 gap physics and next_version structural work; must be stated as event-class ceiling, not model failure fixable by tuning.
- `hybrid_capped_transfer_conclusions`: Earlier next_version decomposition shows most gain from non-gap slices; reclassify as secondary non-gap policy candidate.
- `convex_residual_protection_feasibility_conclusions`: Only allowed against narrow residual objectives: overnight gap shock band, liquidity-vacuum jump losses, severe convex crash residuals.

### What the new agent is allowed to assume going forward

- Post-4.2 research artifacts exist for Phase 4.5, 4.6, 4.7, Phase 5, Phase 5R, next_phase, and next_version.
- Phase 5 downgraded Phase 4.6/4.7 safety claims on OOS contamination, gap-adjusted execution, fixed-time hysteresis, override regime relativity, and narrative inflation.
- Phase 5R permits only bounded continuation of Asymmetric Ratchet and Execution-Aware Policy; Orthogonal Override remains sent back.
- Hybrid capped transfer has prior decomposition evidence showing non-gap slices dominate its aggregate uplift.
- Daily-signal and regular-session execution defenses have a structural ceiling in 2020-like fast gap cascades.
- Residual protection may be researched only against narrow residual damage objectives, not as a general replacement.
