# Blood-Chip Crisis Override Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow `Deployment Controller` to fast-deploy new cash during tightly confirmed `CRISIS` reversal windows while keeping stock beta locked in `RISK_EXIT`.

**Architecture:** Keep `Risk Controller` unchanged, add a narrowly scoped crisis override branch inside `Deployment Controller`, thread live soft features into `FeatureSnapshot`, and upgrade backtest/report audits from “zero crisis deployment” to “zero unauthorized crisis deployment”.

**Tech Stack:** Python 3.12, pytest, pandas, existing v8 runtime pipeline, GitHub CLI

---

## Tasks

### Task 1: Freeze the new crisis override behavior with failing unit tests

**Files:**
- Modify: `tests/unit/test_deployment_controller.py`
- Modify: `tests/unit/test_feature_pipeline.py`
- Modify: `tests/unit/test_signal_expectations.py`

**Step 1: Write the failing tests**

- Add tests for:
  - crisis liquidity-reversal path unlocks `DEPLOY_FAST`
  - crisis panic-exhaustion path unlocks `DEPLOY_FAST`
  - crisis smart-money-support path unlocks `DEPLOY_FAST`
  - tactical stress still blocks override
  - new soft features classify as Class B
  - expectation matrix emits `DEPLOY_FAST` under crisis override fixture

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/test_deployment_controller.py tests/unit/test_feature_pipeline.py tests/unit/test_signal_expectations.py -q
```

**Step 3: Write minimal implementation**

- Update `src/engine/feature_pipeline.py`
- Update `src/engine/deployment_controller.py`
- Update `src/research/signal_expectations.py`

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/test_deployment_controller.py tests/unit/test_feature_pipeline.py tests/unit/test_signal_expectations.py -q
```

### Task 2: Wire live and backtest snapshots to the new soft features

**Files:**
- Modify: `src/main.py`
- Modify: `src/backtest.py`
- Modify: `tests/integration/test_v7_runtime_pipeline.py`
- Modify: `tests/integration/test_v8_linear_pipeline.py`

**Step 1: Write the failing tests**

- Assert live/runtime and linear-pipeline fixtures can trigger crisis override while keeping `risk_state == RISK_EXIT`.
- Assert deployment reason is exposed as `blood_chip_crisis_override`.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_v7_runtime_pipeline.py tests/integration/test_v8_linear_pipeline.py -q
```

**Step 3: Write minimal implementation**

- Add live snapshot fields from Tier-1 / Tier-2.
- Add backtest snapshot defaults plus optional row-driven soft flags.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_v7_runtime_pipeline.py tests/integration/test_v8_linear_pipeline.py -q
```

### Task 3: Upgrade signal-alignment and portfolio backtests

**Files:**
- Modify: `src/backtest.py`
- Modify: `scripts/run_signal_acceptance_report.py`
- Modify: `tests/integration/test_signal_alignment_backtests.py`
- Modify: `tests/integration/test_backtest_v8_pipeline.py`
- Modify: `tests/integration/test_backtest_research_data_contract.py`

**Step 1: Write the failing tests**

- Assert `blood_chip_override_active` is present in signal timeseries.
- Assert crisis fast deployment in authorized fixtures is not counted as an unauthorized breach.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_signal_alignment_backtests.py tests/integration/test_backtest_v8_pipeline.py tests/integration/test_backtest_research_data_contract.py -q
```

**Step 3: Write minimal implementation**

- Thread override flag into daily timeseries.
- Change report/audit metrics from `CRISIS deployment breaches` to authorized vs unauthorized counts.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_signal_alignment_backtests.py tests/integration/test_backtest_v8_pipeline.py tests/integration/test_backtest_research_data_contract.py -q
```

### Task 4: Refresh docs, reports, and generated figures

**Files:**
- Modify: `docs/backtest_report.md`
- Modify: `scripts/plot_beta_backtest_performance.py` if needed
- Modify: `scripts/plot_dca_performance.py` only if generation path changes
- Update generated files in `artifacts/` and `docs/images/`

**Step 1: Run verification commands**

Run:

```bash
python scripts/run_signal_acceptance_report.py
python scripts/plot_beta_backtest_performance.py
python scripts/plot_dca_performance.py
python -m src.backtest --mode portfolio
```

**Step 2: Update the report copy**

- Replace old `CRISIS deployment breaches = 0` wording.
- Add new crisis override audit wording and latest measured numbers.

### Task 5: Full verification, commit, and PR workflow

**Files:**
- Modify: any touched docs/source/tests from prior tasks

**Step 1: Run broad verification**

Run:

```bash
pytest tests/unit -q
pytest tests/integration -q
ruff check src tests
```

**Step 2: Review requirements line by line**

- SRD acceptance criteria
- ADD module mapping
- SPT test coverage
- backtest report and figure outputs

**Step 3: Commit**

```bash
git add docs src tests scripts artifacts docs/images
git commit -m "feat: add crisis blood-chip deployment override"
```

**Step 4: Push and create PR**

```bash
git push -u origin feat/v8-2-blood-chip-crisis-override
gh pr create --fill
```

**Step 5: Run five review/fix rounds**

- Add review comments on the PR
- Apply fixes
- Push updates
- Repeat until no further review findings remain
