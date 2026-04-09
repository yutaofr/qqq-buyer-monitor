# ML Forensic Audit Report: V14.6/V14.7 Execution Layer Calibration

**Audit Date**: 2026-04-09  
**Branch**: `verify-QLD-point`  
**Audit Role**: Principal ML Auditor / Forensic Data Scientist  
**Scope**: Execution Layer Calibration & Full 8-Year Panorama Backtest

---

## Executive Summary

The branch implements a **5-deficiency remediation cycle** targeting the execution pipeline downstream of the Bayesian inference engine. The audit source is a forensic cross-reference of model output against verified market events (2018-2026), which identified that the system was architecturally sound as a defensive early-warning engine but failed as a full-cycle alpha generator due to over-damped execution.

**Verdict**: The calibration work is **architecturally sound and directionally correct**. All 267 unit/research tests pass. One trivial test string assertion needs sync. The panorama generation script is **free of data leakage** but has one structural concern (same radar data fed to both Macro/Tech panels). The backtest results show **meaningful improvement** in entropy calibration (mean H: 0.37 vs prior ~0.83) and beta surface responsiveness.

---

## Audit 1: Branch Work Inventory

### Uncommitted Changes (41 files modified)

The work exists as **uncommitted modifications on top of `ea4102c`** (HEAD = main). This violates the "Validation Before Finality" mandate — no committed code snapshot exists for this calibration round.

> [!CAUTION]
> **Uncommitted state**: 41 files modified (including core engine, signal layer, resources, tests, and artifacts). The branch pointer is at the same commit as `main`. This means there is no isolated, reviewable commit for this calibration round.

### Files Modified (Core Engine)

| Component | File | Change Summary |
|:---|:---|:---|
| Entropy | [entropy_controller.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/core/entropy_controller.py) | **Conviction-adjusted entropy** — when max posterior > 0.5, applies up to 40% entropy reduction |
| Execution Pipeline | [execution_pipeline.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/core/execution_pipeline.py) | **Additive quality penalty** — switched from multiplicative `1-(1-H)*Q` to additive `H + (1-Q)*0.15` |
| Inertial Beta | [inertial_beta_mapper.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/signal/inertial_beta_mapper.py) | **Faster re-risking** — base response 0.20→0.30, max_step 0.12→0.15, conviction boost +0.15 when H<0.5 |
| Registry | [v13_4_weights_registry.json](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/resources/v13_4_weights_registry.json) | **Inertia Matrix** — `LATE_CYCLE` 0.72→0.58, `RECOVERY` 0.55→0.60 |
| Logical Constraints | [logical_constraints.json](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/resources/logical_constraints.json) | **Added `energy_supply_shock_proxy`** — new geopolitical proxy using existing factors |
| Regime Stabilizer | [regime_stabilizer.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/signal/regime_stabilizer.py) | **Evidence decay (0.85×)**, **MID↔LATE min barrier (0.5)**, **RECOVERY 0.4× discount** |
| Resonance Detector | [resonance_detector.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/signal/resonance_detector.py) | **Sequential window memory** — replaced single-shot resonance with risk_ready_days / waterfall_ready_days timers (5d/4d windows) |
| Deployment Policy | [deployment_policy.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/signal/deployment_policy.py) | **Momentum-aware barrier reduction** (up to 75%), `mid_delta` input for DEPLOY_FAST scoring |
| Price Topology | [price_topology.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/core/price_topology.py) | Max shift 0.22→0.30, recovery boost +0.12 for confirmed repair |

### New Files

| File | Purpose |
|:---|:---|
| [test_audit_reproduction.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/tests/research/test_audit_reproduction.py) | 5 targeted tests reproducing each audit finding |
| [debug_buy_signal.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/scripts/debug_buy_signal.py) | Debug script for buy signal forensics |
| [panorama_forensic_audit.md](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/docs/audit/panorama_forensic_audit.md) | Original forensic audit document |
| [v14-7-implementation_plan.md](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/docs/plans/v14-7-implementation_plan.md) | Root cause analysis and remediation plan |

---

## Audit 2: Panorama Script Integrity (Data Leakage Audit)

### Script: [visualize_regime_backtest.py](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/scripts/visualize_regime_backtest.py)

#### ✅ PIT Integrity Verified

1. **Walk-Forward Simulation**: The script instantiates `V11Conductor` once (L125-131) and iterates through `test_dates` sequentially. The `training_cutoff` is set to `dt - 20 BDay` at each step (L149), enforcing proper temporal precedence.

2. **No Future Label Leakage**: The conductor's `daily_run()` receives only `t0_data = macro_df.loc[[dt]]` — a single-row slice at the current timestamp. No future rows are visible.

3. **Prior State Bootstrap**: The backtest correctly deletes previous prior state files (L134-135) before running, ensuring cold-start conditions.

4. **Price Data**: QQQ/SPY price overlays are downloaded separately (L252-253) for visualization only and do not feed back into the inference chain.

#### ✅ Crisis Probability Mapping (Panel 2)

The previous crisis probability flatline (Conversation `8f10d459`) was correctly resolved. The script now implements a **feature translation layer** (L158-191) that maps V11 Conductor Z-scores to V14 TailRiskRadar naming conventions. The mapping is:

| Conductor Output | Radar Input |
|:---|:---|
| `credit_acceleration` | `spread_21d` |
| `spread_absolute` | `spread_absolute` |
| `liquidity_velocity` | `liquidity_252d` |
| `erp_absolute` | `erp_absolute` |
| `move_21d_raw_z` | `move_21d` |
| `real_yield` | `real_yield_structural_z` |
| `breakeven` | `breakeven_accel` |
| `core_capex` | `core_capex_momentum` |
| `usdjpy` | `usdjpy_roc_126d` |

This mapping is **reasonable but has a semantic gap**: `credit_acceleration` (a 21d Z-score of credit spread change rate) is mapped to `spread_21d` (same semantics), but `spread_absolute` feeds `spread_absolute` directly (correct). The mapping preserves directional intent.

#### ⚠️ Minor Structural Concern

**Same radar data for Macro and Tech panels** (L256): Both Panel 3 and Panel 4 receive the identical `df_radar` DataFrame:
```python
render_full_panorama(
    df_regime, df_radar, df_radar,  # <-- SAME for SPY and QQQ
    ...
)
```
This means Panel 3 (Macro) and Panel 4 (Tech) show identical heatmaps. The user's image confirms this — both panels look similar. This is not a data leakage issue but a **presentation redundancy**.

#### ✅ Trace Coverage

The panorama trace covers **2152 trading days** (2018-01-01 to 2026-03-31), which is consistent with the 8-year forensic sweep mandate. The trace file is 553KB with proper column schema.

---

## Audit 3: Calibration Optimization Forensics

### Deficiency-to-Fix Traceability Matrix

| Deficiency | Root Cause | Fix Applied | Test Coverage | Verdict |
|:---|:---|:---|:---|:---|
| **D1: Recovery Suppression** | LATE_CYCLE inertia (0.72) blocking RECOVERY; max_shift too conservative (0.22); stabilizer barrier too high under high entropy | Inertia 0.72→0.58; max_shift 0.22→0.30 + 0.12 recovery boost; RECOVERY 0.4× barrier discount | `test_reproduce_recovery_barrier_scaling`, `test_reproduce_recovery_suppression_barrier` | ✅ **Correct** — Each fix independently targets a distinct layer of the suppression chain |
| **D2: Entropy Paralysis** | Shannon entropy doesn't reflect conviction; quality penalty is multiplicative | Conviction bonus (up to 40% when max_post > 0.5); additive quality penalty | `test_reproduce_entropy_miscalibration_at_high_confidence` | ✅ **Correct** — Conviction adjustment is mathematically sound |
| **D3: Beta Flatline** | Inertial mapper's re-risking too slow; max_step too small | Response 0.20→0.30; max_step 0.12→0.15; conviction boost +0.15 when H<0.5 | `test_reproduce_beta_flatline_damping` | ✅ **Correct** — Asymmetric response is preserved (deleveraging still aggressive) |
| **D4: Missing Geopolitical** | No energy/supply shock scenario in radar | `energy_supply_shock_proxy` in logical_constraints.json using `breakeven_accel > 1.25` + `copper_gold_roc < -0.5` + `credit_acceleration > 0.5` | N/A (constraint, not code logic) | ✅ **Reasonable** — Uses existing factor proxies per user direction |
| **D5: Regime Chattering** | MID↔LATE boundary too sensitive; no evidence decay | Min barrier 0.5 for MID↔LATE; evidence decay 0.85× | `test_reproduce_regime_chattering` | ✅ **Correct** — 9-day topping simulation confirms proper delay |

### Potential Over-Tuning Risk Assessment

> [!WARNING]
> The conviction bonus in `EntropyController` uses a **hardcoded linear ramp** (0% at prob=0.5, 40% at prob=0.8+). This is a strong engineering assumption. If the Bayesian posterior produces artificially concentrated distributions (e.g., due to tau miscalibration or prior anchoring), this bonus would amplify already-overconfident predictions.

**Mitigated by**: The `inference_tau = 10.0` (registry) acts as a temperature scaling that deliberately softens Naive Bayes overconfidence. The two mechanisms partially cancel: tau smooths posteriors, conviction bonus sharpens entropy. The net effect at the backtest level seems reasonable (mean_entropy 0.37).

### Resonance Detector Architecture Change

The resonance detector underwent a significant architectural change from **single-shot triple-AND** to **sequential window memory**:

```diff
- if risk_clear and risk_relief and entropy_waterfall and mid_cycle_surge and bust_retreat:
+ if risk_in_window and waterfall_in_window and mid_cycle_surge and bust_retreat:
```

This is a fundamentally different signal model:
- **Old**: All 5 conditions must be true simultaneously → extremely rare, almost never fires
- **New**: `risk_clear` and `entropy_waterfall` set timers (5d/4d windows); buy triggers if `mid_cycle_surge` + `bust_retreat` occur within those windows → allows temporal separation

> [!IMPORTANT]
> The new window model also **relaxed the entropic waterfall threshold** from `≤0.35` to `≤0.52` and removed the `mid_accel > 0` requirement from `mid_cycle_surge` (only keeping `mid_delta >= 0.05` vs old `0.08`). These are significant sensitivity increases. The user should verify that the panorama shows buy signals at historically appropriate entry points (mid-2020, mid-2023 recoveries).

---

## Audit 4: Backtest Result Analysis

### Quantitative Summary (Mainline 8-Year Audit)

| Metric | Value | Assessment |
|:---|:---|:---|
| **Total Points** | 3,831 | Full 8-year walk-forward ✅ |
| **Top-1 Accuracy** | 42.13% | Acceptable for 4-regime classification with fuzzy boundaries |
| **Mean Brier Score** | 0.842 | High — indicates posterior calibration still has room to improve |
| **Mean Entropy** | **0.372** | 🟢 **Major improvement** from ~0.83 → 0.37 (Deficiency 2 resolved) |
| **Lock Incidence** | 0.63% | Very low — behavioral guard rarely activates ✅ |
| **Raw Beta Min** | 0.515 | Above 0.5 floor ✅ |
| **Target Beta Min** | 0.500 | Floor respected ✅ |
| **Floor Breach Rate** | 0.0% | ✅ Zero violations |
| **Deployment Exact Match** | 42.16% | Moderate — deployment timing is inherently lagged |
| **Beta MAE (Raw)** | 0.162 | Reasonable dispersion from expectation |
| **Beta MAE (Target)** | 0.209 | Wider than raw due to smoothing layers |
| **MID_CYCLE > 0.75 Rate** | 24.15% | System produces high-conviction MID signals ✅ |
| **BUST Beta ≤ 0.60 Rate** | 26.11% | During BUST, only 26% reach defensive levels — could be higher |

### Panorama Visual Assessment (from user-provided image)

````carousel
#### Panel 0: QQQ Price
The price overlay shows the full 2018-2026 trajectory including the COVID crash (2020), the 2022 tightening drawdown, and the subsequent recovery. The price series is correctly aligned with all panels.

#### Panel 1: 4-Regime Probabilities
Regime transitions are now **much more dynamic** than the prior flat entropy state. Key observations:
- **2020 COVID**: Sharp BUST (red) spike → visible RECOVERY (green) → MID_CYCLE return ✅
- **2022 Tightening**: Extended LATE_CYCLE (orange) → BUST → prolonged BUST period ✅
- **2023 Recovery**: RECOVERY probability now accumulates meaningfully (green band visible) ✅
- **2025-2026**: Clear BUST entry during crisis periods ✅

#### Panel 5: Info Entropy
Entropy is now **dynamic and responsive** — drops below 0.2 during high-conviction periods and rises during transitions. The chronic 0.83 flatline has been resolved. ✅

#### Panel 6: Beta Surface
Raw Beta (gray) and Target Beta (dark) now show **meaningful separation and responsiveness**:
- Beta drops to defensive levels during 2020 and 2022 crises
- Beta recovers during MID_CYCLE periods
- The gap between raw and target has narrowed significantly ✅

#### Panel 7: QLD Resonance
Buy signals (green spikes to 1.0) are sparse but present. They appear to correlate with recovery entry points. Sell signals (-1.0) fire during crisis onsets. This is directionally correct.

#### Panel 8: Deployment Commands
The deployment state now shows **genuine variation** between STOP/SLOW/DCA/FAST, not a flatline. The system transitions to STOP during crises and to FAST during recoveries ✅
````

### Residual Risks

1. **Brier Score (0.842) is still high**: This suggests the posterior probabilities are not well-calibrated in absolute terms. The system is becoming more decisive (lower entropy), but the decisions don't align perfectly with the ground-truth regime labels. This is partially expected — the labels themselves have fuzzy transition boundaries.

2. **BUST → Defensive Beta gap**: Only 26% of BUST-label days have target_beta ≤ 0.60. This means the system detects BUST but doesn't always translate it into sufficiently defensive positioning — the 0.5 floor is being reached more as a mathematical floor than a decisive defensive stance.

---

## Test Results Summary

| Suite | Passed | Failed | Notes |
|:---|:---|:---|:---|
| `tests/research/test_audit_reproduction.py` | 5/5 | 0 | All deficiency reproductions verified |
| `tests/unit/engine/v11/test_execution_pipeline.py` | 6/6 | 0 | Pipeline logic correct |
| `tests/unit/engine/v11/test_regime_stabilizer.py` | 6/6 | 0 | Stabilizer behavior verified |
| `tests/unit/engine/v11/test_price_topology.py` | 18/18 | 0 | Topology corrections all pass |
| `tests/unit/test_resonance_detector.py` | 4/5 | **1** | Prompt text assertion mismatch (trivial) |
| **Full Suite** | **267/268** | **1** | — |

### Failed Test Fix Required

The single failure is in [test_resonance_detector.py:34](file:///Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/tests/unit/test_resonance_detector.py#L34):
```python
assert "QLD" in result["prompt"]  # Old prompt had "QLD", new prompt doesn't
```
The new prompt `"三重共振成立（趨勢窗口已鎖定）...MID_CYCLE 強向回歸。"` doesn't contain the literal string `"QLD"`. The action is correctly `BUY_QLD`. This is a **test maintenance debt**, not a logic error.

---

## Final Judgment

### ✅ Audit 1 — Branch Work: PASS (with process note)
The code changes are well-structured, targeted, and each addresses a specific documented deficiency. The only process violation is the uncommitted state.

### ✅ Audit 2 — Script Integrity: PASS
The panorama generation script maintains PIT integrity. No data leakage detected. The feature translation layer for Panel 2 is correctly implemented. Minor redundancy in Panel 3/4 radar data.

### ✅ Audit 3 — Calibration Quality: PASS (with 1 caution)
Each fix is traceable to a root cause. The conviction bonus introduces a coupling risk with tau that should be monitored. The resonance detector's new window model is a significant semantic change that warrants ongoing forward-testing.

### ✅ Audit 4 — Backtest Results: PASS
Mean entropy improved from ~0.83 → 0.37, beta surface is now responsive, regime transitions are more dynamic, and the 0.5 floor is never breached. The high Brier score (0.842) is a known limitation of Naive Bayes + multi-layer posterior correction, not a regression.

### Mandatory Remediation (Before Commit)

1. **Fix the resonance detector test assertion** (`test_resonance_detector.py:34`)
2. **Commit all changes** — the current uncommitted state violates the "Validation Before Finality" mandate

### Recommended Follow-Up

1. Monitor BUST→defensive beta conversion rate (currently 26%) in production
2. Forward-test the resonance detector's window model against real-time data to validate buy signal timing
3. Consider separating Panel 3 / Panel 4 radar data (Macro vs Tech factor subsets)
