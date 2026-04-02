# v13 User Stories And Tasks

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## Story 1: Overlay Audit Artifact And Admitted Inputs

**User Story**

As the runtime owner, I need a single audited parameter artifact and a controlled input contract so that v13 overlay behavior is deterministic, reviewable, and free from placeholder research leaks.

**Tasks**

- create `src/engine/v13/resources/execution_overlay_audit.json`
- define admitted signal weights, floors, ceilings, and source policy metadata
- add v13 raw input datamodel for breadth, concentration, QQQ close/volume, and optional COT
- reject placeholder helpers and semantically misleading proxy fields at the overlay boundary
- add unit tests for neutral fallback, placeholder rejection, and source gating

**Primary AC**

- `AC-1`
- `AC-5`
- `AC-11`
- `AC-13`

---

## Story 2: Execution Overlay Engine

**User Story**

As the quant engineer, I need an execution overlay engine that converts admitted market-internal inputs into monotone penalty and reward coefficients without mutating posterior belief.

**Tasks**

- add `src/engine/v13/execution_overlay.py`
- compute breadth stress, concentration stress, and price-volume confirmation using only trailing or expanding windows
- emit `negative_score`, `positive_score`, `beta_overlay_multiplier`, and `deployment_overlay_multiplier`
- guarantee monotonicity and bounded outputs
- keep all production parameters in `execution_overlay_audit.json`
- add unit tests for monotonic worsening, bounded multipliers, and replayability

**Primary AC**

- `AC-1`
- `AC-3`
- `AC-4`

---

## Story 3: Conductor Integration Without Belief Mutation

**User Story**

As the system architect, I need the overlay integrated after entropy haircut and before final execution commitment so that v12.1 posterior semantics remain unchanged while v13 conditions action.

**Tasks**

- integrate overlay into `src/engine/v11/conductor.py`
- preserve `raw_target_beta` and posterior probabilities
- add `protected_beta` and `overlay_beta` to runtime outputs
- apply negative overlay before inertial beta mapping
- apply positive overlay only to deployment pacing
- write v13 runtime snapshot block and schema version bump
- add integration tests for invariance and snapshot export

**Primary AC**

- `AC-2`
- `AC-8`
- `AC-10`
- `AC-15`
- `AC-16`

---

## Story 4: Presentation And Notification Adaptation

**User Story**

As the operator, I need the dashboard and Discord notification to show overlay conditioning clearly, without changing the existing page style or implying posterior mutation.

**Tasks**

- extend `src/output/web_exporter.py` with overlay-aware fields
- adapt `src/web/public/index.html` to render overlay audit surfaces in the existing style
- adapt `src/output/discord_notifier.py` to surface compact execution audit lines
- preserve current hero metrics, page shell, and notification density
- update alignment and payload tests

**Primary AC**

- `AC-17`
- `AC-18`

---

## Story 5: PIT And Source Governance Tests

**User Story**

As the backtest owner, I need explicit source and publication-lag tests so that weekly sentiment-style sources cannot leak future information into the overlay.

**Tasks**

- add `tests/unit/data/test_overlay_pit_contract.py`
- encode publication-lag handling for optional weekly sources
- verify provenance and quality metadata are carried with every admitted signal
- enforce rejection of repurposed proxy fields

**Primary AC**

- `AC-6`
- `AC-11`
- `AC-13`

---

## Story 6: Backtest Non-Regression And Frozen Acceptance Path

**User Story**

As the release owner, I need v13 backtests to prove no belief regression and to fail closed on missing frozen artifacts, so that acceptance is reproducible and not contaminated by live downloads.

**Tasks**

- add overlay-aware backtest tests
- pin acceptance end date and acceptance artifact mode
- assert no live download path is exercised in acceptance mode
- compare v12.1 champion, v13 disabled, v13 negative-only, and v13 full overlay
- inspect holdout and walk-forward stability before release

**Primary AC**

- `AC-7`
- `AC-8`
- `AC-9`
- `AC-14`

---

## Story 7: Runtime Validation, PR, And Operational Self-Audit

**User Story**

As the system owner, I need end-to-end runtime validation, PR checks, backtest review, and cold/warm start analysis so that v13 is deployable and aligned with real US market operating conditions.

**Tasks**

- run unit and integration tests in Docker
- run full backtest in Docker with pinned acceptance settings
- inspect regression, turnover, and left-tail behavior
- run T+0 cold start and immediate warm start
- inspect runtime snapshot and web export outputs
- create PR, monitor checks, and fix issues until green

**Primary AC**

- all hard acceptance criteria

