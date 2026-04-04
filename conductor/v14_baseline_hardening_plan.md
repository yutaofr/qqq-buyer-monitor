# Implementation Plan: Hardening v14 Baseline PIT & Backtest Integrity (V3)

## Goal
Produce a reproducible, PIT-safe, walk-forward OOS baseline backtest with unambiguous sidecar semantics and report parity.

## Scope
- `src/engine/baseline/execution.py`
- `src/engine/baseline/validation.py`
- `scripts/baseline_backtest.py`
- `tests/baseline/test_oos_metrics.py`
- `docs/research/v14_full_panorama_audit.md`

## Proposed Solution

### 1. Harden OOS execution
Modify `src/engine/baseline/execution.py` to:
- Refine `calculate_baseline_oos_series` to track per-date `^VXN` availability more strictly.
- Ensure `sidecar_valid` is only true if `^VXN` was available for both training and prediction for that date.
- Return `sidecar_prob` as `NaN` if invalid for that date, rather than `0.0` or a ffill.

### 2. Fix AC-2 and add Leakage Detection
Modify `src/engine/baseline/validation.py` to:
- Update `run_ac2_label_permutation_test`:
    - Ensure it uses a true walk-forward across the whole range for each shuffle.
- Add `run_ac2_leakage_detection`:
    - Create a synthetic dataset with a time-dependent signal (e.g., trend).
    - Implement a "leaky" evaluator that uses future data in training (e.g., non-PIT-safe split).
    - Verify that PIT-safe evaluator fails (AUC ~0.5) while leaky one succeeds (AUC >> 0.5) on synthetic data.

### 3. Canonicalize the backtest script
Modify `scripts/baseline_backtest.py` to:
- Remove any remnants of 80/20 split logic.
- Ensure it consumes only the walk-forward OOS series from `calculate_baseline_oos_series`.
- Update the summary table to explicitly show:
    - OOS date range and sample count.
    - Sidecar status: `FULL` or `DEGRADED/INCONCLUSIVE`.
    - If `DEGRADED`, do not report AUC/Brier for sidecar.
- Add AC-2 leakage detection results to the output.

### 4. Strengthen tests
Modify `tests/baseline/test_oos_metrics.py` to:
- Add a test case for `run_ac2_leakage_detection`.
- Verify that `calculate_baseline_oos_series` correctly marks `sidecar_valid` based on `^VXN` availability.

### 5. Regenerate the audit
- Run the updated `scripts/baseline_backtest.py`.
- Update `docs/research/v14_full_panorama_audit.md` with the new results and formatting.

## Implementation Steps

### Phase 1: Engine Hardening
1. Modify `src/engine/baseline/execution.py`'s `calculate_baseline_oos_series`.
2. Update `src/engine/baseline/validation.py` with AC-2 improvements and leakage detection.

### Phase 2: Script and Test Updates
1. Update `scripts/baseline_backtest.py` for canonical reporting.
2. Update `tests/baseline/test_oos_metrics.py` with new test cases.

### Phase 3: Validation and Reporting
1. Run `pytest tests/baseline/`.
2. Run `python scripts/baseline_backtest.py`.
3. Update `docs/research/v14_full_panorama_audit.md`.

## Verification
- `pytest tests/baseline/` must pass.
- `scripts/baseline_backtest.py` must run without errors and produce a clear, unambiguous summary.
- The regenerated audit report must match the script output exactly.
