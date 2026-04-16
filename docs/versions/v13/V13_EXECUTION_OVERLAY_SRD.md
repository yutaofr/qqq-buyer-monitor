# System Requirements Document (SRD): v13 Execution Overlay

**Document Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Audience**: System Architect / Quant Engineer / MLOps / Backtest Owner / Runtime Owner  
**Predecessor**: v12.1 Orthogonal Factor Locked 4-State Baseline  
**Affected Runtime Modules**: `conductor.py`, `deployment_policy.py`, `behavioral_guard.py`, `src/models/deployment.py`, `backtest.py`, `data_contracts.py`, `web_exporter.py`, `discord_notifier.py`, `src/web/public/index.html`, `src/collector/breadth.py`, `src/collector/macro_v3.py`  
**Target New Module**: `execution_overlay.py`
**Target Audit Artifact**: `src/engine/v13/resources/execution_overlay_audit.json`

---

## 0. Version Statement

v13 is an **execution-layer architectural increment**, not a new inference engine.

v13 shall preserve the v12.1 probabilistic core:

- same 10-factor `ProbabilitySeeder`
- same `GaussianNB` posterior inference
- same recursive priors
- same entropy haircut semantics

v13 adds a new **Execution Overlay Layer** that may:

- penalize `target_beta`
- slow down or accelerate incremental cash deployment

v13 shall **not**:

- add sentiment or tape features into the posterior model
- alter regime class definitions
- replace the GaussianNB core with a new classifier
- introduce any leverage reward above the v12.1 beta surface

This boundary is mandatory. If a proposal changes posterior probabilities or factor topology, it is not v13. It is a new core architecture and must be versioned separately.

## 0.1 External SRD Disposition

An external `v12.3` SRD was reviewed before this document was written.

Its findings were separated into three buckets:

- **Adopted into v13**: execution-layer conditioning, market-internal penalties, anti-overfitting discipline, source governance, PIT-safe sentiment admission rules
- **Deferred outside v13**: base conductor data-quality semantics and fallback classification
- **Rejected for v13**: 4-bucket replacement of the 10-factor core, hand-written replacement of the GaussianNB posterior engine, and residual-driven meta-router logic that risks action-time leakage

This disposition is binding. v13 is not a partial implementation of the external `v12.3` architecture. It is a narrower, safer increment derived from the valid parts of that review.

---

## 1. Problem Definition

The v12.1 system is structurally honest at the macro regime level, but it is intentionally sparse on market-internal execution context.

This creates two gaps:

1. The system can be directionally correct on macro state while entering too aggressively into locally euphoric tape conditions.
2. The system can be directionally defensive while failing to exploit high-quality washout-and-repair conditions for incremental cash deployment.

The missing context is not a new macro factor problem. It is an **execution conditioning problem**.

The architecture must therefore distinguish between:

- **belief**: macro regime posterior and structural beta surface
- **action**: execution pace and local risk haircut

v13 exists to condition action without contaminating belief.

---

## 2. Goals

### 2.1 Primary Goals

- Preserve v12.1 posterior integrity.
- Reduce execution aggressiveness during euphoric or weakly confirmed tape conditions.
- Improve incremental deployment timing during statistically defensible washout-and-repair regimes.
- Keep the system deterministic, free-data, and Point-in-Time compliant.

### 2.2 Secondary Goals

- Surface execution diagnostics in the UI and runtime snapshots.
- Establish a formal source whitelist for sentiment and market-internal signals.
- Define an anti-overfitting tuning protocol before any coefficient enters production.

### 2.3 Non-Goals

- No sentiment signal may enter `ProbabilitySeeder`.
- No breadth, fear/greed, short-volume, or tape-confirmation signal may modify class likelihoods.
- No discretionary pattern detector, chart heuristic, or narrative rule may enter production logic.
- No proprietary or unstable commercial feed may become a required production dependency.

---

## 3. Architecture Decision Record

| ADR | Decision | Status | Rationale |
| :--- | :--- | :--- | :--- |
| ADR-1 | Keep v12.1 inference core unchanged | Adopted | Protects posterior calibration and avoids architecture fork |
| ADR-2 | Add execution overlay as a separate module | Adopted | Preserves belief/action separation |
| ADR-3 | Overlay is asymmetric | Adopted | Negative signals may penalize beta; positive signals may accelerate cash deployment only |
| ADR-4 | Overlay signals must be monotone and rank-based | Adopted | Reduces threshold fitting and scale dependence |
| ADR-5 | Missing or degraded overlay data must revert to neutral | Adopted | Prevents synthetic conviction |
| ADR-6 | Production sources must be free and PIT-safe, or self-archived with release timestamps | Adopted | Preserves auditability |
| ADR-7 | Reward may not increase leverage ceiling | Adopted | Prevents emotional or tape-driven over-risking |
| ADR-8 | Weekly sentiment sources require explicit publication-lag modeling | Adopted | Prevents look-ahead leakage |
| ADR-9 | Tuning is allowed only under pre-registered time-series methodology | Adopted | Rejects overfitting disguised as research |
| ADR-10 | Reject 4-bucket core rewrite for v13 | Adopted | Conflicts with locked v12.1 factor contract and posterior baseline |
| ADR-11 | Reject execution-router style meta-awareness for v13 | Adopted | Risks mixing realized outcomes into action timing and breaking PIT discipline |
| ADR-12 | Treat base conductor quality semantics as companion work, not overlay logic | Adopted | Prevents mixing two independent architecture changes into one version |

---

## 4. Architecture Constraints

The following constraints are hard requirements:

1. `raw_target_beta` and posterior probabilities must remain v12.1 outputs.
2. Overlay logic must run **after entropy haircut** and **before final execution commitment**.
3. Overlay logic must be serializable, deterministic, and replayable from stored raw inputs.
4. Every production parameter must be loaded from the single versioned audit artifact `src/engine/v13/resources/execution_overlay_audit.json`.
5. No overlay source may become mandatory unless a historical PIT-safe archive exists for both live and backtest paths.
6. If an overlay signal is unavailable, stale beyond its legal release horizon, or low quality, its multiplier contribution must be `1.0`.
7. Positive overlay must not raise `target_beta` above the pre-overlay protected beta.
8. Any positive execution reward must operate only on **incremental deployment pace**, not on stock-of-assets leverage.
9. v13.0 shall treat inherited `BehavioralGuard` bucket boundaries and inherited deployment-state multipliers as frozen interfaces unless a separate versioned spec explicitly reopens them.
10. Acceptance backtests and CI verification shall run from pinned historical artifacts and pinned evaluation end dates. Live network downloads are forbidden in the acceptance path.
11. If overlay diagnostics are exported, the runtime snapshot schema shall version-bump independently from the inherited v12 snapshot contract.

---

## 5. Architecture Rules

### 5.1 Belief-Action Separation

- Posterior inference belongs to the macro engine.
- Execution overlay belongs to downstream control.
- No overlay score may be reused as a training feature for the regime model.

### 5.2 No Hardcoded Narrative Logic

- No rule of the form `if fear > X and breadth < Y then buy/sell`.
- No event-specific crisis constants.
- No ad hoc overrides tied to one historical episode.
- No production parameter may live outside `execution_overlay_audit.json`.

### 5.3 Monotonicity

- Worsening negative execution context may never increase beta.
- Improving positive execution context may never worsen cash deployment pace.
- Neutral data must map to neutral coefficients.

### 5.4 Data Honesty

- The system must prefer omission to invention.
- Research-only signals may not silently leak into production.
- Any fallback must be explicitly marked and quality-scored.
- Placeholder collectors, constant-return helpers, and repurposed proxy fields may not be treated as production evidence.
- A field whose name implies one measure but currently stores another measure is not admissible until the contract is corrected.

### 5.5 Replayability

- A runtime snapshot must contain all raw overlay inputs, quality scores, derived overlay coefficients, and the final decision path.

---

## 6. High-Level Architecture

```text
v12.1 Macro Data
  -> ProbabilitySeeder (10-factor locked)
  -> GaussianNB posterior
  -> entropy haircut
  -> protected_beta

v13 Overlay Inputs
  -> ExecutionOverlaySnapshot
  -> negative overlay score
  -> positive overlay score
  -> beta multiplier / deployment multiplier

Final Path
  protected_beta
    -> beta overlay penalty
    -> inertial beta mapper
    -> behavioral guard

  deployment_readiness
    -> overlay pace multiplier
    -> deployment policy
```

### 6.1 Mandatory Integration Order

1. Compute posterior and `raw_target_beta` using v12.1 logic.
2. Compute entropy haircut and produce `protected_beta`.
3. Compute execution overlay from separate market-internal inputs.
4. Apply negative beta penalty to `protected_beta`.
5. Feed penalized beta into the existing inertial and behavioral pipeline.
6. Apply deployment multiplier only to incremental-cash pacing inputs.

This order is locked.

---

## 7. Functional Requirements

### 7.1 Execution Overlay Module

The system shall implement `ExecutionOverlayEngine` with the following responsibilities:

- ingest market-internal execution inputs
- validate source freshness and quality
- derive negative and positive execution scores
- emit:
  - `beta_overlay_multiplier`
  - `deployment_overlay_multiplier`
  - per-signal diagnostics
  - overlay quality summary

### 7.2 Negative Beta Penalty

The system shall permit the overlay to reduce `protected_beta` using only negative execution context.

Negative execution context includes:

- weakening breadth participation
- rising cap-weight concentration
- price advance without volume confirmation
- official positioning crowding, if and only if the source has a PIT-safe archive

### 7.3 Positive Deployment Reward

The system shall permit the overlay to accelerate **incremental deployment pacing** when washout-and-repair conditions are present.

Positive execution context includes:

- broad washout followed by internal stabilization
- downside price move with improving volume confirmation
- recovery-type positioning repair from official weekly sentiment sources, if admitted

The system shall not use positive context to increase stock-of-assets leverage.

### 7.4 Neutral Fallback

If all overlay signals are unavailable or degraded, the overlay shall return:

- `beta_overlay_multiplier = 1.0`
- `deployment_overlay_multiplier = 1.0`

This is mandatory.

### 7.5 Presentation And Notification Layer

The system shall adapt the output layer to v13 without changing the existing visual style.

Required behavior:

- `web_exporter.py` shall export overlay-aware fields while preserving the current `meta / signal / evidence` top-level contract shape
- `index.html` shall preserve the current page aesthetic, layout language, color palette, and interaction model
- `discord_notifier.py` shall remain concise and compact, surfacing overlay conditioning as execution context rather than as a new belief engine

The presentation layer shall communicate four distinct surfaces:

- `raw_target_beta`: inherited v12.1 pre-entropy surface
- `protected_beta`: post-entropy, pre-overlay surface
- `overlay_beta`: post-overlay continuous execution surface
- final action context: deployment state and behavioral guard bucket

The presentation layer shall not imply that sentiment or tape signals changed posterior belief.

---

## 8. Data Architecture

## 8.1 Production Data Admission Policy

Signals are admitted only if they satisfy:

- free or publicly accessible source
- stable schema or stable reconstruction rule
- recoverable historical archive
- PIT-safe publication timing
- deterministic derivation

## 8.2 Source Admission Matrix

| Signal Family | Source | Status | Production Use |
| :--- | :--- | :--- | :--- |
| `breadth_proxy` | yfinance `^ADD` / `^ADDN` proxy | Conditionally admitted | Negative overlay after transform hardening |
| `ndx_concentration` | yfinance `QQQ` vs `QQEW` | Admitted | Negative overlay |
| `qqq_close` | yfinance `QQQ` | Admitted | Tape confirmation |
| `qqq_volume` | yfinance `QQQ` volume | Admitted | Tape confirmation |
| `CFTC COT` | official weekly release | Conditionally admitted | Negative or positive overlay only after PIT archive build |
| `NAAIM Exposure Index` | free to view but usage restrictions apply | Research only | Not required for v13.0 production |
| `AAII Sentiment` | not free in structured production form | Rejected | Not admitted |
| `CNN Fear & Greed` | unstable non-audited JSON endpoint | Rejected | Not admitted |
| `FINRA short volume proxy` | historical correction handling incomplete | Research only | Not admitted until self-archived |
| placeholder collectors in `macro_v3.py` | constant values or neutral fallbacks | Rejected | Never admissible as v13 production evidence |

## 8.2.1 Current Repository Source Exceptions

The current repository contains helper functions and proxy fields that must not be promoted into v13 production logic without separate hardening work.

Explicit exclusions:

- `fetch_fcf_yield()` fixed proxy return
- `fetch_earnings_revisions_breadth()` placeholder return
- `fetch_sector_rotation()` placeholder return
- `fetch_short_volume_proxy()` placeholder return
- `fetch_move_index()` neutral constant fallback as overlay evidence
- `pct_above_50d` in the current breadth collector, because the field currently mirrors `adv_dec_ratio` rather than a true percent-above-moving-average measure

These may exist for research convenience or legacy compatibility. They are not admissible production inputs.

## 8.3 Canonical Research Contract Additions

The historical macro contract may add the following optional columns:

```text
ndx_concentration
source_ndx_concentration
ndx_concentration_quality_score
qqq_volume
source_qqq_volume
qqq_volume_quality_score
cot_equity_positioning
source_cot_equity_positioning
cot_quality_score
```

These are raw inputs. Derived overlay multipliers shall not be stored as canonical raw history.

## 8.4 PIT Rules

- Daily equity tape inputs (`QQQ` close, volume, `QQEW`) are visible at market close `T`.
- Daily actions derived from those inputs may not be assumed tradable earlier than the next execution event.
- Weekly official sentiment inputs must respect official publication timestamps.
- No weekly source may be backfilled into earlier days before release.

---

## 9. Derived Overlay Features

v13 shall derive only low-complexity, monotone execution features.

### 9.1 Breadth Stress

```text
breadth_stress_t = rank_expanding(1 - breadth_proxy_t)
```

Interpretation:

- higher value means poorer internal participation
- shall contribute only to negative overlay
- `breadth_proxy_t` must be derived from a documented monotone transform of raw advance-decline data
- the current repository sigmoid constant used in the breadth collector is not a locked production parameter unless versioned into `execution_overlay_audit.json`

### 9.2 Concentration Stress

```text
concentration_stress_t = rank_expanding(max(ndx_concentration_t, 0))
```

Interpretation:

- higher value means cap-weighted leadership is outrunning equal-weight participation
- shall contribute only to negative overlay

### 9.3 Price-Volume Confirmation

The system shall derive a low-complexity tape confirmation signal from `QQQ` price and volume.

Reference form:

```text
price_strength_20d_t = ROC(close, 20)
volume_intensity_t = zscore_expanding(log(volume))
confirmation_t = tanh(price_strength_20d_t * volume_intensity_t)
```

Interpretation:

- strong price with weak volume implies weak confirmation
- washed-out price with improving volume implies repair
- all volume standardization must use expanding or trailing windows observable at decision time
- when price is near highs and RSI is above 70, weak volume is treated as a
  `LATE_CYCLE` / Grind Higher process signal under passive-flow dominance; it is
  not a standalone `BUST` veto without trend damage, widening stress, or selloff
  volume

### 9.4 Official Positioning Stress

If `CFTC COT` is admitted, the system may derive:

```text
position_crowding_t = rank_expanding(cot_equity_positioning_t)
```

This input is optional and may not block production if absent.

---

## 10. Overlay Logic

## 10.1 Negative Score

The negative score must be a quality-weighted monotone aggregate:

```text
negative_score_t = weighted_average(
  breadth_stress_t,
  concentration_stress_t,
  non_confirmation_t,
  optional_position_crowding_t
)
```

with all components clipped to `[0, 1]`.

Requirements:

- weights must sum to `1.0` over observed components
- unobserved or low-quality components must drop out rather than contribute synthetic neutral history
- no single component may dominate through unbounded scaling

## 10.2 Positive Score

The positive score must be strictly narrower than the negative score.

Reference construction:

```text
positive_score_t = weighted_average(
  breadth_repair_t,
  volume_repair_t,
  optional_position_repair_t
)
```

where every component must require observed repair, not mere cheapness.

## 10.3 Beta Overlay

```text
beta_overlay_multiplier_t = 1 - lambda_beta * negative_score_t
beta_overlay_multiplier_t in [beta_floor, 1.0]

overlay_beta_t = protected_beta_t * beta_overlay_multiplier_t
overlay_beta_t <= protected_beta_t
```

This inequality is mandatory.

## 10.4 Deployment Overlay

```text
deployment_overlay_multiplier_t =
  clip(
    1 - lambda_pace_neg * negative_score_t + lambda_pace_pos * positive_score_t,
    pace_floor,
    pace_ceiling
  )
```

This multiplier may accelerate or decelerate incremental deployment pacing.

It may not:

- change posterior probabilities
- alter `raw_target_beta`
- bypass `behavioral_guard`
- lift leverage above the v12.1 base path
- alter inherited deployment state definitions in `v13.0`

---

## 11. Tuning Methodology

v13 tuning must follow time-series ML discipline.

### 11.1 What May Be Tuned

Tunable parameters are limited to:

- overlay feature weights
- multiplier caps and floors
- signal half-life or ranking window

The following may not be tuned:

- crisis-specific thresholds
- hand-selected event dates
- source-specific override rules
- any label-aware transformation inside the production signal definition
- inherited `BehavioralGuard` bucket boundaries
- inherited deployment-state multipliers

### 11.2 Required Procedure

1. Freeze signal definitions before tuning.
2. Use blocked, chronological, nested walk-forward validation only.
3. Keep a final untouched holdout window.
4. Evaluate median performance across windows, not best window.
5. Run ablations for every admitted signal family.
6. Reject any configuration whose gain disappears under ablation or minor perturbation.
7. Use a pinned validation calendar and pinned artifact set for all candidate comparisons.
8. Keep the number of independent free overlay parameters low enough to preserve attribution and reviewability.

### 11.3 Optimization Objective

The optimization objective is constrained and defensive.

Primary objective:

- reduce left-tail execution pain
- improve deployment timing quality
- keep turnover and decision noise controlled

Secondary objective:

- improve opportunity capture in validated washout-and-repair states

The system shall not optimize directly for maximum CAGR.

### 11.4 Hard Overfitting Rejection Rules

A candidate configuration must be rejected if any of the following holds:

- improvement appears only in one crisis slice
- holdout performance fails to confirm validation gains
- coefficient ranking is unstable across windows
- overlay increases leverage or action frequency without robust benefit
- randomized or permuted control signals produce comparable gains
- the candidate depends on unavailable historical data or synthetic backfill
- the candidate requires changing inherited v12.1 execution thresholds to appear effective
- the candidate cannot be replayed from archived raw inputs and the versioned audit artifact

---

## 12. Backtest Methodology Requirements

v13 backtests must satisfy both classical quant discipline and machine learning discipline.

### 12.1 Required Comparisons

Every candidate must be evaluated against:

- v12.1 champion baseline
- v13 overlay disabled
- v13 negative-only overlay
- v13 full overlay

### 12.2 Required Metrics

- posterior invariance
- raw beta invariance
- target beta delta distribution
- deployment timing score
- max adverse excursion on adds
- left-tail drawdown behavior
- turnover and state-switch frequency
- holdout stability
- replay determinism under frozen artifacts

### 12.3 Non-Regression Rule

v13 is accepted only if:

- posterior calibration does not degrade
- `raw_target_beta` is bit-identical to v12.1 for the same macro inputs
- left-tail execution behavior improves or remains neutral
- any reward effect is smaller and less frequent than the corresponding penalty path

### 12.4 Reproducibility Rules

- evaluation windows must use explicit absolute start and end dates
- acceptance backtests must fail closed if required frozen price history or archived overlay inputs are missing
- CI and release acceptance may not download fresh market history from live endpoints
- weekly sources must be aligned to stored publication timestamps, not reconstructed by naive calendar fill
- a candidate result is invalid if it cannot be regenerated from checked-in code, pinned config, and frozen data artifacts

---

## 13. Acceptance Criteria

| AC | Module | Definition of Done | Failure Mode |
| :--- | :--- | :--- | :--- |
| AC-1 | `execution_overlay` | Neutral inputs produce `beta_overlay_multiplier = 1.0` and `deployment_overlay_multiplier = 1.0` | Hard Fail |
| AC-2 | `conductor` | Posterior probabilities and `raw_target_beta` remain identical to v12.1 when overlay is enabled with neutral inputs | Hard Fail |
| AC-3 | `execution_overlay` | Negative score worsening is monotone and may never increase `target_beta` | Hard Fail |
| AC-4 | `deployment_policy` integration | Positive overlay may not increase beta ceiling; it may only affect incremental deployment pace | Hard Fail |
| AC-5 | data contract | Missing or degraded overlay inputs revert to neutral multipliers, not synthetic conviction | Hard Fail |
| AC-6 | PIT tests | Weekly sentiment sources are visible only after official publication time | Hard Fail |
| AC-7 | backtest | No synthetic `fear_greed` or fabricated short-volume proxy is used | Hard Fail |
| AC-8 | backtest | `raw_target_beta` replay is bit-identical versus v12.1 baseline | Hard Fail |
| AC-9 | backtest | Candidate gains must hold on untouched holdout and median walk-forward window | Hard Fail |
| AC-10 | diagnostics/UI | Runtime snapshot exports raw inputs, quality scores, negative/positive scores, and multipliers | Hard Fail |
| AC-11 | source governance | Every production signal is in the source admission matrix and carries provenance | Hard Fail |
| AC-12 | docs | SRD, source matrix, rollout checklist, and test mapping are complete and versioned | Hard Fail |
| AC-13 | source governance | No placeholder collector, neutral constant fallback, or repurposed proxy field is used as production overlay evidence | Hard Fail |
| AC-14 | backtest | Acceptance backtest fails closed when frozen market history or archived overlay inputs are missing; no live download path is exercised | Hard Fail |
| AC-15 | diagnostics/runtime | Overlay-enabled runtime snapshot version is bumped and includes full overlay decision trace | Hard Fail |
| AC-16 | interface governance | v13 overlay does not retune inherited `BehavioralGuard` boundaries or deployment-state multipliers | Hard Fail |
| AC-17 | web export / `index.html` | `status.json` exports overlay-aware fields, and the frontend renders them without changing the established page style or breaking existing hero metrics | Hard Fail |
| AC-18 | `discord_notifier` | Discord embed surfaces overlay conditioning as compact execution audit data, without implying posterior mutation or overwhelming the notification payload | Hard Fail |

---

## 14. Documentation Acceptance Standard

The v13 documentation set is complete only when all of the following exist:

- this SRD
- source admission matrix
- backtest protocol note
- runtime snapshot schema update
- presentation contract
- rollout checklist
- change log versus v12.1
- test mapping

Every document must:

- define scope and non-goals
- identify PIT rules
- identify rejected signals and why they are rejected
- map every new behavior to test IDs
- state whether it changes inherited v12.1 interfaces or leaves them frozen
- state whether it changes page style, page structure, or notification density

Documentation that describes a behavior without a corresponding test contract is incomplete.

---

## 15. Companion Architecture Work

v13 does not absorb every valid concern raised during the external SRD review.

The following issue remains real and must be tracked separately:

- **Base conductor quality blackhole**: the v12.1 quality audit still relies on the current fallback semantics and harmonic aggregation policy inherited from the locked baseline, including the fact that `breadth` remains removed from factor input while quality scoring stays governed by the v12 contract [Appendix G].
- **Collector hardening debt**: several repository helpers in `macro_v3.py` still expose placeholder or neutral constant returns that are acceptable only for research scaffolding.
- **Backtest reproducibility debt**: the current backtest entry path still contains a live-download escape hatch and a moving default end date, which are incompatible with industrial acceptance.

This is a **companion fix**, not part of v13 overlay logic.

Reason:

- overlay neutrality and overlay data governance are independent from base macro quality semantics
- combining both changes in one rollout would destroy attribution
- backtest non-regression would become ambiguous because failures could not be assigned to one change set

Required follow-up:

- open a separate spec and patch line for v12.1 quality semantics
- explicitly distinguish legal low-frequency `ffill` from true data degradation
- re-baseline entropy penalties and quality aggregation in isolation from the execution overlay
- replace or formally quarantine placeholder collector functions in research paths
- pin acceptance backtest end dates and eliminate live-download fallback from acceptance workflows

Until that companion fix lands, v13 must assume the v12.1 base conductor quality path is unchanged.

---

## 16. Development Standards

Implementation shall follow repository standards and Claude Code-compatible workflow discipline.

### 16.1 Repository Standards

- obey `AC-0` through `AC-10` from the v12 standards where applicable
- no hardcoded production parameters
- pure and deterministic logic for overlay transforms
- no look-ahead bias
- no synthetic history in backtest
- no promotion of placeholder research helpers into production without source-matrix approval

### 16.2 Engineering Workflow

- inspect current code before editing
- use atomic patches
- do not revert unrelated user changes
- keep runtime and backtest code paths aligned
- write tests before enabling production behavior
- preserve inherited v12.1 interfaces unless this document explicitly versions the change

### 16.3 Required Test Files

Minimum target suite:

- `tests/unit/engine/v13/test_execution_overlay.py`
- `tests/unit/engine/v11/test_conductor_overlay_integration.py`
- `tests/unit/data/test_overlay_pit_contract.py`
- `tests/unit/test_backtest_v13_overlay.py`
- `tests/integration/engine/v13/test_v13_shadow_mode.py`
- `tests/unit/test_web_exporter.py`
- `tests/unit/test_discord_notifier.py`
- `tests/integration/test_web_alignment.py`

---

## 17. Rollout Plan

### 17.1 Phase 0

- land data contract additions
- add overlay module in shadow mode
- export diagnostics only

### 17.2 Phase 1

- enable negative beta penalty
- keep positive reward disabled by default

### 17.3 Phase 2

- enable positive deployment reward only after holdout confirmation

### 17.4 Champion-Challenger Rule

v12.1 remains champion until v13 passes:

- all hard acceptance criteria
- holdout non-regression
- source governance review

If v13 fails, fallback is immediate: overlay disabled, v12.1 path intact.

---

## 18. Final Architecture Statement

v13 is a disciplined execution-conditioning layer.

It exists to make the system **less eager in bad tape** and **more efficient with new cash in validated repair tape**.

It does not exist to smuggle sentiment into the posterior model.

It does not exist to raise leverage on excitement.

It does not exist to fit the last crisis.

If implementation violates any of those three statements, it is not v13-compliant.
