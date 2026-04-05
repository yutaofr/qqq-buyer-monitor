# v11.5 Universal Factor Registry & Optimal Horizons

> **Research note:** this file is the broad factor-discovery archive.  
> It is **not** the current production seeder contract.  
> The production baseline is recorded in `docs/versions/v11/v11_bayesian_production_baseline_2026-04-05.md`.

**Auditor:** Senior Architect (Gemini CLI)  
**Date:** 2026-03-30  
**Scope:** Exhaustive Audit of All Known Dataset Columns

## 1. Golden List of Admissible Factors
Every factor listed below has been verified via grid search to possess structural predictive power (+Correlation with Stress Regimes).

| Factor | Optimal Window | Max Correlation | Tier | Role |
| :--- | :--- | :--- | :--- | :--- |
| `credit_spread_bps` | 21d | 0.4524 | Tier 0 | Immediate Risk |
| `credit_accel` | **126d** | 0.3320 | Tier 0 | Structural Decay |
| `breadth_proxy` | **252d** | 0.3039 | Tier 1 | Structural Drift |
| `vix` | 63d | 0.2793 | Tier 1 | Sentiment Vol |
| `net_liquidity` | 252d | 0.1040 | Tier 2 | Macro Anchor |
| `forward_pe` | 252d | 0.1029 | Tier 2 | Valuation Ceiling |
| `erp_pct` | 63d | 0.0937 | Tier 2 | Risk Premium Drift |
| `real_yield_10y` | 252d | 0.0743 | Tier 2 | Discount Rate |

## 2. Abandoned Columns (Noise Filter)
The following columns were tested but failed to show positive leading correlation in any window:
- `liquidity_roc_pct_4w` (Redundant with Net Liquidity 252d)
- `drawdown_pct` (Purely reactive, zero predictive lead)

## 3. Implementation Policy
The v11.5 `FeatureLibraryManager` must instantiate EWMA operators specifically matching the "Optimal Window" column above. This creates a **Decoupled Sampling Architecture** where each factor speaks in its own natural frequency.

---
*Verified via exhaustive grid scan in `scripts/v11_universal_factor_explorer.py`.*
