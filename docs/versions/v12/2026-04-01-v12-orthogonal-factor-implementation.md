# V12 Orthogonal Factor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the locked v12 orthogonal-factor architecture end-to-end across data contracts, PIT dataset construction, Bayesian seeding, runtime inference, and audit/backtest outputs without regressing the v11 production guarantees.

**Architecture:** v12 keeps the existing GaussianNB + recursive prior + entropy haircut core, but replaces the v11 feature contract with a 10-factor orthogonal macro observation vector. Delivery is staged in three gates: PIT-safe data foundation, seeder/model integration, then full audit evidence and regression verification.

**Tech Stack:** Python 3.12, pandas, scikit-learn GaussianNB, Docker-based pytest/backtest execution, checked-in CSV/JSON audit artifacts.

---

### Task 1: Freeze the v12 contract in tests

**Files:**
- Modify: `tests/unit/test_research_data_contracts.py`
- Create: `tests/unit/data/test_pit_compliance.py`
- Modify: `tests/unit/engine/v11/test_probability_seeder.py`

**Step 1: Write failing tests for the canonical v12 schema**

Add tests asserting the required v12 columns exist, old deprecated columns are tolerated but not required for inference, and new source columns are mandatory.

**Step 2: Run targeted tests to verify RED**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/test_research_data_contracts.py tests/unit/engine/v11/test_probability_seeder.py tests/unit/data/test_pit_compliance.py -q
```

Expected: failures for missing v12 schema, missing PIT helpers, and legacy seeder assumptions.

**Step 3: Write minimal contract-supporting code**

Update `src/research/data_contracts.py` and `src/engine/v11/probability_seeder.py` only enough to satisfy the first contract assertions.

**Step 4: Re-run the same tests**

Expected: green for the implemented contract scope; remaining failures point to unimplemented PIT builder behavior.

### Task 2: Implement PIT-safe v12 historical dataset construction

**Files:**
- Create: `src/collector/global_macro.py`
- Create: `scripts/v12_historical_data_builder.py`
- Modify: `src/research/historical_macro_builder.py`
- Modify: `tests/unit/test_historical_macro_builder.py`
- Modify: `tests/unit/data/test_pit_compliance.py`

**Step 1: Write failing tests for effective-date lag behavior**

Cover:
- Tier 1 T+1 visibility
- `core_capex_mm` monthly value visible only after `observation_date + 30 BDay`
- `erp_ttm_pct` visible only after `month_end + 30 BDay`
- copper/gold adjusted ratio and USDJPY propagation

**Step 2: Run targeted tests to verify RED**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/test_historical_macro_builder.py tests/unit/data/test_pit_compliance.py -q
```

**Step 3: Implement builder and collector helpers**

Build pure functions first:
- publication-lag helpers
- series alignment helpers
- Shiller ERP derivation
- v12 dataset build/write entrypoint

**Step 4: Re-run builder/PIT tests**

Expected: all PIT assertions green.

### Task 3: Replace v11 seeder with the v12 10-factor observation vector

**Files:**
- Modify: `src/engine/v11/probability_seeder.py`
- Modify: `tests/unit/engine/v11/test_probability_seeder.py`

**Step 1: Write failing tests for per-factor formulas**

Cover:
- 10 feature names in order
- global clip `[-8, 8]`
- expanding vs rolling windows by factor
- `move_21d` orthogonalization diagnostics
- `yield_absolute` removal

**Step 2: Run the seeder tests to verify RED**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/engine/v11/test_probability_seeder.py -q
```

**Step 3: Implement minimal seeder changes**

Use a single code path for live and backtest.

**Step 4: Re-run seeder tests**

Expected: seeder tests green and contract hash stable.

### Task 4: Upgrade runtime and persistence plumbing to the v12 schema

**Files:**
- Modify: `src/engine/v11/conductor.py`
- Modify: `src/main.py`
- Modify: `src/collector/historical_macro_seeder.py`
- Modify: `tests/unit/engine/v11/test_conductor.py`
- Modify: `tests/unit/test_main_v11.py`
- Modify: `tests/integration/engine/v11/test_v11_workflow.py`

**Step 1: Write failing tests for runtime provenance and v12 live rows**

Cover:
- `_build_v12_live_macro_row()` emits all v12 value/source columns
- conductor quality audit reads new source fields
- feature values include orthogonalization diagnostics
- old `forward_pe` remains deprecated, not decision-bearing

**Step 2: Run runtime tests to verify RED**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/engine/v11/test_conductor.py tests/unit/test_main_v11.py tests/integration/engine/v11/test_v11_workflow.py -q
```

**Step 3: Implement minimal runtime wiring**

Update live row construction, quality audit mappings, runtime context columns, and output metadata.

**Step 4: Re-run runtime tests**

Expected: runtime and integration smoke tests green.

### Task 5: Extend audit/backtest outputs to satisfy Gate 2 and Gate 3 evidence

**Files:**
- Modify: `src/backtest.py`
- Modify: `tests/unit/test_backtest_v11.py`
- Create or modify: audit artifact writer helpers under `src/output/` if needed

**Step 1: Write failing tests for v12 audit outputs**

Cover:
- variance-ratio checks
- diagnostic slice export
- event/day recall metrics
- 2020 forensics log schema

**Step 2: Run audit tests to verify RED**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/test_backtest_v11.py -q
```

**Step 3: Implement audit/export logic**

Ensure artifacts land under `artifacts/v12_audit/` and remain deterministic.

**Step 4: Re-run audit tests**

Expected: unit audit tests green.

### Task 6: Regenerate locked artifacts and complete verification

**Files:**
- Modify: `src/engine/v11/resources/regime_audit.json`
- Modify: `data/macro_historical_dump.csv`
- Create: `artifacts/v12_audit/*`
- Update docs only if implementation behavior requires explicit alignment

**Step 1: Run the v12 historical builder**

Run the Docker command that writes the PIT-safe dataset and inspect 2020-03/2020-04 milestone rows.

**Step 2: Run the full unit/integration suite relevant to v12**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pytest tests/unit/test_research_data_contracts.py tests/unit/test_historical_macro_builder.py tests/unit/engine/v11/test_probability_seeder.py tests/unit/engine/v11/test_conductor.py tests/unit/test_main_v11.py tests/unit/test_backtest_v11.py tests/integration/engine/v11/test_v11_workflow.py -q
```

**Step 3: Run the full backtest audit**

Run:

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12-slim python -m src.backtest --evaluation-start 2018-01-01
```

**Step 4: Self-audit against architecture, production baseline, and non-regression**

Verify:
- Gate 1 / Gate 2 / Gate 3 evidence exists
- `regime_audit.json` matches new seeder hash
- v11 baseline behaviors that should remain unchanged still pass
- artifacts are written and readable

**Step 5: Final documentation of evidence**

Summarize what passed, what changed, and any residual risks with exact command evidence.
