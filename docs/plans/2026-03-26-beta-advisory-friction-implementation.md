# Beta Advisory Friction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a low-turnover advisory-friction layer that smooths beta recommendations without managing real brokerage accounts.

**Architecture:** Keep the existing raw beta signal intact, add an advisory state machine on top of it, and wire both live and backtest paths to emit raw and advised beta separately. Backtests will assume recommendations auto-execute for the advisory state only, not for real-account control.

**Tech Stack:** Python 3.12, pytest, pandas, matplotlib, existing v8 runtime pipeline

---

## User Stories

- As a low-turnover investor, I want the system to avoid repeated short-horizon beta flip-flops so transaction friction does not dominate the signal.
- As a risk-conscious investor, I want major risk events to still force fast defensive beta cuts.
- As a report reader, I want to see both raw beta intent and advised beta output so I can audit what the model wanted versus what the advisory policy recommended.
- As a product owner, I want the system to stay firmly outside real-account management while still modeling advisory state consistently.

## Tasks

### Task 1: Freeze the current execution-policy behavior with failing tests

**Files:**
- Modify: `tests/unit/test_execution_policy.py`
- Test: `tests/unit/test_execution_policy.py`

**Step 1: Write failing tests**

- Add tests for:
  - no-trade band blocks repeated rebalance advice
  - min hold blocks non-emergency advice
  - crisis overrides friction
  - upshift confirmation is stricter than downshift confirmation
  - max step caps advised beta changes

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_execution_policy.py -q`

**Step 3: Write minimal implementation**

- Add advisory friction dataclasses and decision builder in `src/engine/execution_policy.py`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_execution_policy.py -q`

### Task 2: Wire live v8 output to advisory semantics

**Files:**
- Modify: `src/main.py`
- Modify: `src/models/__init__.py`
- Modify: `src/output/cli.py`
- Test: `tests/integration/test_v7_runtime_pipeline.py`

**Step 1: Write failing test**

- Assert live runtime results include `raw_target_beta`, advisory `target_beta`, and updated `should_adjust` semantics.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_v7_runtime_pipeline.py -q`

**Step 3: Write minimal implementation**

- Restore advisory state from history.
- Call advisory friction builder.
- Persist raw and advised values into `SignalResult`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_v7_runtime_pipeline.py -q`

### Task 3: Persist advisory fields

**Files:**
- Modify: `src/store/db.py`
- Modify: `tests/unit/test_v7_persistence.py`
- Modify: `tests/unit/test_persistence_v6_4.py`

**Step 1: Write failing tests**

- Cover persistence and migration of advisory fields.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_v7_persistence.py tests/unit/test_persistence_v6_4.py -q`

**Step 3: Write minimal implementation**

- Add raw/advised beta and advisory-state fields to persistence blobs.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_v7_persistence.py tests/unit/test_persistence_v6_4.py -q`

### Task 4: Add advisory friction to signal backtests

**Files:**
- Modify: `src/backtest.py`
- Modify: `tests/integration/test_signal_alignment_backtests.py`
- Modify: `tests/integration/test_backtest_research_data_contract.py`

**Step 1: Write failing tests**

- Assert signal backtest emits raw and advised beta columns.
- Assert advisory state advances in auto-assume-executed mode.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_signal_alignment_backtests.py tests/integration/test_backtest_research_data_contract.py -q`

**Step 3: Write minimal implementation**

- Thread advisory state through `build_signal_timeseries`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_signal_alignment_backtests.py tests/integration/test_backtest_research_data_contract.py -q`

### Task 5: Add advisory friction to portfolio backtests

**Files:**
- Modify: `src/backtest.py`
- Modify: `tests/integration/test_backtest_v8_pipeline.py`
- Modify: `tests/unit/test_backtest_v6_4.py`

**Step 1: Write failing tests**

- Assert portfolio backtest rebalances only when advisory says adjust.
- Assert friction-adjusted turnover is lower than raw daily alignment turnover on a churny fixture.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_backtest_v8_pipeline.py tests/unit/test_backtest_v6_4.py -q`

**Step 3: Write minimal implementation**

- Use advisory decision to gate rebalance.
- Add friction metrics to summaries.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_backtest_v8_pipeline.py tests/unit/test_backtest_v6_4.py -q`

### Task 6: Upgrade reporting and charts

**Files:**
- Modify: `src/output/backtest_plots.py`
- Modify: `scripts/plot_beta_backtest_performance.py`
- Modify: `docs/backtest_report.md`
- Modify: `tests/unit/test_backtest_plots.py`

**Step 1: Write failing tests**

- Assert plots include raw and advised beta.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_backtest_plots.py -q`

**Step 3: Write minimal implementation**

- Plot both beta series.
- Update report copy.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_backtest_plots.py -q`

### Task 7: Run full verification and review

**Files:**
- Modify: `docs/backtest_report.md`
- Modify: `docs/v8.1_beta_advisory_friction_srd.md`
- Modify: `docs/v8.1_beta_advisory_friction_add.md`

**Step 1: Run targeted suites**

Run:
- `pytest tests/unit/test_execution_policy.py -q`
- `pytest tests/integration/test_v7_runtime_pipeline.py -q`
- `pytest tests/integration/test_signal_alignment_backtests.py -q`
- `pytest tests/integration/test_backtest_v8_pipeline.py -q`
- `pytest tests/unit/test_backtest_plots.py -q`

**Step 2: Run broad verification**

Run:
- `pytest tests/unit -q`
- `pytest tests/integration -q`
- `ruff check src tests`
- `python scripts/plot_beta_backtest_performance.py`

**Step 3: Review requirements**

- Check SRD acceptance criteria line by line.
- Check ADD module mapping line by line.
- Confirm no real-account management capability was added.

**Step 4: Commit**

```bash
git add docs src tests scripts artifacts docs/images
git commit -m "feat: add low-turnover beta advisory friction"
```
