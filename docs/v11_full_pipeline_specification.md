# Full-Pipeline Multi-Scale Specification (v11.5)

**Status:** ARCHITECTURAL BLUEPRINT  
**Version:** 11.5  
**Auditor:** Senior Architect (Gemini CLI)

## 1. Pipeline Architecture Definition
v11.5 implements a **Temporal Layering** approach, matching each factor class to its optimal physical horizon within the decision pipeline.

## 2. Layer 0: Regime Inference (Class A)
- **Objective**: Structural Environment Identification.
- **Horizon Policy**: **Strategic / Macro (63d - 252d)**.
- **Key Implementation**:
    - `erp_momentum` -> **63d** (Smoothed)
    - `real_yield_momentum` -> **252d** (Annual Anchor)
    - `credit_spread_accel` -> **21d** (The only permitted tactical macro signal)

## 3. Layer 1: Deployment Pacing (Class B)
- **Objective**: Incremental Capital Entry/Exit Speed.
- **Horizon Policy**: **Bimodal (Tactical + Tactical-Intermediate)**.
- **Key Implementation**:
    - `vix_mean_reversion` -> **126d** (Anchors pacing to long-term vol regimes)
    - `breadth_exhaustion` -> **5d** (Triggers fast entry on extreme sentiment washouts)
    - `drawdown_velocity` -> **21d** (Standard pacing trigger)

## 4. Layer 2: Fidelity Guard (Class C)
- **Objective**: Asset Selection & Tracking Error Control.
- **Horizon Policy**: **Operational-Static (252d)**.
- **Key Implementation**:
    - `relative_strength_drift` -> **252d** (Identifies long-term structural failure of QQQ vs QQEW)
    - `beta_fidelity_audit` -> **5d** (Weekly rebalancing threshold)

## 5. Summary of Optimal Horizons
| Factor Class | Pipeline Stage | Primary Window | Target Metric |
| :--- | :--- | :--- | :--- |
| **Class A** | Regime | **252d** | Accuracy / Entropy |
| **Class B** | Pacing | **126d / 5d** | Return / Drawdown |
| **Class C** | Fidelity | **252d** | Tracking Error |

---
*Verified via `scripts/v11_universal_factor_explorer.py` across 25 years of historical data.*
