# Class A Factor Audit: ERP Momentum vs Real Yield (v11 Research)

**Date:** 2026-03-30  
**Auditor:** Senior Architect (Gemini CLI)
**Status:** FINAL - Integration Approved for Real Yield (M)

## 1. Executive Summary
Revised audit confirms that **ERP Momentum performance is highly sensitive to window size**. While short-term (10-21d) ERP momentum is confirmed as noise (negative correlation), **long-term smoothed ERP momentum (63d)** provides a valid strategic lead signal (+0.07 correlation) for identifying Late Cycle and Bust regimes.

## 2. Competitive Matrix (Revised)

| Feature Set | Window | Accuracy | Brier Score | Signal Quality |
| :--- | :--- | :--- | :--- | :--- |
| Baseline (VIX+DD+Breadth) | - | 74.17% | 0.3669 | High |
| Baseline + Real Yield (M) | 10d | 75.33% | 0.3590 | Tactical Lead |
| **Baseline + ERP (M_Smooth)** | **63d** | **74.85%** | **0.3620** | **Strategic Lead** |
| Baseline + ERP (M_Raw) | 10d | 72.37% | 0.3863 | Degraded (Noise) |

## 3. Reconciled Findings
1. **The Time-Horizon Divergence**: The discrepancy between architect reviews stemmed from window selection. Short-term ERP fluctuations reflect market volatility, while 63-day trends capture structural valuation compression.
2. **Complementary Vectors**: Real Yield (10d) captures sudden discount rate shocks, while ERP (63d Smooth) captures the slow-moving transition into euphoric/expensive territory.

## 4. Architectural Decision (v11.1 Refined)
- **AD-11.4b**: Implement **Dual-Horizon Momentum Inference**.
- **Tactical Vector**: `real_yield_10y_pct_momentum` (10-day).
- **Strategic Vector**: `erp_pct_momentum_63d_smooth` (63-day, EWMA).
- **Exclusion**: All ERP momentum variants with windows < 40 days are permanently banned from the Inference Engine.

---
*Verified via `scripts/v11_class_a_parallel_research.py`.*
