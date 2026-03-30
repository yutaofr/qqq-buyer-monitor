# V11 Probabilistic Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Converge v11 onto a single probabilistic architecture, wire it into runtime and backtest entrypoints, and align implementation, tests, and docs with the accepted SRD.

**Architecture:** Build a hybrid v11 pipeline where probability is the primary decision surface and behavior constraints are a downstream execution-control layer. The runtime path will produce posterior regime probabilities, entropy-aware target beta, dollar-anchored allocations, and a constrained execution action that enforces cooldown, degradation, and deadband rules without overriding the probabilistic core.

**Tech Stack:** Python 3.12+, pandas, numpy, scikit-learn, pytest, SQLite JSON persistence, existing CLI/backtest infrastructure.

---

### Task 1: Converge The V11 Spec Surface

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/conductor/tracks/v11/spec.md`
- Modify: `/Users/weizhang/w/qqq-monitor/conductor/tracks/v11/add.md`
- Modify: `/Users/weizhang/w/qqq-monitor/conductor/tracks/v11/design_decisions.md`

**Step 1: Update the SRD to define the final hybrid architecture**

Document these invariants:
- posterior probabilities are the primary runtime output
- entropy shrinks risk
- dollar anchoring uses reference capital
- behavior control is downstream and cannot replace the probabilistic core
- degraded data must leave an audit trail

**Step 2: Update the ADD to map those invariants onto code modules**

Document the write paths:
- `core/feature_library.py`
- `core/calibration_service.py`
- `core/bayesian_inference.py`
- `core/position_sizer.py`
- `signal/behavioral_guard.py`
- `conductor.py`

**Step 3: Record the trade-off decision**

State clearly:
- keep deadband and cooldown
- reject state-machine-primary architecture
- retire POC-only convexity claims from production design

### Task 2: Add The Failing V11 Tests

**Files:**
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_position_sizer.py`
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_behavioral_guard.py`
- Modify: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_data_degradation.py`
- Modify: `/Users/weizhang/w/qqq-monitor/tests/integration/engine/v11/test_v11_workflow.py`
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/test_main_v11.py`
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/test_backtest_v11.py`

**Step 1: Write tests for data-quality realism**

Cover:
- anomaly/proxy usage lowers quality even when raw inputs are non-null
- forced downgrade marks `action_required`

**Step 2: Write tests for probability-to-allocation behavior**

Cover:
- higher entropy lowers target beta
- reference-capital anchoring limits risk after drawdown
- daily shift cap is enforced

**Step 3: Write tests for behavior control**

Cover:
- cooldown remains active on the next decision cycle
- degraded forced cash updates controller state
- deadband avoids one-day reversals

**Step 4: Write runtime integration tests**

Cover:
- `src.main --engine v11 --json --no-save` emits a v11 payload
- `src.backtest --mode v11` runs a v11 audit path and returns success

**Step 5: Run the new tests and verify they fail for the right reasons**

Run:
- `pytest tests/unit/engine/v11/test_position_sizer.py -q`
- `pytest tests/unit/engine/v11/test_behavioral_guard.py -q`
- `pytest tests/unit/test_main_v11.py -q`
- `pytest tests/unit/test_backtest_v11.py -q`

### Task 3: Rebuild The V11 Core

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/adaptive_memory.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/feature_library.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/calibration_service.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/bayesian_inference.py`
- Create: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/position_sizer.py`

**Step 1: Fix feature-library indexing and rolling-rank safety**

Ensure:
- duplicate index values cannot break weighted ranks
- standardized features are recomputed from raw library columns

**Step 2: Fit a stable inference packet**

Ensure:
- feature order is explicit
- PCA transform only runs after fit
- bad rows are dropped deterministically
- numeric instability is clipped and surfaced

**Step 3: Implement entropy-aware sizing**

Add:
- regime caps
- expected-beta calculation from posterior
- entropy normalization
- dollar-anchored allocation outputs
- daily delta cap

### Task 4: Replace The State-Machine-Primary Execution Layer

**Files:**
- Create: `/Users/weizhang/w/qqq-monitor/src/engine/v11/signal/behavioral_guard.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/signal/data_degradation_pipeline.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/conductor.py`

**Step 1: Move cooldown accounting to the start of the decision cycle**

Ensure next-day lock semantics actually hold.

**Step 2: Make degradation auditable and stateful**

Ensure:
- anomaly flags reduce quality
- proxy usage is explicit
- forced downgrades produce real actions

**Step 3: Return a unified v11 runtime payload**

Include:
- posteriors
- entropy
- target beta
- target allocation
- execution action
- quality audit

### Task 5: Align Main And Backtest Entrypoints

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/src/main.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/backtest.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/collector/vix.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/output/cli.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/models/__init__.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/store/db.py`

**Step 1: Add `--engine v11` to runtime**

Build a live v11 input row from:
- price history
- VIX / VIX3M
- breadth
- credit spread
- liquidity

**Step 2: Add `--mode v11` to backtest**

Implement a deterministic audit path using the v11 feature library that reports:
- walk-forward probabilistic metrics
- 2020 acceptance milestones
- execution stability metrics

**Step 3: Extend CLI/JSON serialization**

Ensure v11 results print and serialize without breaking existing v10 flows.

### Task 6: Align Documentation And Verification

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/README.md`
- Modify: `/Users/weizhang/w/qqq-monitor/README-CN.md`
- Modify: `/Users/weizhang/w/qqq-monitor/docs/roadmap/v11_production_sop.md`
- Modify: `/Users/weizhang/w/qqq-monitor/docs/roadmap/v11_roadmap.md`

**Step 1: Update runtime and backtest usage docs**

Document:
- `python -m src.main --engine v11`
- `python -m src.backtest --mode v11`

**Step 2: Mark old POC claims as research-only where needed**

Explicitly separate:
- archived experimental claims
- production-accepted architecture

**Step 3: Run the full verification set**

Run:
- `pytest tests/unit/engine/v11 -q`
- `pytest tests/integration/engine/v11/test_v11_workflow.py -q`
- `pytest tests/unit/test_main_v11.py -q`
- `pytest tests/unit/test_backtest_v11.py -q`
- `python -m src.backtest --mode v11`

