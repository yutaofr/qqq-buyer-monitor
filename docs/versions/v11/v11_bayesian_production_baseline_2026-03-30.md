# V11 Bayesian Production Baseline

**Date:** 2026-03-30  
**Branch Context:** `erp-composite`  
**Status:** Production baseline for the v11.5 probabilistic engine, updated after the 2026-04-01 architecture cleanup.

## 1. Architectural Decisions

### A. Dual-Surface Contract
The system now treats these as separate decision surfaces:

- `target_beta`: portfolio risk-control surface for stock-of-assets exposure.
- `deployment_state`: incremental-cash pacing surface for new money deployment.

They are related, but they are no longer the same output under different names.

### B. Deterministic Runtime State
`data/v11_prior_state.json` is now the persistent runtime memory for:

- regime priors and transition counts
- last posterior
- current beta inertia state
- current bucket and cooldown
- stable regime state
- deployment pacing state

This removes the prior behavior where every live run re-created a fresh conductor and silently discarded all stability memory.
It is runtime state, not a checked-in research fixture or a source-of-truth model artifact.

### B1. Canonical Cold Start Only

Production and audit cold start must come from the canonical DNA library:

- `data/macro_historical_dump.csv`
- `data/v11_poc_phase1_results.csv`

If canonical DNA is missing, runtime and audit now fail closed.
Synthetic bootstrap is no longer part of the production or audit path; it is test-only disaster tooling.

### C. Regime Stability
`raw_regime` and `stable_regime` are now different surfaces.

- `raw_regime` = current posterior top-1
- `stable_regime` = entropy-aware stabilized regime state

High-entropy days must accumulate evidence before the stable regime can switch. This is an engineering stability rule, not a new macro heuristic.

### D. Execution Bucket Stability
The execution bucket layer no longer uses the old `0.45/0.55/0.95/1.05` deadband thresholds.

- natural beta boundaries are now used instead (`0.5` for `CASH/QQQ`, `1.0` for `QQQ/QLD`)
- bucket switches require entropy-aware evidence accumulation
- the `BehavioralGuard` barrier is now structural: `entropy_odds / bucket_state_count`
- bucket evidence is persisted in `data/v11_prior_state.json`

This keeps the execution surface deterministic while preventing one-day churn around a thin beta boundary.

### E. Retired Components
The following components were removed from the active code path on 2026-03-30:

- `src/engine/v11/signal/hysteresis_beta_mapper.py`
- `src/engine/v11/signal/data_degradation_pipeline.py`
- `scripts/v11_5_bayesian_hyper_grid_search.py`
- `src/engine/v11/core/position_sizer.ProbabilisticPositionSizer`

Reason:

- they were not part of the current production runtime
- they encoded the old fixed-threshold / degradation worldview
- keeping them in-tree made future refactors more likely to re-import stale logic
- `PositionSizingResult` remains as a pure payload contract, but the legacy sizing engine is retired

Historical roadmap documents that mention them should be read as archive context, not as production guidance.

## 2. Production Factor Set

### Kept In Production Seeder

- `spread_21d`
- `liquidity_252d`
- `real_yield_structural_z`
- `erp_absolute`
- `spread_absolute`
- `yield_absolute`

### Removed From Production Seeder

- `erp_21d_mom`
- `real_yield_10d_mom`
- `credit_accel_21d`
- `liq_mom_4w`

### Why They Were Removed
On the current labeled corpus, the short-horizon momentum/derivative bundle behaved as noise relative to stress-regime prediction, while the level/structural bundle dominated.

Observed 10-day lead correlations on the current production corpus:

| Feature | 10d Lead Corr |
| :--- | ---: |
| `spread_absolute` | `0.5186` |
| `spread_21d` | `0.5104` |
| `yield_absolute` | `0.3520` |
| `liquidity_252d` | `0.3477` |
| `real_yield_structural_z` | `0.1705` |
| `erp_absolute` | `0.1033` |
| `liq_mom_4w` | `0.0503` |
| `credit_accel_21d` | `0.0333` |
| `erp_21d_mom` | `0.0309` |
| `real_yield_10d_mom` | `0.0102` |

## 3. Factor Role Policy

### Primary Regime Drivers

- credit spread level and spread structure
- real-yield level / structural pressure
- liquidity level

### Secondary Valuation Surface

- `ERP` remains useful, but not as a primary regime driver
- its production role is now valuation / pacing support (`erp_absolute`, `value_score`)

Do not re-promote ERP momentum into the regime core without out-of-sample evidence.

## 4. Risk Pricing Policy

### Threshold-Free Entropy Pricing

Risk pricing is now threshold-free.

- no fixed entropy cutoff
- no “high entropy -> pull back to 1.0x” behavior
- no non-Bayesian outlier override in the active production path

Current rule:

- `raw_target_beta = E[beta | posterior]`
- `target_beta = raw_target_beta * exp(-H)`

where `H` is the Shannon entropy of the posterior in natural-log space.
This preserves determinism and guarantees that uncertainty can only reduce risk, never increase it.

### JIT Model Integrity

Every fitted `GaussianNB` now passes a deterministic coefficient validation contract before it can be used:

- `classes_` must match the supplied regime DNA
- `theta_`, `var_`, and `class_prior_` must be finite
- `var_` must stay strictly positive
- `class_prior_` must stay positive and sum to `1.0`

This closes the old gap where JIT training was correct in principle but could still admit silently corrupted coefficients.

### Feature DNA Parity

`ProbabilitySeeder` is now bound to the audit archive by a deterministic feature contract:

- `feature_names` are recorded in `regime_audit.json`
- the seeder config is hashed into `feature_contract.seeder_config_hash`
- production and backtest both fail closed if the live seeder hash drifts from the audited hash

This closes the old spec-to-code gap where feature engineering could change without invalidating the archived calibration.

### Data Quality Penalty

Live runtime now distinguishes between:

- canonical direct observations
- degraded proxy observations
- missing observations

When a live input arrives through a degraded proxy path such as `proxy:nfci` or `proxy:hyg`, the conductor now raises effective entropy through a deterministic data-quality penalty:

- `quality_score` is computed from core field availability/provenance
- `effective_entropy = 1 - ((1 - posterior_entropy) * quality_score)`

This means degraded live data cannot be treated as if it had the same informational clarity as canonical DNA, even if the classifier itself remains numerically stable.

## 5. Current Measured Result

Current `python -m src.backtest --evaluation-start 2018-01-01` result on the checked-in corpus:

- `Accuracy: 98.71%`
- `Brier: 0.0225`
- `Mean Entropy: 0.046`
- `Lock: 0.4%`

Methodology:

- deterministic walk-forward audit
- daily causal re-fit of `GaussianNB(var_smoothing=1e-2)`
- no reuse of production runtime state

Repeated runs on 2026-04-01 produced identical audit output.

## 6. Research Guardrails

Do not add a factor back into production unless it beats the current baseline on the accepted audit corpus in at least one of:

- lower Brier score
- higher top-1 accuracy
- lower entropy without hurting Brier
- improved target-beta fidelity without increasing daily churn

If a factor is economically intuitive but empirically weak, convert it to:

- a valuation overlay
- a deployment pacing input
- an explainability-only field

Do not keep it in the regime core “just in case”.
