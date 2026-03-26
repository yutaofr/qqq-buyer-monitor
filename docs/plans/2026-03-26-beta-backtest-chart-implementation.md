# v8.1 Beta Backtest Chart Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a backtest visualization that compares the system's stock-beta recommendation path against QQQ price history, and publish it in the backtest report.

**Architecture:** Keep decision logic unchanged. Add a reusable plotting module in `src/output/` and a thin script wrapper in `scripts/`. Wire the chart into `run_backtest()` as an output-only side effect after the summary is available.

**Tech Stack:** Python 3.12, pandas, matplotlib, pytest.

---

### Task 1: Add a reusable beta backtest plotting module

**Files:**
- Create: `src/output/backtest_plots.py`
- Test: `tests/unit/test_backtest_plots.py`

**Step 1: Write the failing test**

```python
def test_build_beta_backtest_figure_uses_target_beta_and_close():
    ...
```

Run: `pytest tests/unit/test_backtest_plots.py -q`
Expected: FAIL because the module does not exist yet.

**Step 2: Write minimal implementation**

Implement a dark-theme two-panel figure builder and a save helper.

**Step 3: Run test to verify it passes**

Run: `pytest tests/unit/test_backtest_plots.py -q`
Expected: PASS

### Task 2: Wire the chart into the backtest entrypoint

**Files:**
- Modify: `src/backtest.py`
- Test: `tests/integration/test_backtest_research_data_contract.py`

**Step 1: Write the failing test**

Add a guard that ensures `run_backtest()` still works when the summary stub has no `daily_timeseries`.

Run: `pytest tests/integration/test_backtest_research_data_contract.py -q`
Expected: FAIL until the new save path is guarded.

**Step 2: Write minimal implementation**

Call the plotting helper only when `daily_timeseries` is present and usable.

**Step 3: Run test to verify it passes**

Run: `pytest tests/integration/test_backtest_research_data_contract.py -q`
Expected: PASS

### Task 3: Add a standalone regeneration script

**Files:**
- Create: `scripts/plot_beta_backtest_performance.py`

**Step 1: Write the failing test**

No dedicated test is required; validate via direct execution.

**Step 2: Write minimal implementation**

Read the cached price and macro datasets, run the backtest, save the figure to `artifacts/` and `docs/images/`.

**Step 3: Run the script**

Run: `python scripts/plot_beta_backtest_performance.py`
Expected: `artifacts/v8.1_beta_recommendation_performance.png` and `docs/images/v8.1_beta_recommendation_performance.png` exist.

### Task 4: Update report docs

**Files:**
- Modify: `docs/backtest_report.md`

**Step 1: Review the rendered links**

Ensure the report links the new image and says it is a stock-beta audit figure.

**Step 2: Commit**

```bash
git add src/output/backtest_plots.py scripts/plot_beta_backtest_performance.py src/backtest.py tests/unit/test_backtest_plots.py tests/integration/test_backtest_research_data_contract.py docs/backtest_report.md docs/v8.1_stock_beta_backtest_srd.md docs/v8.1_stock_beta_backtest_add.md docs/plans/2026-03-26-beta-backtest-chart-implementation.md
git commit -m "feat(report): add stock beta backtest visualization"
```

