# v13 Execution Overlay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the v13 execution overlay architecture end-to-end, including audit artifact, engine logic, runtime integration, presentation adaptation, tests, backtests, and release validation.

**Architecture:** v13 preserves the v12.1 probabilistic core and introduces a downstream execution overlay that conditions beta and incremental deployment pace using monotone, PIT-safe market-internal inputs. The implementation must keep posterior outputs and `raw_target_beta` invariant, version the runtime snapshot, and adapt web and Discord outputs without changing the page style.

**Tech Stack:** Python 3.12, pytest, Docker, static `index.html`, Discord webhook output, JSON audit artifacts

---

### Task 1: Add v13 audit artifact scaffold

**Files:**
- Create: `src/engine/v13/resources/execution_overlay_audit.json`
- Test: `tests/unit/engine/v13/test_execution_overlay.py`

**Step 1: Write the failing test**

- assert the v13 overlay engine can load a versioned audit artifact
- assert required keys exist for beta and pace multipliers

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/engine/v13/test_execution_overlay.py -k audit -q`

**Step 3: Write minimal implementation**

- create the JSON artifact with version, weights, floors, ceilings, and source policy

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/engine/v13/test_execution_overlay.py -k audit -q`

---

### Task 2: Add execution overlay datamodel and engine

**Files:**
- Create: `src/engine/v13/__init__.py`
- Create: `src/engine/v13/execution_overlay.py`
- Test: `tests/unit/engine/v13/test_execution_overlay.py`

**Step 1: Write failing tests**

- neutral inputs return `1.0` multipliers
- worsening negative input does not increase beta
- rejected placeholder inputs are ignored

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/engine/v13/test_execution_overlay.py -q`

**Step 3: Write minimal implementation**

- add overlay input dataclass
- add monotone rank-based feature derivation
- add bounded multiplier computation

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/engine/v13/test_execution_overlay.py -q`

---

### Task 3: Integrate overlay into conductor runtime path

**Files:**
- Modify: `src/engine/v11/conductor.py`
- Test: `tests/unit/engine/v11/test_conductor_overlay_integration.py`

**Step 1: Write failing tests**

- `raw_target_beta` remains unchanged
- runtime snapshot version bumps
- overlay block appears in runtime outputs and snapshots

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/engine/v11/test_conductor_overlay_integration.py -q`

**Step 3: Write minimal implementation**

- compute `protected_beta`
- run overlay after entropy haircut
- feed penalized beta into inertial mapper
- apply pace multiplier only to deployment readiness and deployment decision metadata
- export overlay diagnostics

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/engine/v11/test_conductor_overlay_integration.py -q`

---

### Task 4: Extend main result mapping and output contracts

**Files:**
- Modify: `src/main.py`
- Modify: `src/output/web_exporter.py`
- Modify: `src/output/discord_notifier.py`
- Test: `tests/unit/test_main_v11.py`
- Test: `tests/unit/test_web_exporter.py`
- Test: `tests/unit/test_discord_notifier.py`

**Step 1: Write failing tests**

- result metadata carries overlay fields
- `status.json` carries overlay semantic surfaces
- Discord embed includes compact overlay audit lines

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_main_v11.py tests/unit/test_web_exporter.py tests/unit/test_discord_notifier.py -q`

**Step 3: Write minimal implementation**

- extend `SignalResult.metadata`
- export overlay fields in `status.json`
- add compact Discord overlay lines without changing primary narrative

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_main_v11.py tests/unit/test_web_exporter.py tests/unit/test_discord_notifier.py -q`

---

### Task 5: Adapt `index.html` without visual redesign

**Files:**
- Modify: `src/web/public/index.html`
- Test: `tests/integration/test_web_alignment.py`

**Step 1: Write failing test**

- assert `index.html` references all required v13 web-export paths

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_web_alignment.py -q`

**Step 3: Write minimal implementation**

- render compact overlay audit strip
- add overlay detail sections inside existing insights panel
- preserve hero metrics and page shell

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_web_alignment.py -q`

---

### Task 6: Add PIT and source governance tests

**Files:**
- Create: `tests/unit/data/test_overlay_pit_contract.py`
- Modify: `src/collector/breadth.py` only if required for safe contract exposure

**Step 1: Write failing tests**

- weekly sources require release-lag handling
- placeholder and repurposed proxy fields are rejected
- provenance and quality metadata are mandatory

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/data/test_overlay_pit_contract.py -q`

**Step 3: Write minimal implementation**

- add source-policy helpers or static validation tables as needed

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/data/test_overlay_pit_contract.py -q`

---

### Task 7: Add backtest non-regression and frozen acceptance tests

**Files:**
- Modify: `src/backtest.py`
- Create: `tests/unit/test_backtest_v13_overlay.py`

**Step 1: Write failing tests**

- acceptance mode fails closed on missing frozen artifacts
- no live download path in acceptance mode
- `raw_target_beta` remains bit-identical when overlay is neutral

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_backtest_v13_overlay.py -q`

**Step 3: Write minimal implementation**

- add pinned acceptance configuration
- gate live downloads behind non-acceptance path
- add overlay-disabled and neutral-overlay backtest modes

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_backtest_v13_overlay.py -q`

---

### Task 8: Run full unit and integration test suite in Docker

**Files:**
- None

**Step 1: Run tests**

Run: `docker run --rm -v "$PWD":/app -w /app python:3.12-slim bash -c "pip install -r requirements.txt >/tmp/pip.log && PYTHONPATH=. pytest tests/unit tests/integration -q"`

**Step 2: Fix regressions**

- iterate until green

---

### Task 9: Run acceptance backtest and inspect regression

**Files:**
- None

**Step 1: Run backtest**

Run: `docker run --rm -v "$PWD":/app -w /app qqq-monitor:py313 python -m src.backtest --evaluation-start 2018-01-01`

**Step 2: Review outputs**

- inspect invariance, left-tail behavior, holdout stability, and turnover
- if regression appears, fix architecture or parameters without introducing overfit

---

### Task 10: Run cold start, warm start, and release workflow

**Files:**
- None

**Step 1: Run T+0 cold start**

- execute runtime with clean prior state and inspect output artifacts

**Step 2: Run immediate warm start**

- re-execute runtime with persisted state and compare behavior

**Step 3: Create PR and monitor checks**

- create branch commit series
- open PR
- monitor checks until green

