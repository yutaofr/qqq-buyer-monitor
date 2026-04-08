# Recovery HMM Shadow Research Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a shadow-only orthogonalized asymmetric HMM research pipeline that specifically tests whether `RECOVERY` can be released from current suppression without modifying the live production execution chain.

**Architecture:** This work must live beside the current Bayesian production stack, not inside it. The new path is `raw factor domains -> rolling PCA orthogonalization -> asymmetric HMM state engine -> hardcoded shadow execution tensor -> OOS audit`, with outputs written to separate research artifacts for comparison against the current production trace. Production redlines remain in force unless and until a future SRD explicitly reopens them.

**Tech Stack:** Python, pandas, numpy, scikit-learn PCA, hmmlearn or equivalent HMM implementation, pytest, existing backtest artifact protocol.

---

### Task 1: Freeze scope and codify non-negotiable invariants

**Files:**
- Create: `docs/srd/recovery_hmm_shadow_srd.md`
- Modify: `docs/plans/2026-04-08-recovery-hmm-shadow-research.md`
- Test: `tests/research/test_recovery_hmm_contract.py`

**Step 1: Write the failing test**

```python
def test_recovery_hmm_shadow_contract_does_not_mutate_production_defaults():
    from src.research.recovery_hmm.contract import RecoveryHmmShadowContract

    contract = RecoveryHmmShadowContract()

    assert contract.shadow_only is True
    assert contract.production_beta_floor == 0.5
    assert contract.may_modify_live_target_beta is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_contract.py::test_recovery_hmm_shadow_contract_does_not_mutate_production_defaults -v`
Expected: FAIL because module does not exist.

**Step 3: Write minimal implementation**

Create a tiny immutable contract object in `src/research/recovery_hmm/contract.py` with:
- `shadow_only=True`
- `production_beta_floor=0.5`
- `may_modify_live_target_beta=False`
- a docstring stating this research track is non-production.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_contract.py::test_recovery_hmm_shadow_contract_does_not_mutate_production_defaults -v`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/srd/recovery_hmm_shadow_srd.md docs/plans/2026-04-08-recovery-hmm-shadow-research.md tests/research/test_recovery_hmm_contract.py src/research/recovery_hmm/contract.py
git commit -m "docs: define recovery HMM shadow contract"
```

### Task 2: Build the constrained factor-domain dataset

**Files:**
- Create: `src/research/recovery_hmm/feature_space.py`
- Create: `tests/research/test_recovery_hmm_feature_space.py`
- Reference: `data/macro_historical_dump.csv`
- Reference: `data/qqq_history_cache.csv`

**Step 1: Write the failing test**

```python
def test_feature_space_emits_locked_domain_columns(sample_macro_frame):
    from src.research.recovery_hmm.feature_space import build_feature_space

    frame = build_feature_space(sample_macro_frame)

    expected = {
        "L1_hy_ig_spread",
        "L2_curve_10y_2y",
        "L3_chicago_fci",
        "V1_spread_compression_velocity",
        "V2_real_yield_velocity",
        "V3_orders_inventory_gap",
        "S1_vix_term_ratio",
        "S2_qqq_skew_mean",
    }
    assert expected.issubset(frame.columns)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_feature_space.py::test_feature_space_emits_locked_domain_columns -v`
Expected: FAIL because builder does not exist.

**Step 3: Write minimal implementation**

In `src/research/recovery_hmm/feature_space.py`:
- load only the approved Level/Velocity/Sentiment fields
- derive the three velocity features exactly once
- normalize index handling to daily trading dates
- fail closed if required upstream columns are missing
- do not allow extra features into the returned frame.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_feature_space.py::test_feature_space_emits_locked_domain_columns -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_feature_space.py src/research/recovery_hmm/feature_space.py
git commit -m "feat: add locked recovery HMM feature space"
```

### Task 3: Add rolling PCA orthogonalization with explicit variance-retention rule

**Files:**
- Create: `src/research/recovery_hmm/orthogonalization.py`
- Create: `tests/research/test_recovery_hmm_orthogonalization.py`

**Step 1: Write the failing test**

```python
def test_rolling_pca_keeps_components_until_85pct_variance(sample_feature_frame):
    from src.research.recovery_hmm.orthogonalization import fit_transform_rolling_pca

    result = fit_transform_rolling_pca(sample_feature_frame, window=504, variance_threshold=0.85)

    assert result.component_count >= 1
    assert result.explained_variance_ratio_sum >= 0.85
    assert result.transformed.shape[0] == sample_feature_frame.shape[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_orthogonalization.py::test_rolling_pca_keeps_components_until_85pct_variance -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:
- 504-trading-day rolling covariance window
- PCA fit on standardized domain features
- smallest `k` satisfying explained variance >= `0.85`
- deterministic transformed output with component names like `PC1`, `PC2`, ...
- explicit metadata per date for `k` and explained variance sum.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_orthogonalization.py::test_rolling_pca_keeps_components_until_85pct_variance -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_orthogonalization.py src/research/recovery_hmm/orthogonalization.py
git commit -m "feat: add rolling PCA orthogonalization for recovery HMM"
```

### Task 4: Implement the asymmetric HMM state engine

**Files:**
- Create: `src/research/recovery_hmm/state_engine.py`
- Create: `tests/research/test_recovery_hmm_state_engine.py`

**Step 1: Write the failing test**

```python
def test_recovery_to_midcycle_transition_depends_on_level_and_momentum_decay():
    from src.research.recovery_hmm.state_engine import recovery_to_midcycle_probability

    p_fast_recovery = recovery_to_midcycle_probability(level_score=0.7, decay_score=0.9)
    p_faded_recovery = recovery_to_midcycle_probability(level_score=0.7, decay_score=0.1)

    assert p_fast_recovery < p_faded_recovery
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_state_engine.py::test_recovery_to_midcycle_transition_depends_on_level_and_momentum_decay -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:
- four-state HMM labels: `RECOVERY`, `MID_CYCLE`, `LATE_CYCLE`, `BUST`
- a standalone helper for `P(R -> M)_t = sigmoid(alpha * level - beta * decay)`
- state fitting on PCA components only
- no state freeze logic inside the HMM
- exported per-date posterior probabilities and most-likely state.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_state_engine.py::test_recovery_to_midcycle_transition_depends_on_level_and_momentum_decay -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_state_engine.py src/research/recovery_hmm/state_engine.py
git commit -m "feat: add asymmetric recovery HMM state engine"
```

### Task 5: Add the hardcoded shadow execution tensor

**Files:**
- Create: `src/research/recovery_hmm/execution_tensor.py`
- Create: `tests/research/test_recovery_hmm_execution_tensor.py`

**Step 1: Write the failing test**

```python
def test_shadow_execution_tensor_applies_entropy_and_fdas_multipliers():
    from src.research.recovery_hmm.execution_tensor import compute_shadow_weight

    result = compute_shadow_weight(
        state="RECOVERY",
        entropy=0.80,
        fdas_triggered=True,
        preserve_production_floor=True,
    )

    assert result["w_base"] == 1.0
    assert result["m_entropy"] < 1.0
    assert result["m_fdas"] == 0.15
    assert result["w_final"] >= 0.5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_execution_tensor.py::test_shadow_execution_tensor_applies_entropy_and_fdas_multipliers -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement a pure function that returns:
- `w_base`
- `m_entropy`
- `m_fdas`
- `w_final_raw`
- `w_final`

Important:
- keep the original research formula visible
- add a `preserve_production_floor` option
- default that option to `True` for shadow comparison against current repository contract.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_execution_tensor.py::test_shadow_execution_tensor_applies_entropy_and_fdas_multipliers -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_execution_tensor.py src/research/recovery_hmm/execution_tensor.py
git commit -m "feat: add shadow execution tensor for recovery HMM"
```

### Task 6: Build the true OOS audit runner

**Files:**
- Create: `src/research/recovery_hmm/audit.py`
- Create: `scripts/run_recovery_hmm_shadow_audit.py`
- Create: `tests/research/test_recovery_hmm_audit.py`

**Step 1: Write the failing test**

```python
def test_shadow_audit_respects_training_cutoff_and_oos_window(tmp_path):
    from src.research.recovery_hmm.audit import run_shadow_audit

    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
    )

    assert summary["training_end"] == "2021-12-31"
    assert summary["evaluation_start"] == "2022-01-01"
    assert summary["evaluation_end"] == "2024-12-31"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_audit.py::test_shadow_audit_respects_training_cutoff_and_oos_window -v`
Expected: FAIL

**Step 3: Write minimal implementation**

The runner must:
- fit PCA and HMM using data up to `2021-12-31`
- freeze those learned objects
- replay daily from `2022-01-01` to `2024-12-31`
- write separate artifacts under `artifacts/recovery_hmm_shadow/`
- emit trace columns for state, probabilities, entropy, FDAS trigger, and final shadow weight.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_audit.py::test_shadow_audit_respects_training_cutoff_and_oos_window -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_audit.py src/research/recovery_hmm/audit.py scripts/run_recovery_hmm_shadow_audit.py
git commit -m "feat: add recovery HMM shadow OOS audit runner"
```

### Task 7: Encode the acceptance criteria as tests, not prose

**Files:**
- Create: `tests/research/test_recovery_hmm_acceptance.py`
- Modify: `src/research/recovery_hmm/audit.py`

**Step 1: Write the failing test**

```python
def test_shadow_acceptance_hits_2022_defensive_floor_and_2023_recovery_reacceleration(tmp_path):
    from src.research.recovery_hmm.audit import run_shadow_audit

    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
    )

    assert summary["acceptance"]["q1_2022_below_or_equal_0_5"] is True
    assert summary["acceptance"]["q1_2023_above_or_equal_0_85"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_acceptance.py::test_shadow_acceptance_hits_2022_defensive_floor_and_2023_recovery_reacceleration -v`
Expected: FAIL

**Step 3: Write minimal implementation**

In the audit summary:
- compute minimum `w_final` inside `2022-01-01` to `2022-03-31`
- compute maximum and median `w_final` inside `2023-01-01` to `2023-02-28`
- set explicit boolean acceptance flags
- fail closed if required windows are missing.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_acceptance.py::test_shadow_acceptance_hits_2022_defensive_floor_and_2023_recovery_reacceleration -v`
Expected: PASS once the research model actually satisfies the thresholds.

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_acceptance.py src/research/recovery_hmm/audit.py
git commit -m "test: encode recovery HMM shadow acceptance criteria"
```

### Task 8: Add side-by-side comparison against the current production trace

**Files:**
- Create: `src/research/recovery_hmm/comparison.py`
- Create: `tests/research/test_recovery_hmm_comparison.py`
- Reference: `artifacts/v14_panorama/mainline/execution_trace.csv`

**Step 1: Write the failing test**

```python
def test_comparison_report_flags_recovery_release_vs_production_baseline(tmp_path):
    from src.research.recovery_hmm.comparison import compare_shadow_vs_production

    report = compare_shadow_vs_production(
        production_trace_path="artifacts/v14_panorama/mainline/execution_trace.csv",
        shadow_trace_path=tmp_path / "shadow_trace.csv",
    )

    assert "recovery_release_gap" in report
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_comparison.py::test_comparison_report_flags_recovery_release_vs_production_baseline -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Comparison output should quantify:
- `RECOVERY` frequency
- `MID_CYCLE` frequency
- `2022 Q1` defensive beta difference
- `2023 Q1` re-risking beta difference
- specific dates where shadow enters `RECOVERY` and production remains trapped in `BUST` or `LATE_CYCLE`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research/test_recovery_hmm_comparison.py::test_comparison_report_flags_recovery_release_vs_production_baseline -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/research/test_recovery_hmm_comparison.py src/research/recovery_hmm/comparison.py
git commit -m "feat: add recovery HMM comparison report"
```

### Task 9: Publish the research readout and decision gate

**Files:**
- Create: `docs/research/recovery_hmm_shadow_readout.md`
- Modify: `scripts/run_recovery_hmm_shadow_audit.py`

**Step 1: Write the failing test**

```python
def test_shadow_audit_writes_readout_ready_summary(tmp_path):
    from src.research.recovery_hmm.audit import run_shadow_audit

    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
    )

    assert "decision_gate" in summary
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/research/test_recovery_hmm_acceptance.py -k decision_gate -v`
Expected: FAIL

**Step 3: Write minimal implementation**

The readout must state one of:
- `REJECT`
- `SHADOW_ONLY`
- `CANDIDATE_FOR_INTEGRATION`

`CANDIDATE_FOR_INTEGRATION` is allowed only if:
- both OOS acceptance criteria pass
- no PIT breach is detected
- comparison report shows a real `RECOVERY` release improvement without violating the production floor contract.

**Step 4: Run test to verify it passes**

Run: `pytest tests/research -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/research/recovery_hmm_shadow_readout.md scripts/run_recovery_hmm_shadow_audit.py src/research/recovery_hmm tests/research
git commit -m "docs: add recovery HMM shadow decision gate"
```

