# Dual Signal Audit Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate the system into two auditable decision surfaces, `target_beta` for stock-of-assets risk control and `deployment_state` for incremental cash timing, then evaluate each surface directly against an expected market-date matrix.

**Architecture:** The runtime pipeline remains the source of truth for daily decisions. Backtesting is split into a pure signal-generation layer and two expectation-alignment audit layers. Legacy portfolio/NAV backtests remain available as research tools, but acceptance for the production decision system moves to signal alignment rather than mixed return comparisons. The runtime semantics also need to be internally consistent: `RISK_EXIT` must allow true `0 beta` cash fallback and `EUPHORIC` must be able to surface `RISK_ON` / `>1.0 beta` recommendations.

**Tech Stack:** Python 3.12, pandas, pytest, Ruff, canonical macro dataset loader, runtime candidate registry.

---

### Task 1: Extract pure daily signal generation

**Files:**
- Modify: `src/backtest.py`
- Test: `tests/integration/test_signal_alignment_backtests.py`

**Steps:**
1. Add a daily `build_signal_timeseries()` path that reuses Tier-0, Risk, Search, and Deployment logic without cash-transfer simulation.
2. Ensure the emitted frame contains `signal_target_beta`, `deployment_state`, `tier0_regime`, `risk_state`, and `selected_candidate_id`.
3. Verify with integration tests that a controlled macro path produces deterministic beta and deployment outputs.

### Task 2: Add expectation-driven signal audits

**Files:**
- Modify: `src/backtest.py`
- Test: `tests/integration/test_signal_alignment_backtests.py`

**Steps:**
1. Add `backtest_target_beta_alignment()` with `MAE`, `RMSE`, and tolerance-hit metrics.
2. Add `backtest_deployment_alignment()` with exact-match and ranked-distance metrics.
3. Keep the daily joined frame in each summary for diagnosis and review.

### Task 3: Build the executable audit workflow

**Files:**
- Modify: `src/backtest.py`
- Modify: `README.md`
- Test: `tests/integration/test_backtest_research_data_contract.py`

**Steps:**
1. Add expectation-matrix CSV loading and validation.
2. Add `run_signal_audits()` and CLI modes for `beta`, `deployment`, and `both`.
3. Reject synthetic `dev-fixture` macro datasets by default for acceptance audits.

### Task 3.5: Restore the full runtime decision space

**Files:**
- Modify: `src/engine/risk_controller.py`
- Modify: `src/engine/allocation_search.py`
- Modify: `data/candidate_registry_v7.json`
- Test: `tests/unit/test_risk_controller.py`
- Test: `tests/unit/test_allocation_search_v8.py`
- Test: `tests/integration/test_signal_alignment_backtests.py`

**Steps:**
1. Make `CRISIS` and hard drawdown breaches map to a real `0.0` exposure ceiling.
2. Make `EUPHORIC` clean regimes surface `RISK_ON` instead of collapsing into `RISK_NEUTRAL`.
3. Ensure runtime candidate search can legally choose `0.0 beta` candidates.

### Task 4: Preserve legacy research backtests

**Files:**
- Modify: `src/backtest.py`
- Test: `tests/integration/test_backtest_v8_pipeline.py`
- Test: `tests/unit/test_backtest_v6_4.py`

**Steps:**
1. Keep the existing mixed NAV backtest path intact for research and regression coverage.
2. Reuse shared price and macro loaders where possible.
3. Re-run legacy backtest tests after signal-audit changes.

### Task 5: Verification and delivery

**Files:**
- Modify: `README.md`
- Create: `docs/plans/2026-03-26-dual-signal-audit-refactor.md`

**Steps:**
1. Run focused integration/unit tests for new audits and legacy regressions.
2. Verify README commands and data prerequisites match implementation.
3. Commit only refactor-related files and create a GitHub PR with acceptance evidence.
