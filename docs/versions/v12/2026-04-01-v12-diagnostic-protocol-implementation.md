# V12 Diagnostic Protocol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reproducible v12 diagnostic and ablation workflow that identifies why the orthogonal-factor backtest underperforms, then applies only cross-window-stable improvements without overfitting.

**Architecture:** Add a small research-grade diagnostics module on top of the existing backtest artifacts, then expose controlled experiment knobs in the probability seeder and backtest runner. The workflow must separate root-cause measurement from tuning, enforce state-contract validation, and emit slice-level evidence for crisis recall, beta protection, entropy behavior, and feature ablations.

**Tech Stack:** Python 3.12+, pandas, existing v12 backtest pipeline, Docker-based test and backtest execution, pytest.

---

### Task 1: Lock the diagnostic contract in tests

**Files:**
- Create: `tests/unit/test_v12_diagnostics.py`
- Modify: `src/research/data_contracts.py`
- Modify: `src/backtest.py`

**Step 1: Write the failing tests**

Add tests that require:
- a validator to reject audit state contracts that contain regimes absent from the label dataset
- a diagnostics function that computes, at minimum, overall accuracy, raw/stable critical recall, crisis-slice recall, beta compression, and a state-support report
- a report entry that explicitly flags unsupported audit regimes such as `CAPITULATION`

**Step 2: Run the targeted tests to verify they fail**

Run:
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c "pip install -e '.[dev]' >/tmp/pip.log && PYTHONPATH=. pytest tests/unit/test_v12_diagnostics.py -q"
```

**Step 3: Implement the minimal validator and diagnostics interfaces**

Add only the smallest amount of code needed to make the tests pass.

**Step 4: Re-run the targeted tests**

Run the same `pytest` command and confirm green.

### Task 2: Add a reusable v12 diagnostics module and CLI entry

**Files:**
- Create: `src/research/v12_diagnostics.py`
- Create: `scripts/run_v12_diagnostics.py`
- Modify: `src/backtest.py`

**Step 1: Write the failing tests for the report shape**

Expand `tests/unit/test_v12_diagnostics.py` with report-shape assertions for:
- crisis windows: `2018Q4`, `2020_COVID`, `2022_H1`
- raw vs stable regime divergence
- raw vs executed beta return and drawdown comparison
- entropy summary
- feature diagnostic summary

**Step 2: Run the tests to verify the new assertions fail**

Run the same targeted `pytest` command.

**Step 3: Implement the diagnostics module**

Implement pure functions that read a backtest audit frame and output:
- summary metrics
- state-support diagnostics
- confusion matrix
- crisis-slice metrics
- raw-vs-executed beta comparison
- entropy timing summary

Expose a thin CLI script that loads `artifacts/v12_audit/full_audit.csv` and writes a JSON/CSV report under `artifacts/v12_diagnostics/`.

**Step 4: Re-run the targeted tests**

Run the same targeted `pytest` command and confirm green.

### Task 3: Parameterize the seeder and backtest for controlled ablations

**Files:**
- Modify: `src/engine/v11/probability_seeder.py`
- Modify: `src/backtest.py`
- Modify: `tests/unit/engine/v11/test_probability_seeder.py`
- Modify: `tests/unit/test_backtest_v11.py`

**Step 1: Write the failing tests**

Add tests that require:
- `ProbabilitySeeder` to accept explicit config overrides for factor windows, smoothing, z-clip range, and orthogonalization mode
- `run_v11_audit` to accept an experiment configuration and preserve the default v12 baseline when no overrides are supplied

**Step 2: Run the targeted tests to verify failure**

Run:
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c "pip install -e '.[dev]' >/tmp/pip.log && PYTHONPATH=. pytest tests/unit/engine/v11/test_probability_seeder.py tests/unit/test_backtest_v11.py tests/unit/test_v12_diagnostics.py -q"
```

**Step 3: Implement narrowly scoped configuration injection**

Support only the experiment knobs needed by the protocol:
- `var_smoothing`
- z-score clip range
- copper/gold and USDJPY ROC lookbacks
- capex smoothing mode
- move/spread orthogonalization mode

Do not change the default baseline behavior.

**Step 4: Re-run the targeted tests**

Run the same targeted `pytest` command and confirm green.

### Task 4: Build the ablation runner and baseline-vs-variant report

**Files:**
- Create: `scripts/run_v12_ablation.py`
- Modify: `src/research/v12_diagnostics.py`
- Modify: `tests/unit/test_v12_diagnostics.py`

**Step 1: Write the failing tests**

Add tests for a comparison function that:
- ranks variants against baseline
- rejects variants that improve one slice while regressing aggregate critical recall or drawdown control
- surfaces unsupported-state and overfitting warnings

**Step 2: Run the targeted tests to verify failure**

Run the same targeted `pytest` command set.

**Step 3: Implement the ablation runner**

Add a script that:
- runs named experiments through `run_v11_audit`
- writes each result to an isolated artifact directory
- compares variants against the default baseline using the diagnostics module

**Step 4: Re-run the targeted tests**

Run the same targeted `pytest` command and confirm green.

### Task 5: Run baseline diagnostics and controlled experiments

**Files:**
- Modify: `artifacts/v12_audit/*`
- Create: `artifacts/v12_diagnostics/*`
- Create: `artifacts/v12_ablations/*`

**Step 1: Run baseline backtest and diagnostics**

Run:
```bash
docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 python -m src.backtest --evaluation-start 2018-01-01
docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 python scripts/run_v12_diagnostics.py
```

**Step 2: Run the protocol ablations**

Run named experiments for:
- lower `var_smoothing`
- looser z clipping
- shorter copper/gold and USDJPY lookbacks
- smoothed capex momentum
- orthogonalization disabled or attenuated

**Step 3: Keep only robust improvements**

Accept a variant only if it improves crisis recall and aggregate metrics without introducing slice-specific regressions or unsupported-state drift.

### Task 6: Verify and document the accepted state

**Files:**
- Modify: `docs/V12_ORTHOGONAL_FACTOR_SPEC.md`
- Modify: `docs/plans/2026-04-01-v12-diagnostic-protocol-implementation.md`
- Modify: `src/engine/v11/resources/regime_audit.json`

**Step 1: Run the relevant verification suite**

Run:
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c "pip install -e '.[dev]' >/tmp/pip.log && PYTHONPATH=. pytest tests/unit -q"
docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 python -m src.backtest --evaluation-start 2018-01-01
docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 python scripts/run_v12_diagnostics.py
```

**Step 2: Update the spec and audit contract**

Document:
- baseline diagnosis
- accepted parameter changes
- rejected overfit variants
- remaining risks

**Step 3: Final review**

Confirm code, docs, artifacts, and runtime contracts agree before closing the loop.
