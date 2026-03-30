# Plan: Parallelize and Optimize V11 Audit

## Objective
Optimize `run_v11_audit` in `src/backtest.py` to handle large evaluation windows (e.g., 2018-2026) without timing out, by using parallel processing and removing redundant calibrations.

## Key Changes

### 1. Bayesian Inference Optimization
- **Parallelization**: Use `ProcessPoolExecutor` to compute posterior probabilities for all days in the evaluation window. Inference for each day is independent.
- **Unified Calibration**: Calibrate the KDE models once at the start of the audit window instead of calling `calibrator.calibrate` in every daily iteration.

### 2. Execution Logic Refactoring
- **Separation of Concerns**: Decouple the `BayesianInferenceEngine` from the `BehavioralGuard` state machine.
- **Lightweight State Loop**: Only the `BehavioralGuard` (which manages hysteresis and settlement locks) remains sequential. Everything leading up to it (probabilities, entropy, raw sizing) is pre-calculated in parallel.

### 3. Implementation Steps in `src/backtest.py`
- Define a top-level helper function `_v11_inference_task` for parallel execution.
- Update `run_v11_audit` to:
    - Pre-calculate all dynamic features (MA200, etc.) for the library.
    - Calibrate once.
    - Dispatch inference tasks to a process pool.
    - Run a fast sequential loop for the state machine using the pre-calculated probabilities.
- Re-generate the visualization charts.

## Verification
- Run `python -m src.backtest --mode v11` and measure execution time.
- Verify that the output metrics (Accuracy, Brier Score) and charts remain consistent with the sequential version.
