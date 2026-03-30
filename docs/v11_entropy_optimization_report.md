# v11.5 Factor Entropy & Information Gain Specification

**Auditor:** Senior Architect (Gemini CLI)  
**Date:** 2026-03-30  
**Status:** ARCHITECTURAL MANDATE

## 1. Executive Summary
Information-theoretic audit confirms that factor selection must balance **Confidence (Low Base Entropy)** and **Discrimination (High Stress Entropy Spike)**. Valuation factors (ERP/PE) provide confidence, while Macro factors (Real Yield) provide discrimination.

## 2. Quantitative Entropy Matrix

| Bundle | Mean Entropy (Lower=Better) | Discrimination (Higher=Better) | Verdict |
| :--- | :--- | :--- | :--- |
| Baseline | 1.0024 | 0.7282 | Baseline |
| **Valuation-Heavy** | **0.8472** | 0.6384 | **Confidence Anchor** |
| **Rate-Heavy (Real Yield)** | 0.9883 | **0.8470** | **Stress Sentry** |
| Global All-Factor | 0.9301 | 0.7250 | Redundant |

## 3. Factor Selection for v11.5 Inference Engine
To maximize risk-adjusted signals, the v11.5 Bayesian Engine shall standardize on the **Rate-Heavy Bundle**:
- `credit_spread_bps` (21d)
- `vix` (63d)
- `real_yield_10y_momentum` (252d)
- `breadth_proxy` (252d)

## 4. Uncertainty Penalty Policy (Entropy-to-Beta)
- **Base Regime Beta**: Determined by posterior Top-1.
- **Uncertainty Haircut**: Applied linearly when **Normalized Entropy > 0.75**.
- **Discrimination Bonus**: If `real_yield_momentum` drives the entropy spike, the haircut is increased by 1.5x (Fast Deleveraging).

---
*Verified via KDE Likelihood Simulation in `scripts/v11_entropy_efficiency_audit.py`.*
