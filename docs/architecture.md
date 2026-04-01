# Architecture Design Document: QQQ Monitor (v11.5 Bayesian-Core)

This document details the **V11.5 Bayesian Probabilistic Architecture**, which represents the system's evolution from threshold-based logic to a unified probabilistic inference engine.

---

## 1. System Philosophy: Probabilistic Survival
The core design shifts responsibility from human-defined rules ("If X then Y") to **Evidence-Based Inference**. Risk is managed by quantifying uncertainty through **Shannon Entropy**.

## 2. Component Responsibility Matrix

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Inference** | `src/engine/v11/` | **The Brain**. Recursive Bayesian inference, entropy pricing, JIT GaussianNB training, and coefficient validation. |
| **Ingestion** | `src/collector/` | **The Sensors**. Multi-source data fetching (FRED, yf) with fail-soft defaults and explicit provenance for degraded proxy inputs. |
| **Seeding** | `ProbabilitySeeder` | **Feature Engineering**. Deterministic causal normalization of curated macro factors with no fixed decision thresholds and a hashed feature-DNA contract. |
| **Storage** | `src/store/` | **The Memory**. Managing local DNA (CSV), Prior state (JSON), and Cloud sync (Vercel Blob). |
| **Execution** | `BehavioralGuard` | **The Armor**. Enforcing entropy-aware bucket switching and T+1 settlement locks with topology-derived barriers. |
| **Models** | `src/models/` | **Data Contracts**. Unified `SignalResult` and `PortfolioState`. |

---

## 3. Data Flow: The Bayesian Loop

The system operates as a **Recursive Feedback Loop**, enabling the model to "evolve" with every daily run.

```mermaid
graph TD
    A[Macro DNA: CSV] -->|JIT Training| B(GaussianNB Classifier)
    C[Prior State: JSON] -->|Recursive Input| D{Bayesian Core}
    E[Live Observation] -->|Standardized Vector| D
    D -->|Posterior Probabilities| F[Entropy Controller]
    F -->|Entropy Haircut| G[Continuous Sizing Payload]
    G -->|Inertial Smoothing + Bucket Evidence| H[Behavioral Guard]
    H -->|Final Signal| I[Output: status.json / Discord]
    I -->|T+0 Feedback| A
    I -->|State Update| C
```

---

## 4. Core Implementation Mandates

### 4.1 AC-1: Causal Isolation
The engine enforces strict temporal boundaries. Inference for date $T$ is only exposed to DNA data `< T` for model fitting, while the date-$T$ observation is used only as evidence. This is audited via `src/backtest.py` which now performs a deterministic walk-forward re-fit for every evaluation day.

### 4.2 AC-2: Numerical Integrity (Decimal Parity)
To prevent "Distribution Drift", all macro inputs are standardized to **decimal units** (e.g., ERP of 5.0% is represented as `0.05`). This ensures the KDE likelihood clusters remain stable across research and production environments.

### 4.3 Uncertainty-Aware Positioning (Entropy Haircut)
Risk is not binary. The system calculates the **Shannon Entropy ($H$)** of the posterior distribution:
- **Low Entropy**: High confidence; exposure stays close to the posterior-weighted raw beta.
- **High Entropy**: Model doubt; exposure is multiplicatively reduced by a threshold-free entropy factor.

The active rule is:

`target_beta = raw_target_beta * exp(-H)`

### 4.4 JIT Model Integrity
Every live or audit `GaussianNB` fit must pass a deterministic integrity contract before inference:
- finite `theta_`
- strictly positive finite `var_`
- positive normalized `class_prior_`
- class coverage aligned with the supplied regime DNA

### 4.5 Degraded-Source Conservatism
Runtime data provenance now affects effective uncertainty:
- canonical direct observations keep posterior entropy unchanged
- degraded proxy observations reduce `quality_score`
- reduced `quality_score` raises effective entropy before beta pricing and state transitions

This preserves deterministic behavior while preventing proxy-fed observations from masquerading as canonical DNA.

---

## 5. Persistence & Cloud Bridge (Stateless Resilience)
The system is designed for **Stateless Execution** (e.g., GitHub Actions):
1. **Pull**: Retrieve DB, DNA, and Prior State from Vercel Blob. Cold-start object misses may fall back to checked-in canonical seeds, but non-404 storage failures abort the run.
2. **Run**: Execute JIT inference and update local files.
3. **Push**: Upload updated state back to Vercel Blob.

Namespace isolation (e.g., `prod/`, `staging/`) is enforced to prevent development runs from contaminating production memory.
Canonical DNA is mandatory; synthetic bootstrap is not part of the production path.

---
© 2026 QQQ Entropy Architecture Group.
