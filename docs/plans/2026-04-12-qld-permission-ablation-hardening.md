# QLD Permission Ablation Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden QLD buy/sell authorization so the live and backtest paths share one auditable decision chain, add PIT-safe fundamental override inputs, remove breadth/concentration double-counting, and prove via ablation that each addition does not regress the current baseline.

**Architecture:** Keep `raw_target_beta` and posterior generation unchanged. Add a separate execution-permission layer that governs whether `QLD` is legally available, what can relax or revoke that permission, and how tactical `resonance` signals bind to execution. Make every new rule switchable so acceptance and ablation can replay the exact same history with one rule toggled at a time.

**Tech Stack:** Python, pandas, pytest, existing v11/v13 execution pipeline, existing baseline tractor/sidecar diagnostics, GitHub PR workflow.

---

### Task 1: Freeze the desired QLD permission contract with failing tests

**Files:**
- Modify: `tests/unit/engine/v11/test_behavioral_guard.py`
- Modify: `tests/unit/test_resonance_detector.py`
- Modify: `tests/unit/engine/v11/test_conductor.py`
- Create: `tests/unit/engine/v11/test_qld_permission.py`

**Step 1: Write failing tests for binding tactical risk**
- Assert `SELL_QLD` can force `QLD -> QQQ` in the execution path, not just UI metadata.
- Assert `BUY_QLD` only relaxes entry rules when QLD permission is already granted.

**Step 2: Write failing tests for sub-1.0x QLD gating**
- Assert `target_beta < 1.0` may not map to `QLD` unless all hard conditions hold:
- `sidecar_valid == True`
- `tractor_prob < calm_threshold`
- `sidecar_prob < calm_threshold`
- `effective_entropy <= threshold`
- `fundamental_override_score >= threshold`

**Step 3: Write failing tests for live/backtest parity**
- Assert the canonical backtest path passes `baseline_result` into the same permission logic used in live mode.

**Step 4: Run targeted tests and confirm RED**

Run:
```bash
PYTHONPATH=. pytest tests/unit/engine/v11/test_qld_permission.py tests/unit/engine/v11/test_behavioral_guard.py tests/unit/test_resonance_detector.py tests/unit/engine/v11/test_conductor.py -q
```

### Task 2: Add PIT-safe fundamental override inputs and source quality handling

**Files:**
- Modify: `src/collector/macro_v3.py`
- Modify: `src/main.py`
- Create: `src/engine/v11/signal/fundamental_override.py`
- Create: `tests/unit/engine/v11/test_fundamental_override.py`
- Modify: `tests/unit/test_main_v11.py`

**Step 1: Write failing tests for the new fundamental override payload**
- Validate fail-closed behavior when revision data is missing or placeholder.
- Validate score only becomes actionable when breadth/diffusion inputs are observed and high quality.

**Step 2: Implement minimal collector/runtime plumbing**
- Replace placeholder-only handling with an explicit structured snapshot contract.
- Keep the feature out of posterior and `raw_target_beta`; use it only for execution permission.

**Step 3: Run targeted tests and confirm GREEN**

Run:
```bash
PYTHONPATH=. pytest tests/unit/engine/v11/test_fundamental_override.py tests/unit/test_main_v11.py -q
```

### Task 3: Eliminate breadth/concentration double-counting under degraded breadth sourcing

**Files:**
- Modify: `src/collector/breadth.py`
- Modify: `src/engine/v13/execution_overlay.py`
- Modify: `tests/unit/test_breadth.py`
- Modify: `tests/unit/engine/v13/test_execution_overlay.py`

**Step 1: Write failing tests**
- If `adv_dec_ratio` is derived from `QQQ/QQEW`, one of `breadth_stress` or `concentration_stress` must be neutralized.
- If true observed breadth is available, both channels remain independent.

**Step 2: Implement minimal source-aware collinearity guard**
- Preserve existing overlay behavior for observed breadth.
- Fail closed rather than inventing a second independent signal from the same source.

**Step 3: Run targeted tests**

Run:
```bash
PYTHONPATH=. pytest tests/unit/test_breadth.py tests/unit/engine/v13/test_execution_overlay.py -q
```

### Task 4: Insert QLD permission layer into live and backtest execution

**Files:**
- Create: `src/engine/v11/signal/qld_permission.py`
- Modify: `src/engine/v11/conductor.py`
- Modify: `src/backtest.py`
- Modify: `src/output/web_exporter.py`
- Modify: `tests/unit/engine/v11/test_conductor_overlay_integration.py`
- Modify: `tests/unit/test_backtest_v13_overlay.py`

**Step 1: Write failing tests**
- Assert `raw_target_beta` remains bit-identical.
- Assert `target_beta` remains continuous, but `target_bucket` and `target_allocation` obey permission state.
- Assert backtest execution traces export the permission diagnostics needed for acceptance and ablation.

**Step 2: Implement minimal permission state**
- Compute permission after overlay/topology/baseline diagnostics are available and before `BehavioralGuard`.
- Bind `SELL_QLD` as revocation.
- Bind `BUY_QLD` as a relaxer, never a unilateral override.
- Store full permission reasons and source quality diagnostics in runtime output.

**Step 3: Run targeted tests**

Run:
```bash
PYTHONPATH=. pytest tests/unit/engine/v11/test_qld_permission.py tests/unit/engine/v11/test_conductor_overlay_integration.py tests/unit/test_backtest_v13_overlay.py -q
```

### Task 5: Add ablation and acceptance verification for 2022 defense and 2023 re-risking

**Files:**
- Create: `scripts/run_qld_permission_ablation.py`
- Create: `tests/unit/test_qld_permission_ablation.py`
- Modify: `docs/research/2026-04-08-regime-process-panorama.md`
- Create: `docs/versions/v14/2026-04-12-qld-permission-ablation.md`

**Step 1: Write failing tests for ablation report shape**
- One row for baseline plus one row per approved change.
- Metrics must include:
- `2022_mean_target_beta`
- `2022_share_qld_days`
- `2023_q1_mean_target_beta`
- `2023_q1_share_qld_days`
- `2023_q1_first_qld_date`
- `process_alignment`
- `raw_beta_drift_vs_baseline`

**Step 2: Implement replay script**
- Replay canonical history with feature flags:
- `bind_resonance`
- `fundamental_override`
- `breadth_collinearity_guard`
- `sub1x_qld_hard_gate`
- `baseline_parity`
- Report non-regression against current baseline and flag any raw-beta drift as hard fail.

**Step 3: Run targeted tests**

Run:
```bash
PYTHONPATH=. pytest tests/unit/test_qld_permission_ablation.py -q
```

### Task 6: Align docs, run production baseline checks, and prepare PR

**Files:**
- Modify: `docs/versions/v13/V13_EXECUTION_OVERLAY_SRD.md`
- Modify: `docs/versions/v14/V14_5_RESONANCE_DETECTOR_SPEC.md`
- Modify: `docs/versions/v11/v11_bayesian_production_baseline_2026-04-05.md`
- Modify any architecture docs touched by the final implementation

**Step 1: Update documentation**
- Document that `raw_target_beta` is unchanged.
- Document the new QLD permission layer and its fail-closed data contract.
- Document ablation results and why each rule is retained.

**Step 2: Run verification**

Run:
```bash
PYTHONPATH=. pytest tests/unit/engine/v11/test_qld_permission.py tests/unit/engine/v11/test_fundamental_override.py tests/unit/test_qld_permission_ablation.py tests/unit/engine/v13/test_execution_overlay.py tests/unit/test_breadth.py tests/unit/engine/v11/test_conductor_overlay_integration.py tests/unit/test_backtest_v13_overlay.py tests/unit/test_resonance_detector.py tests/unit/engine/v11/test_behavioral_guard.py -q
PYTHONPATH=. python scripts/run_qld_permission_ablation.py
ruff check src tests scripts
PYTHONPATH=. pytest -q
```

**Step 3: Prepare branch and PR**
- Create a feature branch.
- Commit with coherent messages.
- Push to GitHub.
- Create a new PR with ablation summary, acceptance summary, and residual risks.
