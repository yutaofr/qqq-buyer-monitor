# v12.0 Project Structure & Module Roles

> **The "Map" - File & Folder Breakdown**

## 1. Directory Structure
- `src/engine/v12/`: Bayesian Decision Engine (Orthogonal Inference).
- `src/collector/`: Sensor Layer (PIT Data Ingestion).
- `src/models/`: Domain Contracts (Portfolio & Signal Types).
- `src/store/`: Persistence & Cloud Bridge (Vercel Blob Sync).
- `src/output/`: Web & Discord Export (Interpretation Layer).
- `src/main.py`: Production Pipeline Entry Point.
- `src/backtest.py`: Performance Fidelity Audit Entry Point.

## 2. Resources (SSoT Registry)
- `src/engine/v12/resources/regime_audit.json`: Decision parameters.
- `data/macro_historical_dump.csv`: PIT-Compliant Factor DNA.
- `docs/versions/v12/V12_ORTHOGONAL_FACTOR_SPEC.md`: Architecture Spec.
