# QQQ Sidecar Model Specification (v14.7)

## 0. Overview

The QQQ Sidecar is a secondary risk model designed to capture Nasdaq-specific volatility and liquidity pressures that the Macro "Mud Tractor" may miss. This specification defines the **Physical Invariants** and **Feature Engineering** rules required to maintain architectural alignment and prevent overfitting.

## 1. Physical Sign Matrix (Inviolable Rules)

All Sidecar features must follow the **Left Tail Risk** convention. During model training (Logistic Regression), coefficients ($C$) must satisfy the following constraints. Violation triggers an `audit_failed_overfitting` error.

| Feature ID | Feature Name | Constraint | Physical Intuition |
| :--- | :--- | :--- | :--- |
| `growth_composite` | Macro Growth | $C_{growth} \le 0$ | Higher growth reduces risk. |
| `liquidity_composite` | Macro Liquidity | $C_{liquidity} \le 0$ | Higher liquidity reduces risk. |
| `stress_composite_extreme` | Macro Stress (Max) | $C_{stress} \ge 0$ | Higher credit/volatility spreads increase risk. |
| `vxn_acceleration` | VXN 3-day Jump | $C_{accel} \ge 0$ | Rapidly accelerating volatility increases risk. |
| `qqq_spy_relative_weakness` | QQQ/SPY Underperformance | $C_{weakness} \le 0$ | Negative relative strength (weakness) increases risk. |

> [!IMPORTANT]
> **Tractor-Parity Rule**: The Sidecar model must never use signs that contradict the Mud Tractor's macro intuition. If `liquidity_composite` becomes a positive risk contributor, the model is architecturally rejected.

---

## 2. Feature Engineering & Lookback Windows

Consistent lookback windows ensure that the Sidecar's sensors are calibrated against a stable historical baseline.

| Component | Logic | Window | Units |
| :--- | :--- | :--- | :--- |
| **Macro Anchors** | IPMAN, M2REAL, BAML Spread, VIX | **750d** | Rolling Z-Score (~3yr) |
| **VXN Level** | Standard Level | **750d** | Rolling Z-Score |
| **VXN Acceleration** | `^VXN - ^VXN.shift(3)` | **252d** | Rolling Z-Score (1yr) |
| **Relative Weakness** | `log(QQQ/SPY)` clipped at 0 | **252d** | Rolling Z-Score |

---

## 3. Panic Thresholds (Redlines)

These thresholds are derived from the V14 Expert Audit and used for target labeling and safety gating.

- **VXN Panic Level**: **35.0**. Any VXN level exceeding this is treated as a state of "Extreme Stress".
- **VXN Acceleration Redline**: **Z > 2.0**. A 3-day jump exceeding 2 standard deviations is a critical risk signal.
- **Sidecar Target Definition**: $Y_{qqq}=1$ if **QQQ MDD > 10%** or **VXN > 35** within the next 20 trading days.

---

## 4. Audit & Fail-Closed Protocols

- **Coefficient Audit**: Performed after every training cycle. If any coefficient sign flips, the model falls back to the previous stable state or `ConstrainedLogisticRegression` with hard bounds.
- **Data Gap Handling**: If `^VXN` or `SPY` sensors are missing, the Sidecar must produce a `NaN` prediction (Fail-Closed). It is better to have "Zero Signal" than a "Hallucinated Signal".

---
© 2026 QQQ Entropy AI Governance.
