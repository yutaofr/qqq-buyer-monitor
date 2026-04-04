# SRD-v13.8-INDUSTRIAL-HARDENING: QQQ 贝叶斯正交配置引擎

**Version**: 13.8-INDUSTRIAL-HARDENING  
**Status**: PROPOSED FOR IMPLEMENTATION  
**Date**: 2026-04-04  
**Parent Baseline**: `docs/srd/v13_7_ULTIMA_SRD.md`  
**Companion Specs**: `docs/versions/v13/V13_EXECUTION_OVERLAY_SRD.md`, `docs/versions/v13/V13_BACKTEST_PROTOCOL.md`, `docs/core/PRD.md`  
**Audience**: Systems Architect / Runtime Owner / Backtest Owner / ML Owner / Data Owner / MLOps / Release Owner

---

## 0. 执行摘要 (Executive Statement)

v13.7-ULTIMA sealed a strong mathematical baseline:

- true Bayesian posterior update
- factor-lineage normalization
- entropy-aware de-risking
- execution overlay separation
- explicit user redline at `target_beta >= 0.5`

However, the current repository still exhibits an industrialization gap between:

1. sealed architecture intent
2. live runtime behavior
3. backtest certification behavior
4. audit narrative

This SRD defines the only acceptable hardening path for v13.8.

The purpose of v13.8 is not to invent a new model.
The purpose of v13.8 is to make the existing system auditable, replayable, reproducible, and contract-consistent enough to support industrial release discipline.

---

## 1. 问题定义 (Problem Definition)

The current system has four structural tensions:

1. **Runtime / backtest parity is incomplete**  
   Live runtime applies data-quality entropy penalty, floor protection, and high-entropy sensor surgery, while backtest does not reproduce the same end-to-end control path.

2. **Data quality is audited but not fully enforced at likelihood time**  
   Low-quality or missing features can still influence posterior shape through fallback filling semantics, even though the runtime computes quality scores.

3. **Calibration is directionally disciplined but not industrially frozen**  
   The repo contains ablation surfaces and heuristic parameters, but lacks a sealed calibration protocol with explicit untouched holdout evidence and reliability reporting.

4. **Reproducibility is partial, not sealed**  
   The repository has Docker and Python project metadata, but acceptance is not fully locked against floating dependencies, moving end dates, and live data escape hatches outside explicit frozen mode.

v13.8 exists to close these gaps without replacing the v13.7 probabilistic core.

---

## 2. 目标定义 (Goals)

### 2.1 Primary Goals

- Enforce a single canonical decision pipeline shared by live runtime and backtest.
- Convert data quality from a diagnostic concept into a causal gating concept.
- Freeze model calibration and acceptance methodology under explicit chronological discipline.
- Make release certification fail-closed on missing frozen artifacts or non-reproducible environments.
- Preserve the user redline: final recommended beta must not fall below `0.5` unless a future separately versioned SRD explicitly reopens that contract.

### 2.2 Secondary Goals

- Reduce audit overclaim risk by aligning documentation with actual code semantics.
- Improve replayability through richer runtime snapshots and deterministic audit artifacts.
- Separate "mathematical correctness", "statistical evidence", and "production readiness" into different acceptance layers.

### 2.3 Non-Goals

- No new regime topology.
- No replacement of `GaussianNB` with a new classifier in v13.8.
- No new discretionary event override logic.
- No new leverage reward above the protected beta surface.
- No silent broadening of acceptable data providers without PIT-safe archival rules.

---

## 3. 版本定位 (Version Statement)

v13.8 is an **industrial hardening release**, not a new inference architecture.

v13.8 shall preserve:

- the v13.7 factor topology
- the Bayesian posterior structure
- the entropy-based confidence haircut family
- the belief/action separation introduced by v13
- the permanent user redline at `0.5`

v13.8 shall add:

- canonical runtime/backtest parity
- likelihood-time data quality gating
- frozen calibration workflow
- deterministic release acceptance
- stronger observability and audit contracts

Any proposal that changes factor topology, regime labels, or the core posterior family is out of scope for v13.8 and must be versioned separately.

---

## 4. 架构原则 (Architecture Principles)

### 4.1 Contract First

Public system contracts shall be treated as binding:

- `raw_target_beta`
- `target_beta`
- `stable_regime`
- `deployment_state`
- `is_floor_active`
- `hydration_anchor`

No release may claim compliance unless both runtime and backtest produce these values under the same semantic ordering.

### 4.2 Belief and Action Separation

Posterior belief remains a macro-engine responsibility.
Execution conditioning remains downstream.
Data quality may suppress or neutralize evidence, but may not smuggle new action-only signals into posterior inference.

### 4.3 Prefer Omission to Invention

When a feature is unavailable, stale, or degraded, the default behavior shall be:

- suppress feature contribution
- reduce confidence
- preserve traceability

The system shall not invent conviction through neutral zero-fill semantics when the absence itself is information.

### 4.4 Fail Closed

Release acceptance, certification backtests, and sealed replay flows must reject:

- missing frozen inputs
- moving evaluation dates
- live network downloads
- unpinned environments

### 4.5 Evidence Before Assertion

The system shall distinguish:

1. mathematically valid
2. historically non-leaking
3. statistically calibrated
4. operationally production-ready

No document may claim level `4` using evidence that only supports levels `1` or `2`.

---

## 5. 缺口处置 (Current Gap Disposition)

The following observed gaps are adopted into v13.8 scope:

| Gap ID | Gap | Status |
| :--- | :--- | :--- |
| G-1 | Runtime/backtest pipeline divergence | Adopted |
| G-2 | Data quality computed but not injected into likelihood | Adopted |
| G-3 | Prior gravity description mismatches actual staged logic | Adopted |
| G-4 | Acceptance not fully frozen outside explicit acceptance mode | Adopted |
| G-5 | Heuristic tuning not yet sealed by untouched holdout evidence | Adopted |
| G-6 | Audit narrative overclaims readiness beyond code evidence | Adopted |

The following are explicitly deferred:

| Deferred ID | Topic | Reason |
| :--- | :--- | :--- |
| D-1 | New posterior family | Too large for hardening release |
| D-2 | New regime taxonomy | Requires separate economic specification |
| D-3 | Full multi-provider market data mesh | Valuable, but larger than v13.8 release envelope |

---

## 6. 目标高层架构 (High-Level Target Architecture)

```text
Canonical Inputs
  -> raw macro / market data
  -> source markers
  -> freshness metadata
  -> frozen artifact metadata

Canonical Feature Layer
  -> ProbabilitySeeder
  -> feature availability mask
  -> feature quality weights

Canonical Belief Layer
  -> runtime priors
  -> quality-aware likelihood
  -> posterior
  -> normalized entropy

Canonical Risk Layer
  -> quality penalty
  -> entropy haircut
  -> floor protection
  -> execution overlay
  -> inertial beta mapper
  -> behavioral guard
  -> deployment policy

Canonical Audit Layer
  -> runtime snapshot
  -> replay artifact
  -> acceptance trace
  -> calibration evidence
```

### 6.1 Mandatory Ordering

The final v13.8 decision path shall be:

1. ingest raw inputs and provenance
2. generate features
3. derive feature-level availability and quality
4. compute quality-aware posterior
5. compute posterior entropy
6. apply quality penalty to effective entropy
7. map to pre-floor beta via entropy haircut
8. apply floor protection
9. apply execution overlay
10. apply inertial beta mapping
11. apply behavioral guard
12. apply deployment policy
13. emit audit snapshot

This order is mandatory for both runtime and backtest.

---

## 7. 功能需求 (Functional Requirements)

### FR-1 Canonical Shared Pipeline

The system shall implement a single shared decision pipeline used by:

- `src/engine/v11/conductor.py`
- `src/backtest.py`

This shared pipeline shall own the full decision sequence described in Section 6.1.

`backtest.py` shall not reimplement risk semantics independently.

### FR-2 Runtime / Backtest Semantic Parity

For a frozen input row and identical inherited execution state, runtime and replay/backtest shall produce identical values for:

- posterior probabilities
- effective entropy
- `raw_target_beta`
- `raw_target_beta_pre_floor`
- `protected_beta`
- `overlay_beta`
- `target_beta`
- `deployment_state`
- `is_floor_active`
- `hydration_anchor`

Bit-identical equivalence is required where numeric determinism is technically achievable.
Otherwise tolerance must be explicitly versioned and justified.

### FR-3 Likelihood-Time Quality Gating

The system shall convert feature-level quality from a post-hoc diagnostic into a causal influence control.

Acceptable mechanisms include:

- multiplicative feature masking
- quality-weighted likelihood contributions
- hard suppression for unavailable features

Unacceptable mechanism:

- allowing missing features to behave as ordinary zero-valued evidence without explicit suppression semantics

### FR-4 Missingness Semantics

The system shall distinguish at least three states for each feature:

1. observed and canonical
2. observed but degraded
3. unavailable

The inference engine shall not treat states `2` and `3` as equivalent to canonical observation.

### FR-5 User Redline Preservation

The final recommended `target_beta` shall remain floor-locked at `0.5`.

This protection must be enforced:

- in live runtime
- in backtest replay
- in acceptance certification

No module may bypass this contract unless a separately versioned SRD explicitly reopens it.

### FR-6 High-Entropy Defense Parity

The high-entropy defensive path shall be contractually identical in runtime and replay.

This includes:

- `high_entropy_streak`
- secondary-factor damping thresholds
- ULTIMA non-core sensor cuts
- emitted diagnostics and state persistence

### FR-7 Prior Gravity Transparency

The prior system shall expose staged blending explicitly in diagnostics:

- `base_weight`
- `posterior_weight`
- `transition_weight`
- phase condition for each schedule

Documentation shall reflect the actual staged behavior rather than a single constant statement.

### FR-8 Acceptance Mode Hard Lock

Acceptance backtests shall require:

- pinned code revision
- pinned artifact bundle
- pinned evaluation start
- pinned evaluation end
- pinned price cache
- no live network download

If any required artifact is missing, acceptance shall fail immediately.

### FR-9 Calibration Registry

All production-effective inference and overlay coefficients shall live in versioned artifacts, not ad hoc code paths.

This includes:

- inference temperature
- feature lineage weights
- overlay penalty/reward coefficients
- quality transfer function
- holdout boundary metadata

### FR-10 Audit Narrative Discipline

System-generated or checked-in audit documents shall classify conclusions under one of:

- `mathematical`
- `causal/PIT`
- `statistical`
- `operational`

A document may not state `production-ready` unless operational evidence exists for:

- parity
- reproducibility
- frozen acceptance
- environment sealing

---

## 8. 数据与溯源需求 (Data and Provenance Requirements)

### FR-11 Source Classes

Every input source shall be classified as one of:

- `canonical`
- `degraded`
- `proxy`
- `synthetic`
- `missing`

Each class shall have:

- explicit allowed use
- explicit quality transfer
- explicit replay policy

### FR-12 PIT Visibility Contract

Any source entering replay or production shall define:

- `observation_date`
- `effective_date`
- publication lag semantics
- legal replay visibility rule

Weekly and delayed-release sources must carry archival publication timestamps or be excluded from acceptance.

### FR-13 Data Provider Redundancy Tiering

The system shall classify providers by redundancy tier:

- Tier A: multi-path or archived canonical provider
- Tier B: single primary with replay archive
- Tier C: live-only exploratory input

Tier C inputs may not become required production evidence.

### FR-14 Price History Integrity

Acceptance and certification flows shall load price history only from frozen artifacts.

Live price collectors may continue using current fetchers in production runtime, but acceptance shall not depend on them.

---

## 9. 校准与验证需求 (Calibration and Validation Requirements)

### FR-15 Frozen Chronological Calibration

v13.8 calibration shall use blocked chronological validation only.

Required protocol:

1. freeze candidate feature definitions
2. freeze regime labels
3. split into nested walk-forward windows
4. tune only on inner windows
5. evaluate on outer windows
6. keep one untouched final holdout
7. report median and dispersion, not best-case window only

### FR-16 Reliability Reporting

The minimum calibration report shall include:

- Brier score
- reliability / calibration plot
- expected calibration error or equivalent
- entropy distribution
- window stability of chosen parameters
- posterior invariance where required

Return metrics alone are insufficient.

### FR-17 Overfitting Rejection Gates

A candidate shall be rejected if any of the following holds:

- performance gain appears only in one crisis slice
- gains disappear in untouched holdout
- chosen coefficients are unstable across windows
- randomized or permuted controls produce similar gains
- candidate requires post-hoc crisis-specific retuning
- candidate cannot be replayed from frozen artifacts

### FR-18 Calibration Freeze Artifact

Every accepted production calibration shall produce a frozen artifact containing:

- chosen parameters
- validation windows
- holdout window
- metric panel
- code revision
- artifact checksums

This artifact is mandatory for release certification.

---

## 10. 可复现性与环境需求 (Reproducibility and Environment Requirements)

### NFR-1 Environment Locking

Release acceptance shall run in an environment with:

- fixed Python minor version
- locked dependency graph
- deterministic container image tag

Range-only dependency constraints are insufficient for release certification.

### NFR-2 Network Closure

Acceptance and certification runs shall be network-closed for historical market data.

Any attempted live download during acceptance is a certification failure.

### NFR-3 Replay Determinism

Given the same:

- code revision
- frozen inputs
- initial execution state
- calibration artifacts

the system shall reproduce the same decision trace.

### NFR-4 Observability

Every runtime snapshot shall include enough information to reconstruct:

- raw inputs
- feature vector
- feature availability mask
- feature quality weights
- prior blend details
- posterior
- effective entropy
- floor state
- overlay diagnostics
- final execution path

---

## 11. 运行时快照契约 (Runtime Snapshot Contract)

### FR-19 Mandatory Snapshot Fields

The runtime snapshot schema shall contain, at minimum:

- schema version
- observation date
- raw input payload
- source markers
- feature vector
- feature mask
- feature weights
- prior details
- posterior probabilities
- posterior entropy
- effective entropy
- pre-floor beta
- floor state
- overlay block
- final execution block
- persisted execution-state deltas

### FR-20 Decision Trace Semantics

The snapshot shall explicitly separate:

- belief outputs
- risk transforms
- action outputs

This separation is required to prove that action conditioning does not mutate belief.

---

## 12. 测试与验收映射 (Test and Acceptance Mapping)

### FR-21 Required Test Classes

The implementation shall add or maintain tests covering:

- runtime/backtest parity
- floor parity
- high-entropy streak parity
- likelihood masking for degraded and missing features
- acceptance fail-closed behavior
- replay determinism from frozen artifacts
- calibration artifact completeness

### FR-22 Acceptance Gates

v13.8 may be certified only if all of the following pass:

1. runtime/backtest parity suite passes
2. frozen acceptance backtest passes
3. calibration artifact exists and matches release revision
4. no live-download path is exercised in acceptance
5. all public output contracts remain valid
6. audit narrative does not overstate readiness beyond evidence

---

## 13. 迁移计划 (Migration Plan)

### Phase 1: Parity Extraction

- extract shared decision pipeline
- route runtime and backtest through the same ordered semantics
- add parity snapshot fixtures

### Phase 2: Quality-Aware Inference

- add feature mask and quality-aware likelihood semantics
- remove zero-fill-as-evidence behavior from acceptance path
- preserve diagnostics for degraded vs unavailable inputs

### Phase 3: Frozen Calibration

- define nested walk-forward calibration job
- emit frozen calibration artifact
- add reliability reporting and untouched holdout evidence

### Phase 4: Environment Sealing

- pin Python minor version
- add dependency lockfile strategy
- make acceptance default to frozen artifact mode

### Phase 5: Documentation Alignment

- update SRD/PRD/WIKI wording
- downgrade unsupported `production-ready` claims
- version all acceptance claims to concrete evidence

---

## 14. 已知开放风险 (Open Risks)

The following risks remain acknowledged even after v13.8:

- structural macro regime shift can still invalidate learned class statistics
- free-data providers remain operationally weaker than institutional feeds
- execution overlay can still degrade if market-internal source quality decays
- prior-memory schedules may still need future economic re-baselining

These risks must be disclosed, not hidden.

---

## 15. 最终验收标准 (Final Acceptance Criteria)

The v13.8 hardening release is considered complete only if:

- a single canonical pipeline exists for runtime and backtest
- quality gating affects inference causally, not just diagnostically
- the `0.5` floor is enforced identically in runtime and replay
- high-entropy and ULTIMA semantics are replayable
- acceptance runs are frozen and fail-closed
- calibration is frozen and evidenced by untouched holdout reporting
- release documentation states only what the code and artifacts can prove

---

**Decision Summary**: v13.8 does not ask the system to become smarter. It asks the system to become honest, sealed, and industrial.
