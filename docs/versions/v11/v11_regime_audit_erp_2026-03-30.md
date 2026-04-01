# Architectural Audit: V11 Regime Classification & ERP Sensitivity

**Date:** 2026-03-30  
**Context:** V11 Probabilistic Monitor Production Baseline  
**Auditor:** UI/UX & Systems Architect

## 1. Audit Objective
To verify why the V11 engine maintains a `MID_CYCLE` classification (99.9% probability) despite a historically low Equity Risk Premium (ERP) of **2.02%**, and to confirm if this behavior aligns with the V11 specification.

## 2. Technical Findings

### A. Feature Omission by Design (SRD 4.2)
The V11 Bayesian Inference Engine explicitly excludes ERP from its core feature set. The inference is driven by six specific stress vectors:
1.  `spread_stress`: High Yield Credit Spreads (BAMLH0A0HYM2).
2.  `liquidity_stress`: Net Liquidity 4-Week ROC.
3.  `vix_stress`: 1-Month Implied Volatility.
4.  `drawdown_stress`: Rolling maximum drawdown.
5.  `breadth_stress`: Percent of stocks above 50-day moving average.
6.  `term_structure_stress`: VIX / VIX3M ratio.

**Rationale:** ERP has shown reduced predictive power for regime shifts during the current "Everything Rally" and QT-normalization cycles. V11 prioritizes **Credit and Liquidity causality** over valuation-based signals.

### B. Stable Core Metrics (Current Snaphot)
As of the 2026-03-27 observation:
- **Credit Spread:** 321 bps (Within normal historical bounds for MID_CYCLE).
- **Liquidity ROC:** +0.78% (Positive momentum, non-recessive).
- **VIX:** 31.0 (Elevated but stable relative to the 20-year EWMA rank).

### C. Posterior Certainty & Entropy (P-3 Principle)
- **Entropy Score:** `1e-06` (Near zero).
- **Uncertainty Penalty:** 0%.
- **Target Beta:** 0.90x (Consistent with raw advisory for `MID_CYCLE`).

The Bayesian engine displays extremely high confidence because the current PCA coordinates fall squarely within the `MID_CYCLE` cluster trained in the `CalibrationService`.

### D. Behavioral Guard Stability (FR-3)
Even if macro metrics were to deteriorate slightly, the **Behavioral Guard** enforces:
- **T+1 Settlement Locks:** Prevents rapid oscillating between buckets.
- **Deadband Hysteresis:** A shift to `LATE_CYCLE` or `CASH` requires target beta to cross strict thresholds (e.g., `< 0.45` for CASH) to avoid noise-driven churn.

## 3. Conclusion
The current `MID_CYCLE` status is **architecturally correct**. The "Low ERP" is a secondary valuation metric that is monitored for UI display but is **intentionally decoupled** from the Bayesian inference pipeline to ensure the system remains focused on physical liquidity and credit reality rather than subjective valuation "cheapness".

---
*Verified against `conductor/tracks/v11/spec.md` and `src/engine/v11/core/feature_library.py`.*
