# QQQ "Entropy" Monitor (v11.5)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Audit: 27yr Passed](https://img.shields.io/badge/Audit-27yr_Passed-green.svg)](docs/audit/v11_5_comprehensive_audit_report.md)

**QQQ Entropy** is a unified Bayesian probabilistic engine for portfolio risk management. It leverages 25+ years of macro memory to synthesize optimal `Target Beta` recommendations and `Incremental Cash` deployment pacing through information-theoretic risk pricing.

> "The exoskeleton doesn't walk for you, but it keeps you upright in the storm."

---

## 🧠 Core Philosophy: Bayesian-Core
v11.5 marks the final convergence from threshold-based logic to **Pure Probabilistic Inference**.
*   **JIT Intelligence**: Real-time GaussianNB training on the latest macro DNA (`macro_historical_dump.csv`). No pre-trained weights; logic follows data.
*   **Uncertainty Pricing**: Shannon Entropy quantifies model doubt, triggering threshold-free exponential "haircuts" on risk exposure.
*   **Self-Healing Data**: **Data Quality Penalty (DQP)** automatically raises uncertainty when sensor degradation or proxy data is detected.
*   **DNA Contract**: SHA-256 configuration hashing enforces deterministic feature-contract parity across research and production.

## 🚀 Performance Snapshot (2018-2026 Audit)
Verified via `python -m src.backtest` across **3,012 causal windows**:

| Metric | Performance | Status |
| :--- | :--- | :--- |
| **Top-1 Accuracy** | **98.71%** | Verified via daily walk-forward re-fit |
| **Brier Score** | **0.0225** | High-fidelity probability calibration |
| **Mean Entropy** | **0.046** | High-confidence inference clusters |
| **Lock Incidence** | **0.4%** | Optimal balance between stability and agility |

## 🛠 Quick Start

### 1. Environment Setup
```bash
pip install -e .[dev]
```

### 2. Live Run (T+0)
Generate today's Bayesian signal and update cloud state:
```bash
python -m src.main
```

### 3. Fidelity Audit (Backtest)
Run the causal isolation audit:
```bash
python -m src.backtest --evaluation-start 2018-01-01
```
*Full audit report: `docs/audit/v11_5_comprehensive_audit_report.md`*

## 🏗 System Architecture

```mermaid
graph TD
    A[Macro DNA] -->|JIT Fit| B[GaussianNB Engine]
    C[Live Feed] -->|DQP Audit| D[Inference Matrix]
    B --> D
    D -->|Posteriors| E[Entropy Controller]
    E -->|Haircut| F[Sizing Payload]
    F -->|Inertial Barrier| G[Behavioral Guard]
    G --> H[Output: Web UI & Discord]
```

## 📂 Repository Map
*   `src/engine/v11/` - Bayesian core implementation & state governance.
*   `src/models/` - Standardized V11 data contracts.
*   `src/store/` - CloudPersistenceBridge (Vercel Blob) & Schema-versioned SQLite.
*   `docs/audit/` - Formal architectural and performance audit records.

---
© 2026 QQQ Entropy Development Group.
