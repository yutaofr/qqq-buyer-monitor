# v13.8 Industrial Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the v13.8 industrial hardening SRD without changing the v13.7 economic model, while making runtime and backtest behavior parity-safe, acceptance reproducible, and degraded data causally safer.

**Architecture:** Do not invent a new inference system. First extract the existing live runtime semantics into shared modules with zero behavior change. Then route backtest through the same shared path. Only after parity is proven may you add likelihood-time quality gating and frozen acceptance/reporting. Every behavior change must be isolated, tested, and evaluated against a frozen baseline before it is kept.

**Tech Stack:** Python 3.13, `pytest`, `ruff`, Docker Compose, pandas, NumPy, scikit-learn, JSON audit artifacts, frozen CSV backtest inputs

---

## Before You Touch Code

This plan is written for a junior engineer. Follow it literally.

### Hard Rules

1. Do not change factor topology.
2. Do not change regime labels.
3. Do not change `base_betas` or `regime_sharpes`.
4. Do not remove the `0.5` beta floor.
5. Do not tune numerical constants until runtime/backtest parity is proven.
6. Do not edit files outside the task's file list.
7. Do not "fix forward" with random hacks. If a step behaves unexpectedly, stop and diagnose.
8. Do not delete the old backtest path until the new path is proven equivalent on frozen inputs.
9. Do not change public output field names unless the task explicitly says to add a new one.
10. Do not use live downloads in acceptance-mode verification.

### Global Stop Conditions

Stop immediately and do not continue if:

- a targeted test fails for a reason you do not understand
- more than 5 files changed in a task that was supposed to touch 2-3 files
- canonical parity breaks before the quality-gating task
- a backtest metric changes on canonical `quality=1.0` data before the quality-gating task

### Files You Must Read First

Read these before coding:

- `docs/srd/v13_8_INDUSTRIAL_HARDENING_SRD.md`
- `docs/srd/v13_7_ULTIMA_SRD.md`
- `docs/versions/v13/V13_EXECUTION_OVERLAY_SRD.md`
- `docs/versions/v13/V13_BACKTEST_PROTOCOL.md`
- `docs/core/PRD.md`
- `src/engine/v11/conductor.py`
- `src/backtest.py`
- `src/engine/v11/core/bayesian_inference.py`
- `src/engine/v11/core/prior_knowledge.py`
- `src/engine/v13/execution_overlay.py`
- `tests/fixtures/forensics/snapshot_2026-03-31.json`

### Global Quality Gate After Every Task

Run all three:

```bash
git diff --stat
docker compose run --rm test ruff check <changed files>
docker compose run --rm test pytest <targeted tests> -q
```

Expected:

- `git diff --stat` only shows files listed in the task
- `ruff check` returns exit code `0`
- targeted tests pass

If any of these fail, do not move to the next task.

---

## Definition of Done

This project is not done when code compiles. It is done only when all of the following are true:

1. Runtime and backtest share the same post-posterior decision pipeline.
2. Canonical frozen inputs produce matching parity fields in runtime and replay.
3. Missing or degraded features are suppressed at likelihood time, not merely punished after the fact.
4. Acceptance mode is frozen and fails closed.
5. Backtest matrix output is sufficient to judge whether the hardening is pertinent.
6. Final metrics are acceptable under the pertinence rules at the end of this document.

---

### Task 1: Freeze a Baseline and Record What Must Not Change

**Files:**
- Create: `artifacts/v13_8_baseline/`
- Modify: none

**Purpose:** Create a frozen baseline before refactoring anything. You need this to detect accidental behavior drift.

**Step 1: Run the existing targeted unit tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_v13_4_inference.py \
  tests/unit/engine/v13/test_execution_overlay.py \
  tests/unit/engine/v11/test_conductor_overlay_integration.py \
  tests/unit/test_backtest_v13_overlay.py \
  -q
```

Expected:

- all tests pass

**Step 2: Run a frozen acceptance backtest in a new artifact directory**

Run:

```bash
docker compose run --rm backtest python -m src.backtest \
  --evaluation-start 2018-01-01 \
  --acceptance \
  --overlay-mode FULL \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-03-31 \
  --artifact-dir artifacts/v13_8_baseline
```

Expected:

- command exits `0`
- files appear in `artifacts/v13_8_baseline/`
- `summary.json`, `execution_trace.csv`, and `full_audit.csv` exist

**Step 3: Record the baseline metrics**

Open and note:

- `artifacts/v13_8_baseline/summary.json`
- `artifacts/v13_8_baseline/execution_trace.csv`

Record these values in your notes:

- `top1_accuracy`
- `mean_brier`
- `mean_entropy`
- `lock_incidence`
- first 5 rows of `raw_target_beta`
- first 5 rows of `target_beta`

**Step 4: Do not edit code until the baseline exists**

If baseline artifacts are missing, stop. Do not continue.

---

### Task 2: Extract Shared Data-Quality Logic With Zero Behavior Change

**Files:**
- Create: `src/engine/v11/core/data_quality.py`
- Modify: `src/engine/v11/conductor.py`
- Create: `tests/unit/engine/v11/test_data_quality.py`

**Purpose:** Backtest cannot share runtime semantics until the quality logic is no longer trapped inside `conductor.py`.

**Step 1: Write the failing tests**

Create tests for:

- `test_apply_data_quality_penalty_matches_current_conductor_behavior`
- `test_assess_data_quality_returns_expected_reason_for_missing_core_field`
- `test_feature_reliability_weights_zero_out_missing_raw_features`
- `test_detect_source_switch_flags_build_version_change`

Use the existing snapshot fixture:

- `tests/fixtures/forensics/snapshot_2026-03-31.json`

**Step 2: Run the new tests and make sure they fail**

Run:

```bash
docker compose run --rm test pytest tests/unit/engine/v11/test_data_quality.py -q
```

Expected:

- failure due to missing module or missing functions

**Step 3: Write the minimal shared implementation**

Move only these behaviors into `src/engine/v11/core/data_quality.py`:

- `apply_data_quality_penalty`
- `normalize_source_marker`
- `detect_source_switch`
- `assess_data_quality`
- `feature_reliability_weights`
- any tiny helper required by those functions

Use these exact function names:

```python
def apply_data_quality_penalty(*, posterior_entropy: float, quality_score: float) -> float: ...

def normalize_source_marker(raw_source: object) -> str: ...

def detect_source_switch(latest_raw: pd.Series, *, previous_raw: pd.Series | None = None) -> dict[str, object]: ...

def assess_data_quality(
    latest_raw: pd.Series,
    *,
    previous_raw: pd.Series | None,
    registry: dict[str, object],
    field_specs: dict[str, tuple[str, str | None, str | None]],
) -> dict[str, object]: ...

def feature_reliability_weights(
    *,
    latest_vector: pd.DataFrame,
    latest_raw: pd.Series,
    field_quality: dict[str, float],
    seeder_config: dict[str, dict[str, object]],
) -> dict[str, float]: ...
```

**Step 4: Switch `conductor.py` to import and use the shared functions**

Do not change behavior. This is an extraction only.

**Step 5: Run the targeted tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/engine/v11/test_data_quality.py \
  tests/unit/engine/v11/test_conductor.py \
  tests/unit/engine/v11/test_conductor_overlay_integration.py \
  -q
```

Expected:

- all pass

**Step 6: Verify no backtest metric changed**

Re-run the baseline command from Task 1 into:

- `artifacts/v13_8_task2_check/`

Compare:

- `summary.json`
- first 20 rows of `raw_target_beta`
- first 20 rows of `target_beta`

Expected:

- no change

If anything changed, you introduced behavior drift. Undo the extraction and retry.

---

### Task 3: Extract a Shared Execution Pipeline With Zero Behavior Change

**Files:**
- Create: `src/engine/v11/core/execution_pipeline.py`
- Modify: `src/engine/v11/conductor.py`
- Create: `tests/unit/engine/v11/test_execution_pipeline.py`

**Purpose:** Pull the post-posterior decision path out of `conductor.py` so runtime and backtest can share it.

**Step 1: Write the failing tests**

Create tests for:

- `test_execution_pipeline_matches_snapshot_floor_and_overlay_order`
- `test_execution_pipeline_sets_is_floor_active_correctly`
- `test_execution_pipeline_preserves_hydration_anchor`
- `test_execution_pipeline_updates_high_entropy_streak_correctly`

Base expectations on:

- `tests/fixtures/forensics/snapshot_2026-03-31.json`

**Step 2: Run the tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest tests/unit/engine/v11/test_execution_pipeline.py -q
```

Expected:

- failure because the module does not exist

**Step 3: Write a minimal pipeline module**

Create `src/engine/v11/core/execution_pipeline.py` with only these pure helpers:

```python
def compute_effective_entropy(*, posterior_entropy: float, quality_score: float) -> float: ...

def compute_pre_floor_beta(*, raw_beta: float, effective_entropy: float, state_count: int, entropy_controller: Any) -> float: ...

def apply_beta_floor(*, pre_floor_beta: float, floor: float = 0.5) -> tuple[float, bool]: ...

def compute_overlay_beta(*, protected_beta: float, beta_overlay_multiplier: float) -> float: ...

def compute_deployment_readiness(*, effective_entropy: float, e_sharpe: float, erp_percentile: float) -> float: ...

def run_execution_pipeline(... ) -> dict[str, Any]: ...
```

`run_execution_pipeline(...)` must return at least:

- `posterior_entropy`
- `effective_entropy`
- `raw_target_beta`
- `raw_target_beta_pre_floor`
- `protected_beta`
- `overlay_beta`
- `target_beta`
- `is_floor_active`
- `deployment_readiness`
- `deployment_readiness_overlay`
- `high_entropy_streak`
- `hydration_anchor`

**Step 4: Switch `conductor.py` to use the shared pipeline**

Important:

- keep public result keys unchanged
- do not change existing floor semantics yet
- do not tune constants

**Step 5: Run targeted tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/engine/v11/test_execution_pipeline.py \
  tests/unit/engine/v11/test_conductor.py \
  tests/unit/engine/v11/test_conductor_overlay_integration.py \
  tests/unit/test_main_v11.py \
  -q
```

Expected:

- all pass

**Step 6: Re-run the frozen acceptance backtest**

Write results to:

- `artifacts/v13_8_task3_check/`

Expected:

- `summary.json` unchanged from baseline
- `raw_target_beta` unchanged
- `target_beta` unchanged

If changed, fix the ordering bug. Do not touch tuning values.

---

### Task 4: Wire Backtest to Shared Quality and Execution Modules Behind a Safety Flag

**Files:**
- Modify: `src/backtest.py`
- Modify: `tests/unit/test_backtest_v13_overlay.py`
- Create: `tests/integration/engine/v11/test_runtime_backtest_parity.py`

**Purpose:** Introduce the new path safely before making it the default.

**Step 1: Add a temporary experiment flag**

In `src/backtest.py`, add:

```python
use_canonical_pipeline = bool(experiment.get("use_canonical_pipeline", False))
```

Do not default it to `True` yet.

**Step 2: Write failing tests**

Add tests for:

- `test_backtest_old_and_new_path_match_when_use_canonical_pipeline_is_true`
- `test_backtest_exports_raw_target_beta_pre_floor_and_is_floor_active`
- `test_runtime_and_backtest_parity_on_frozen_row`

Expected parity fields:

- `raw_target_beta`
- `raw_target_beta_pre_floor`
- `protected_beta`
- `overlay_beta`
- `target_beta`
- `is_floor_active`
- `hydration_anchor`

**Step 3: Run tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_backtest_v13_overlay.py \
  tests/integration/engine/v11/test_runtime_backtest_parity.py \
  -q
```

Expected:

- failure because the new path is not wired

**Step 4: Wire the new path**

In the `use_canonical_pipeline=True` branch:

- compute `quality_audit` using the shared data-quality module
- compute `feature_weights`
- preserve existing posterior logic
- call `run_execution_pipeline(...)`
- export the parity fields into `execution_rows`

**Step 5: Run targeted tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_backtest_v13_overlay.py \
  tests/integration/engine/v11/test_runtime_backtest_parity.py \
  -q
```

Expected:

- all pass

**Step 6: Run a side-by-side parity check**

Run old path:

```bash
docker compose run --rm backtest python -m src.backtest \
  --evaluation-start 2018-01-01 \
  --acceptance \
  --overlay-mode FULL \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-03-31 \
  --artifact-dir artifacts/v13_8_task4_old
```

Run new path:

```bash
docker compose run --rm backtest python -m src.backtest \
  --evaluation-start 2018-01-01 \
  --acceptance \
  --overlay-mode FULL \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-03-31 \
  --artifact-dir artifacts/v13_8_task4_new
```

Use `experiment_config={"use_canonical_pipeline": True}` through a small targeted test or temporary harness. Do not change the CLI yet.

Expected:

- canonical fields match

If not, debug state propagation first. Do not tune anything.

---

### Task 5: Make the Shared Backtest Path the Default and Remove Duplicate Semantics

**Files:**
- Modify: `src/backtest.py`
- Modify: `tests/unit/test_backtest_v13_overlay.py`

**Purpose:** Once parity is proven, remove the dangerous duplication.

**Step 1: Flip the default**

Change:

```python
use_canonical_pipeline = bool(experiment.get("use_canonical_pipeline", False))
```

to:

```python
use_canonical_pipeline = bool(experiment.get("use_canonical_pipeline", True))
```

**Step 2: Remove the old inline post-posterior risk path**

Delete only the duplicated logic that is now inside the shared pipeline.

Do not delete:

- data loading
- model fitting
- posterior calculation
- artifact writing

**Step 3: Run tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_backtest_v13_overlay.py \
  tests/unit/test_backtest_v11.py \
  tests/integration/engine/v11/test_runtime_backtest_parity.py \
  -q
```

Expected:

- all pass

**Step 4: Re-run the frozen acceptance backtest**

Write to:

- `artifacts/v13_8_task5_check/`

Expected:

- canonical metrics equal baseline

If this changes, you removed logic incorrectly. Restore the old path and isolate the diff.

---

### Task 6: Add Likelihood-Time Quality Gating

**Files:**
- Modify: `src/engine/v11/core/bayesian_inference.py`
- Modify: `src/engine/v11/conductor.py`
- Modify: `src/backtest.py`
- Modify: `src/engine/v11/resources/v13_4_weights_registry.json`
- Modify: `tests/unit/test_v13_4_inference.py`
- Create: `tests/unit/engine/v11/test_quality_gated_inference.py`

**Purpose:** Make degraded and missing features causally weaker in inference, not just cosmetically audited.

**Step 1: Add a new optional parameter to inference**

Extend the function signature:

```python
def infer_gaussian_nb_posterior(
    ...,
    feature_quality_weights: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
```

Default must preserve old behavior.

**Step 2: Write failing tests**

Create tests for:

- `test_quality_weight_1_preserves_existing_math`
- `test_missing_feature_quality_0_removes_feature_contribution`
- `test_degraded_feature_quality_reduces_confidence_not_increases_it`
- `test_all_quality_1_keeps_canonical_outputs_identical`

Use simple mock classifiers like the existing inference tests.

**Step 3: Run tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_v13_4_inference.py \
  tests/unit/engine/v11/test_quality_gated_inference.py \
  -q
```

Expected:

- failure because `feature_quality_weights` is not used

**Step 4: Implement the minimal gating**

Use this rule first. Do not invent a fancy curve:

```python
effective_feature_weight = registry_weight * feature_quality_weight
```

where:

- canonical feature => `1.0`
- degraded feature => existing quality score, clipped to `[0, 1]`
- unavailable feature => `0.0`

Do not multiply the observation value itself.
Only change the contribution weight.

**Step 5: Pass `feature_quality_weights` from runtime and backtest**

Use the shared `feature_reliability_weights(...)` output.

**Step 6: Add registry keys only if you truly need them**

If no new registry constant is needed, do not add one.
If one is needed, add the smallest possible key to:

- `src/engine/v11/resources/v13_4_weights_registry.json`

**Step 7: Run tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/test_v13_4_inference.py \
  tests/unit/engine/v11/test_quality_gated_inference.py \
  tests/unit/engine/v11/test_conductor.py \
  tests/unit/test_backtest_v13_overlay.py \
  -q
```

Expected:

- all pass

**Step 8: Verify no drift on canonical quality**

Re-run the frozen acceptance backtest into:

- `artifacts/v13_8_task6_check/`

Expected:

- if all relevant quality scores are `1.0`, canonical outputs remain unchanged

If canonical outputs changed, your quality gating is wrong. Fix code, not parameters.

---

### Task 7: Harden Acceptance Mode and Environment Reproducibility

**Files:**
- Modify: `src/backtest.py`
- Modify: `scripts/run_v13_backtest_matrix.py`
- Create: `.python-version`
- Create or Modify: `requirements.lock.txt` or another explicit lock artifact chosen by the team
- Modify: `tests/unit/test_backtest_v13_overlay.py`

**Purpose:** Make acceptance reproducible and fail-closed.

**Step 1: Write failing tests**

Add tests for:

- `test_acceptance_rejects_missing_price_cache`
- `test_acceptance_rejects_missing_end_date`
- `test_acceptance_never_uses_date_today`
- `test_acceptance_never_uses_live_download`

**Step 2: Run tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_backtest_v13_overlay.py -q
```

Expected:

- failure on at least one new case

**Step 3: Make acceptance mode stricter**

Acceptance must require:

- `--price-cache-path`
- `--price-end-date`
- `allow_price_download=False`

Also:

- do not use moving default end dates in acceptance calculations
- emit a clear error if any frozen artifact is missing

**Step 4: Add Python-version lock**

Create:

- `.python-version`

Value:

```text
3.13
```

**Step 5: Add dependency lock artifact**

Use the simplest team-approved method.
Do not invent a new package manager.
If the team has no existing lock strategy, choose `requirements.lock.txt` generated from the Docker environment and document how it was produced.

**Step 6: Run tests**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_backtest_v13_overlay.py -q
```

Expected:

- all pass

---

### Task 8: Extend the Backtest Matrix So a Human Can Judge Pertinence

**Files:**
- Modify: `scripts/run_v13_backtest_matrix.py`
- Create: `tests/unit/test_v13_8_backtest_matrix.py`

**Purpose:** The backtest must answer "Did the hardening matter in the right direction?" not just "Did it run?"

**Step 1: Write failing tests**

Add tests for summary columns:

- `max_raw_target_beta_delta_vs_disabled`
- `mean_target_beta_delta_vs_disabled`
- `left_tail_mean_beta`
- `mean_turnover`
- `penalty_days`
- `reward_days`
- `acceptance_pass`
- `acceptance_fail_reason`

**Step 2: Run tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_v13_8_backtest_matrix.py -q
```

Expected:

- failure because the columns do not exist

**Step 3: Add pass/fail logic**

Add an `acceptance_pass` boolean with these rules:

- canonical parity fields unchanged when expected
- `left_tail_mean_beta` is not higher than baseline in degraded-safety scenarios
- `reward_days <= penalty_days`
- no live-download path used
- no unsupported acceptance inputs

Add `acceptance_fail_reason` as a short machine-readable string.

**Step 4: Run tests**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_v13_8_backtest_matrix.py -q
```

Expected:

- all pass

---

### Task 9: Add a Frozen Calibration Evidence Artifact

**Files:**
- Create: `scripts/run_v13_8_calibration_report.py`
- Create: `tests/unit/test_v13_8_calibration_report.py`

**Purpose:** Do not let anyone claim "calibrated" without an artifact.

**Step 1: Write failing tests**

The report script must emit JSON containing:

- `code_revision`
- `evaluation_start`
- `evaluation_end`
- `price_cache_path`
- `parameter_values`
- `holdout_window`
- `summary_metrics`
- `reliability_required`

**Step 2: Run tests and confirm failure**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_v13_8_calibration_report.py -q
```

Expected:

- failure because the script does not exist

**Step 3: Write the minimal script**

The script does not need to re-train a new model.
It only needs to:

- read frozen backtest artifacts
- collect the required metadata
- emit a versioned JSON artifact

Output location:

- `artifacts/v13_8_acceptance/calibration_report.json`

**Step 4: Run tests**

Run:

```bash
docker compose run --rm test pytest tests/unit/test_v13_8_calibration_report.py -q
```

Expected:

- all pass

---

### Task 10: Run the Full Verification Sequence

**Files:**
- None

**Step 1: Run all targeted unit and integration tests**

Run:

```bash
docker compose run --rm test pytest \
  tests/unit/engine/v11/test_data_quality.py \
  tests/unit/engine/v11/test_execution_pipeline.py \
  tests/unit/engine/v11/test_quality_gated_inference.py \
  tests/unit/engine/v11/test_conductor.py \
  tests/unit/engine/v11/test_conductor_overlay_integration.py \
  tests/unit/test_v13_4_inference.py \
  tests/unit/test_backtest_v13_overlay.py \
  tests/unit/test_v13_8_backtest_matrix.py \
  tests/unit/test_v13_8_calibration_report.py \
  tests/integration/engine/v11/test_runtime_backtest_parity.py \
  -q
```

Expected:

- all pass

**Step 2: Run the frozen acceptance backtest**

Run:

```bash
docker compose run --rm backtest python -m src.backtest \
  --evaluation-start 2018-01-01 \
  --acceptance \
  --overlay-mode FULL \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-03-31 \
  --artifact-dir artifacts/v13_8_acceptance
```

Expected:

- exits `0`
- no live download

**Step 3: Run the backtest matrix**

Run:

```bash
docker compose run --rm backtest python scripts/run_v13_backtest_matrix.py \
  --dataset-path data/macro_historical_dump.csv \
  --regime-path data/v11_poc_phase1_results.csv \
  --evaluation-start 2018-01-01 \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-03-31 \
  --output-dir artifacts/v13_8_matrix
```

Expected:

- `matrix_summary.csv` exists
- `matrix_summary.json` exists

**Step 4: Run the calibration evidence script**

Run:

```bash
docker compose run --rm backtest python scripts/run_v13_8_calibration_report.py
```

Expected:

- `artifacts/v13_8_acceptance/calibration_report.json` exists

---

## How to Analyze Whether the Change Is Pertinent

This section tells you how to decide if the hardening helped, hurt, or did nothing useful.

### A. Parity Criteria

These must be true before you consider tuning anything:

- on canonical `quality=1.0` inputs, `raw_target_beta` is unchanged
- on canonical `quality=1.0` inputs, `raw_target_beta_pre_floor` is unchanged
- `is_floor_active` matches runtime semantics
- `hydration_anchor` survives replay

If any of these fail, the architecture is not aligned. Stop. Fix parity first.

### B. Safety Criteria

On degraded or missing-feature fixtures:

- effective entropy must stay the same or increase
- `protected_beta` must stay the same or decrease
- `target_beta` must not increase
- deployment readiness must stay the same or decrease unless the scenario is explicitly a positive overlay repair case

If degraded data causes more conviction, the change is wrong.

### C. Acceptance Criteria

From `artifacts/v13_8_matrix/matrix_summary.csv`:

- `max_raw_target_beta_delta_vs_disabled == 0.0` for neutral and parity scenarios
- `reward_days <= penalty_days`
- `left_tail_mean_beta` is not worse than baseline in safety scenarios
- `mean_turnover` is not materially higher without a clear safety gain

### D. Calibration Criteria

The change is not pertinent if:

- holdout metrics worsen and safety does not improve
- a gain appears only in one crisis window
- you need to retune many constants to hide a bug

---

## If the Results Are Not Good Enough

Do not improvise. Use this decision tree.

### Case 1: Canonical parity broke

Symptoms:

- `raw_target_beta` changed on canonical frozen data
- baseline summary changed before the quality-gating task

Action:

1. inspect pipeline ordering
2. inspect execution-state propagation
3. inspect floor application order
4. inspect overlay application order

Do not touch:

- registry constants
- priors
- factor weights

### Case 2: Degraded data still creates too much conviction

Symptoms:

- degraded fixture lowers entropy
- degraded fixture increases beta

Action:

1. inspect `feature_quality_weights` plumbing
2. confirm unavailable features map to `0.0`
3. confirm degraded features reduce contribution weight, not increase it
4. only if code is correct, adjust the quality transfer function

Allowed tuning files:

- `src/engine/v11/resources/v13_4_weights_registry.json`

Forbidden tuning files:

- `data/v11_poc_phase1_results.csv`
- `src/engine/v11/resources/regime_audit.json`
- `scripts/v11_poc_phase1.py`

### Case 3: Holdout metrics worsen but parity is fine

Action:

1. reject the last tuning change
2. revert only the tuning constant
3. rerun the frozen matrix
4. keep the architectural refactor

Do not:

- chase a single crisis window
- change labels
- add new factors

### Case 4: Turnover jumps with no safety benefit

Action:

1. inspect whether the pipeline changed inertial or behavioral order
2. inspect whether `target_beta` now bypasses a guard
3. inspect whether degraded data is oscillating between masked and unmasked states

Only if the code is correct may you adjust:

- masking stability behavior

Do not adjust:

- economic regimes
- base beta table

---

## Iteration Loop

You are not done when the first attempt compiles. Use this loop.

### Loop Start

1. make one small change
2. run targeted tests
3. run frozen acceptance backtest
4. run matrix summary
5. compare against baseline

### Keep the Change Only If

All are true:

1. no canonical parity regression
2. degraded-source safety improved or stayed neutral
3. acceptance remains fail-closed
4. turnover did not worsen without explanation
5. holdout evidence is not worse in a meaningful way

### Reject the Change If

Any are true:

1. it fixes one crisis and harms the rest
2. it requires touching unrelated constants
3. it changes canonical outputs unexpectedly
4. it adds a second source of truth
5. it makes the code harder to explain than before

### Loop End Condition

The loop ends only when:

- all tests pass
- frozen acceptance passes
- matrix summary is acceptable
- calibration evidence artifact exists
- code changes remain narrow and explainable

If you cannot satisfy all of the above without broad invasive changes, stop and escalate. Do not manufacture a local optimum and call it done.

---

## Final Sanity Checklist

Before closing the work, answer all of these with `yes`:

1. Did I preserve the v13.7 economic model?
2. Did I remove code duplication instead of adding another path?
3. Did I keep all changes inside the listed files?
4. Did I prove parity before tuning?
5. Did I reject live downloads in acceptance?
6. Did I avoid changing labels, betas, and regime tables?
7. Did I produce artifacts a reviewer can inspect without trusting me?

If any answer is `no`, the work is not complete.

---

### Task 11: Document Alignment and Audit Narrative (Phase 5)

**Files:**
- Modify: `docs/core/PRD.md` (or other relevant index specs)
- Modify: `src/backtest.py`
- Modify: `src/engine/v11/core/prior_knowledge.py`

**Purpose:** Bring documentation and output traces into alignment with actual code behavior, satisfying `FR-7` (Prior Gravity Transparency) and `FR-10` (Audit Narrative Discipline) to remove unsupported "production-ready" claims.

**Step 1: Ensure Prior Transparency in Execution Trace**
In `src/backtest.py`, when exporting the `full_audit_df` or `execution_trace.csv`, ensure the raw prior tracking details (e.g., `base_weight`, `posterior_weight`, `transition_weight`) computed by `PriorKnowledgeBase` are explicitly snapshotted on each row. Do not change the 5% baseline logic! Only export it to dataframes for transparency.

**Step 2: Update Prior Knowledge Documentation**
Add clear docstrings in `src/engine/v11/core/prior_knowledge.py` that describe the staged blend process (`base_weight`, `posterior_weight`, `transition_weight`) to resolve the "Description mismatches actual staged logic" discrepancy (SRD Gap G-3). 

**Step 3: Scrub False Production-Ready Claims**
Find and downgrade any claim in our `docs/` that states the system is "v13 production-ready" unless there are frozen artifacts mapped to SRD FR-10.
