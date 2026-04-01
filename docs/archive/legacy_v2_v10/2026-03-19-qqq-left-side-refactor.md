# Long-Term QQQ Left-Side Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild `qqq-monitor` from a high-conviction buy-signal monitor into a deterministic long-term QQQ accumulation and position-sizing system.

**Architecture:** Split the system into three horizons. Structural regime decides whether long-duration risk should be accumulated, tactical stress decides whether to accelerate or slow buying, and microstructure only fine-tunes timing instead of vetoing long-term decisions. Every live feature must be deterministic, tagged with source quality, and allowed to be missing without inventing data.

**Tech Stack:** Python 3.12, pandas, yfinance, FRED, SQLite, pytest

---

## Recommended Product Shape

Replace the current output states with allocation states:

- `PAUSE_CHASING`: Market extended, do not add.
- `BASE_DCA`: Continue baseline recurring buy.
- `SLOW_ACCUMULATE`: Modest left-side add.
- `FAST_ACCUMULATE`: Strong left-side add, but still tranche-based.
- `RISK_CONTAINMENT`: Macro stress too high for aggressive adds; preserve optionality.

Replace “strong buy” language with sizing guidance:

- `daily_tranche_pct`
- `max_total_add_pct`
- `cooldown_days`
- `required_persistence_days`
- `confidence`

## Operating Principles

- No random or simulated values in the live path.
- No feature may silently masquerade as real data.
- Slow-moving macro and valuation inputs must dominate short-dated options structure.
- The system must help the investor stay calm, not feel clever.
- Backtests must use only information plausibly known on that date.

### Task 1: Introduce Deterministic Domain Models

**Files:**
- Modify: `src/models/__init__.py`
- Modify: `src/output/report.py`
- Test: `tests/unit/test_aggregator.py`

**Step 1: Write failing tests for new output model**

Add tests asserting the system can represent:

```python
assert result.allocation_state == AllocationState.BASE_DCA
assert result.confidence in {"high", "medium", "low"}
assert result.daily_tranche_pct >= 0
```

**Step 2: Run targeted test**

Run: `python3 -m pytest tests/unit/test_aggregator.py -q`

Expected: FAIL because `AllocationState` and new fields do not exist.

**Step 3: Add minimal domain types**

Add:

```python
class AllocationState(str, Enum):
    PAUSE_CHASING = "PAUSE_CHASING"
    BASE_DCA = "BASE_DCA"
    SLOW_ACCUMULATE = "SLOW_ACCUMULATE"
    FAST_ACCUMULATE = "FAST_ACCUMULATE"
    RISK_CONTAINMENT = "RISK_CONTAINMENT"
```

Extend the final result model with:

```python
allocation_state: AllocationState
daily_tranche_pct: float
max_total_add_pct: float
cooldown_days: int
required_persistence_days: int
confidence: str
data_quality: dict
```

**Step 4: Update JSON serialization expectations**

Make sure `src/output/report.py` and DB serialization can carry the new fields without breaking existing consumers.

**Step 5: Re-run tests**

Run: `python3 -m pytest tests/unit/test_aggregator.py -q`

Expected: PASS for the new model expectations.

### Task 2: Remove Random and Synthetic Data from the Live Path

**Files:**
- Modify: `src/collector/macro_v3.py`
- Modify: `src/main.py`
- Test: `tests/unit/test_macro_v3.py`
- Test: `tests/integration/test_pipeline.py`

**Step 1: Write failing tests for deterministic collector behavior**

Add tests that verify:

```python
assert fetch_fcf_yield() is None
assert fetch_earnings_revisions_breadth() is None
```

when no trusted source is configured.

**Step 2: Run targeted tests**

Run: `python3 -m pytest tests/unit/test_macro_v3.py -q`

Expected: FAIL because collectors currently fabricate values.

**Step 3: Replace random fallbacks with explicit unavailability**

Change collectors so they either:

- return trusted fetched values, or
- return `None` and log that the feature is unavailable.

Do not generate mock values in production code.

**Step 4: Propagate missingness through `main.py`**

The live pipeline must:

- preserve `None`
- add feature availability into `data_quality`
- avoid awarding valuation or revision bonuses when inputs are unavailable

**Step 5: Re-run tests**

Run: `python3 -m pytest tests/unit/test_macro_v3.py tests/integration/test_pipeline.py -q`

Expected: PASS with deterministic collector behavior.

### Task 3: Add a Feature-Quality Layer

**Files:**
- Create: `src/engine/data_quality.py`
- Modify: `src/main.py`
- Modify: `src/models/__init__.py`
- Test: `tests/unit/test_data_quality.py`

**Step 1: Write failing tests**

Add tests for:

```python
quality = assess_feature_quality(
    credit_spread=450.0,
    forward_pe=None,
    short_vol_ratio=None,
)
assert quality["credit_spread"]["usable"] is True
assert quality["forward_pe"]["usable"] is False
```

**Step 2: Implement minimal quality assessor**

Create a small engine that returns per-feature metadata:

```python
{
    "value": 450.0,
    "source": "fred",
    "usable": True,
    "stale_days": 1,
    "category": "slow"
}
```

**Step 3: Attach feature quality to the final result**

The user should see which parts of the recommendation are based on complete data versus degraded mode.

**Step 4: Re-run tests**

Run: `python3 -m pytest tests/unit/test_data_quality.py -q`

Expected: PASS.

### Task 4: Replace Tier-0 Cliff Logic with a Structural Regime Ladder

**Files:**
- Modify: `src/engine/tier0_macro.py`
- Create: `tests/unit/test_structural_regime.py`

**Step 1: Write failing tests for a five-level regime ladder**

Add tests for:

```python
assert assess_structural_regime(credit_spread=320, erp=1.5) == "RICH_TIGHTENING"
assert assess_structural_regime(credit_spread=420, erp=3.5) == "TRANSITION_STRESS"
assert assess_structural_regime(credit_spread=560, erp=5.0) == "CRISIS"
```

**Step 2: Implement regime ladder**

Replace binary veto logic with:

- `EUPHORIC`
- `RICH_TIGHTENING`
- `NEUTRAL`
- `TRANSITION_STRESS`
- `CRISIS`

Only `CRISIS` should block aggressive adds outright. The middle regimes should slow sizing, not force silence.

**Step 3: Re-run tests**

Run: `python3 -m pytest tests/unit/test_structural_regime.py tests/unit/test_tier0_macro.py -q`

Expected: PASS.

### Task 5: Rebuild Tactical Engine Around Stress, Capitulation, and Persistence

**Files:**
- Modify: `src/engine/tier1.py`
- Modify: `src/engine/divergence.py`
- Test: `tests/unit/test_tier1.py`
- Test: `tests/unit/test_divergence.py`

**Step 1: Write failing tests for three tactical buckets**

Add tests for:

- `stress_score`
- `capitulation_score`
- `persistence_score`

Example:

```python
result = calculate_tactical_state(data)
assert result.stress_score >= 0
assert result.capitulation_score >= 0
assert result.persistence_score >= 0
```

**Step 2: Remove mixed-breadth comparisons**

Use one consistent breadth definition in both history and current state. Do not compare `pct_above_50d` against stored `adv_dec_ratio`.

**Step 3: Gate “fast accumulate” on persistence**

A single scary day must not produce the most aggressive action. Require at least one of:

- stress persisting for `n` sessions
- drawdown persistence
- macro regime improvement from worse to less bad

**Step 4: Re-run tests**

Run: `python3 -m pytest tests/unit/test_tier1.py tests/unit/test_divergence.py -q`

Expected: PASS.

### Task 6: Demote Options Microstructure to an Optional Overlay

**Files:**
- Modify: `src/engine/tier2.py`
- Modify: `src/engine/aggregator.py`
- Test: `tests/unit/test_tier2.py`
- Test: `tests/unit/test_aggregator.py`

**Step 1: Write failing tests for overlay-only behavior**

Add tests asserting:

```python
assert options_overlay.can_reduce_tranche is True
assert options_overlay.cannot_upgrade_structural_state is True
```

**Step 2: Refactor Tier-2 semantics**

Tier-2 may:

- delay one tranche
- reduce daily add size
- lower confidence

Tier-2 may not:

- create `FAST_ACCUMULATE` by itself
- override a favorable slow-horizon regime into permanent inaction

**Step 3: Re-run tests**

Run: `python3 -m pytest tests/unit/test_tier2.py tests/unit/test_aggregator.py -q`

Expected: PASS.

### Task 7: Replace Signal Aggregation with Allocation Policy

**Files:**
- Modify: `src/engine/aggregator.py`
- Create: `tests/unit/test_allocation_policy.py`

**Step 1: Write failing allocation-policy tests**

Example cases:

```python
assert recommend_allocation(structural="NEUTRAL", tactical="CALM") == AllocationState.BASE_DCA
assert recommend_allocation(structural="TRANSITION_STRESS", tactical="CAPITULATION") == AllocationState.SLOW_ACCUMULATE
assert recommend_allocation(structural="CRISIS", tactical="PANIC") == AllocationState.RISK_CONTAINMENT
```

**Step 2: Implement sizing rules**

Recommended defaults:

- `PAUSE_CHASING`: `daily_tranche_pct=0.0`
- `BASE_DCA`: `daily_tranche_pct=0.25`
- `SLOW_ACCUMULATE`: `daily_tranche_pct=0.50`
- `FAST_ACCUMULATE`: `daily_tranche_pct=0.75`
- `RISK_CONTAINMENT`: `daily_tranche_pct=0.10`

All tranche sizes are relative to the planned multi-week add budget, not total account NAV.

**Step 3: Add psychology guardrails**

Include:

- cooldown after any `FAST_ACCUMULATE`
- max cumulative add over rolling 20 sessions
- no “all-in” language in explanations

**Step 4: Re-run tests**

Run: `python3 -m pytest tests/unit/test_allocation_policy.py tests/unit/test_aggregator.py -q`

Expected: PASS.

### Task 8: Redesign Backtest Methodology

**Files:**
- Modify: `src/backtest.py`
- Create: `docs/backtests/methodology.md`
- Test: `tests/unit/test_backtest_methodology.py`

**Step 1: Write failing methodology tests**

Add checks that the backtest:

- does not use synthetic fear/greed
- does not use fabricated short-volume
- reports forward returns and drawdown pain

**Step 2: Replace “capture rate” headline metrics**

The core report should include:

- forward return at `T+5`, `T+20`, `T+60`
- max adverse excursion after add
- average cost improvement vs baseline DCA
- fraction of capital deployed before final low

**Step 3: Model tranche deployment**

Backtest the system as an allocator, not a labeler:

- baseline weekly DCA always runs
- tactical states speed up or slow down adds
- compare to pure DCA and lump-sum alternatives

**Step 4: Re-run tests**

Run: `python3 -m pytest tests/unit/test_backtest_methodology.py -q`

Expected: PASS.

### Task 9: Update CLI, JSON, and Documentation

**Files:**
- Modify: `src/main.py`
- Modify: `src/output/cli.py`
- Modify: `src/output/report.py`
- Modify: `README.md`
- Modify: `docs/PRD.md`

**Step 1: Write failing snapshot-style tests**

Add tests that assert CLI and JSON now show:

- allocation state
- tranche size
- confidence
- data-quality summary

**Step 2: Update output wording**

Replace:

- “强烈买入”
- “百年一遇”
- “分批加仓区间”

with calmer operational wording:

- “维持基础定投”
- “允许提高加仓速度”
- “仅小幅试探”

**Step 3: Re-run tests**

Run: `python3 -m pytest tests/integration/test_pipeline.py -q`

Expected: PASS with new output semantics.

### Task 10: Final Validation

**Files:**
- Test: `tests/unit/`
- Test: `tests/integration/`
- Verify: `src/backtest.py`

**Step 1: Run full test suite**

Run: `python3 -m pytest -q`

Expected: PASS.

**Step 2: Run static compilation**

Run: `python3 -m compileall src tests`

Expected: PASS.

**Step 3: Run backtest**

Run: `python3 -m src.backtest`

Expected: completes without synthetic live-path assumptions and emits allocation metrics.

**Step 4: Commit**

```bash
git add src tests docs README.md
git commit -m "refactor: convert qqq monitor into long-term allocation engine"
```

## Execution Notes

- Do not preserve backward-compatible semantics for `STRONG_BUY` if that keeps the wrong product behavior alive.
- If historical data for a feature is unavailable, omit it from the backtest rather than synthesize it.
- Prefer fewer trustworthy features over many theatrical ones.
- If a field cannot be trusted in live trading, it should not influence sizing.
- Progress:
- Task 1 completed on 2026-03-19 with transitional allocation fields and serialization coverage.
