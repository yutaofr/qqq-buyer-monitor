# Architecture Design Document: QQQ Monitor (v13.4 Black-Box Governance)

This document describes the current production architecture: a PIT-safe macro Bayesian core, coupled with price-topology vetoes, execution-layer physical constraints, and forensic snapshots that backtests must replay as a black box.

---

## 1. System Philosophy: Orthogonal Reality, Information Honesty, Black-Box Governance

The current design is centered on three pillars:
1.  **Physical Orthogonality**: Ensuring each macro factor represents a distinct, non-redundant dimension of the global economy (Discount, Real Economy, Sentiment).
2.  **Information Honesty**: Acknowledging the inherent uncertainty in high-dimensional macro spaces. The system prioritizes **Shannon Entropy** as a first-class citizen to prevent "Spurious Confidence" caused by collinear factors.
3.  **Spec-to-Code Parity**: Historical replay must call the production `V11Conductor` directly. Research-only re-implementations are not part of the certified audit path.

## 2. Component Responsibility Matrix

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Inference** | `src/engine/v11/` | **The Brain**. Recursive Bayesian inference, production JIT GaussianNB training, topology-coupled likelihood penalties, and execution-layer physical constraints. |
| **Ingestion** | `src/collector/` | **The Sensors**. Multi-source data fetching (FRED, yf, Shiller) with strict **PIT (Point-in-Time) Lag Alignment**. |
| **Seeding** | `ProbabilitySeeder` | **Factor Engineering**. 10-factor orthogonal matrix generation with **Gram-Schmidt post-processing** for MOVE-Spread decoupling. |
| **Storage** | `src/store/` | **The Memory**. Managing local DNA (CSV), hydrated prior state (JSON), and Cloud sync (Vercel Blob). |
| **Forensics** | `snapshot_*.json` | **The Audit Trail**. Per-day runtime priors, penalties, feature vectors, quality audits, topology state, and final execution payload. |
| **Execution** | `BehavioralGuard` | **The Armor**. Entropy-aware bucket switching and T+1 settlement locks. |

---

## 3. Data Flow: The Orthogonal Bayesian Loop

The current loop keeps orthogonalization, but now also couples `QQQ` price topology into the posterior calculation before execution sizing.

```mermaid
graph TD
    A[Macro DNA: PIT-Compliant CSV] -->|JIT Training| B(GaussianNB Classifier)
    C[Prior State: JSON] -->|Recursive Input| D{Bayesian Core}
    E[Live Observation] -->|Standardized Vector| G[Gram-Schmidt Engine]
    G -->|Orthogonalized Evidence| D
    P[QQQ Price Topology] -->|Likelihood Penalty / Veto| D
    D -->|Posterior Probabilities| F[Entropy Controller]
    F -->|Entropy Haircut| H[Continuous Sizing Payload]
    H -->|Inertial Smoothing| I[Behavioral Guard]
    I -->|Final Signal + Forensics| J[Output: Web/Discord]
    J -->|T+0 Feedback| A
    J -->|State Update| C
```

---

## 4. Core Implementation Mandates (v12.0)

### 4.1 AC-6: PIT (Point-in-Time) Integrity
The engine enforces strict **Lag Alignment Protocols**. Backtests must use data as it was *initially released*, accounting for physical publication delays:
- **Financial Data**: T+1 Business Day lag.
- **Real Economy (Capex)**: Release Date + 30 BDay lag (to immune revision noise).
- **Earnings (Shiller EPS)**: Month-End + 30 BDay lag.

### 4.2 AC-8: The 10-Factor Orthogonal Matrix
Factors are organized into three non-overlapping layers:
1.  **Discount (贴现层)**: Real Yield, Treasury Realized Vol (MOVE proxy), Breakeven Accel.
2.  **Real Economy (实体层)**: Core Capex Momentum, Copper/Gold ROC, USD/JPY (Carry Trade).
3.  **Sentiment (情绪层)**: Credit Spread (Level/Pulse), Net Liquidity, ERP (TTM-based).

### 4.3 AC-10: Gram-Schmidt Orthogonalization Engine
To satisfy the GaussianNB assumption of conditional independence, the system performs an online **Gram-Schmidt** process. For example, `move_21d` is orthogonalized against `spread_21d` using an expanding-window regression, extracting the residual as the unique "Volatility" signal.

### 4.4 Information Honesty (Entropy Pricing)
As dimensions increase to 10, the probability space becomes sparser. v12.0 embraces higher **Shannon Entropy (H)** (0.15 - 0.40) as a sign of model honesty. The positioning rule remains:

`target_beta = raw_target_beta * exp(-H)`

### 4.5 Numerical Consistency (Standardized Scales)
All factors are normalized using **Expanding Z-scores** or **Rolling Z-scores** with a strict `clip=[-8, 8]` to prevent outliers from distorting the covariance matrix.

---

## 5. Persistence & Cloud Bridge (Stateless Resilience)
The system remains **Stateless** and CI/CD-native:
1. **Pull**: Sync PIT DNA and Prior State from Vercel Blob.
2. **Run**: Execute v12.0 inference with orthogonalized sensors.
3. **Push**: Update state and audit logs.

Runtime snapshots now include `runtime_priors`, `prior_details`, `price_topology`, `v13_4_diagnostics`, and final execution payload for post-run forensic analysis. Certified backtests must consume these artifacts rather than reproducing the logic independently.

---
© 2026 QQQ Entropy Architecture Group.
