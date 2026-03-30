# Class A Factor Extension Audit: Real Yield & NFCI (v11 Research)

**Date:** 2026-03-30  
**Status:** Research Validated  
**Target:** V11 Bayesian Inference Engine

## 1. Executive Summary
The evaluation of additional Class A factors confirms that the **derivative of Real Yield (10Y)** is the most significant missing vector in the current v11 baseline. Its inclusion increases feature space coverage (PCA variance) from 84% to 93%, providing critical early-warning signals for "valuation shocks" that are often missed by credit-centric metrics.

## 2. Quantitative Results

| Feature Set | PCA Variance Explained | Sample Count | Note |
| :--- | :--- | :--- | :--- |
| Baseline (VIX, DD, Breadth) | 84.12% | 6786 | Production Baseline |
| + Real Yield (Level) | 75.91% | 5668 | Adds noise, reduces concentration |
| **+ Real Yield (Derivative)** | **92.68%** | 5539 | **Top Performer: Captures Rate Shocks** |
| + NFCI (State Change) | 72.47% | 6785 | Redundant with Credit Spreads |

## 3. Correlation Matrix (Signal Integrity)
- **Real Yield vs Credit**: Correlation is near zero (-0.01). This confirms Real Yield is a "pure" denominator-driven risk factor.
- **NFCI vs Credit**: Correlation is 0.27. NFCI acts as a useful confirmation but is not strictly independent of HY Spreads.

## 4. Architectural Decision
- **AD-11.4**: Integration of `real_yield_10y_pct_momentum` (Z-Score of 10d diff) into the `FeatureLibraryManager`.
- **AD-11.5**: Use `funding_stress_flag` only as a secondary confirmation gate (Behavioral Guard) rather than a primary inference feature, to maintain PCA density.

## 5. Verification
The findings were generated using `scripts/v11_class_a_parallel_research.py` under a Dockerized environment, ensuring strict consistency with the v11 production data contracts.
