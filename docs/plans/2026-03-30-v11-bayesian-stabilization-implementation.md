# V11 Bayesian Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize the v11 probabilistic system by making the prior state deterministic, making posterior inference explicitly Bayesian, and persisting posterior evidence back into a reusable prior knowledge base.

**Architecture:** Keep the existing v11 runtime surface, but replace the implicit/equal prior path with a deterministic prior knowledge base bootstrapped from labeled regime history. The conductor will use classifier likelihoods plus runtime priors to compute posteriors, then persist posterior mass back into the prior library so each run updates the next run's prior without introducing non-causal randomness.

**Tech Stack:** Python 3.12+, pandas, numpy, scikit-learn, pytest, JSON resources/state files.

---

### Task 1: Lock deterministic feature seeding

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_probability_seeder.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/probability_seeder.py`

**Step 1: Write a failing determinism test**

Assert repeated calls over the same input yield identical features.

**Step 2: Run the focused seeder tests and verify failure**

Run: `pytest tests/unit/engine/v11/test_probability_seeder.py -q`

**Step 3: Remove random feature perturbations and keep causal scaling**

Ensure feature generation is deterministic and look-ahead safe.

### Task 2: Add a stable prior knowledge base

**Files:**
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_prior_knowledge.py`
- Create: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/prior_knowledge.py`

**Step 1: Write failing bootstrap and persistence tests**

Cover:
- base priors are bootstrapped deterministically from regime history
- posterior updates persist and change future priors
- runtime priors stay normalized and bounded

**Step 2: Implement prior library**

Add:
- deterministic bootstrap from labeled regimes
- posterior-count updates
- optional transition-aware prior blending
- JSON persistence for runtime reuse

### Task 3: Rewire conductor onto explicit Bayesian updates

**Files:**
- Modify: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_probabilistic_core.py`
- Create: `/Users/weizhang/w/qqq-monitor/tests/unit/engine/v11/test_conductor.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/core/bayesian_inference.py`
- Modify: `/Users/weizhang/w/qqq-monitor/src/engine/v11/conductor.py`

**Step 1: Write failing tests for prior reweighting and posterior persistence**

Cover:
- runtime priors reweight classifier posteriors deterministically
- conductor writes posterior evidence back to the prior store

**Step 2: Implement minimal production changes**

Ensure:
- classifier likelihoods are separated from runtime priors
- conductor no longer hardcodes equal priors
- posterior output remains normalized and auditable

### Task 4: Verify with focused v11 tests

**Files:**
- Modify only if verification reveals gaps

**Step 1: Run focused unit and integration tests**

Run:
- `pytest tests/unit/engine/v11/test_probability_seeder.py -q`
- `pytest tests/unit/engine/v11/test_prior_knowledge.py -q`
- `pytest tests/unit/engine/v11/test_probabilistic_core.py -q`
- `pytest tests/unit/engine/v11/test_conductor.py -q`
- `pytest tests/integration/engine/v11/test_v11_workflow.py -q`

**Step 2: Run the v11 audit backtest**

Run: `python -m src.backtest --mode v11`

**Step 3: Record remaining factor/backtest risks**

Document which factors still need out-of-sample calibration and which entropy/penalty settings remain heuristic.
