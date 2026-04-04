# v12.0 Project Structure & Module Roles

> **The "Map" - File & Folder Breakdown**

## 1. Directory Structure
- `src/engine/v11/`: Bayesian Decision Engine (Orthogonal Inference - Implementation of v12 Architecture).
- `src/engine/v13/`: Execution Overlay & Behavioral Guard extensions.
- `src/collector/`: Sensor Layer (PIT Data Ingestion).
- `src/models/`: Domain Contracts (Portfolio & Signal Types).
- `src/store/`: Persistence & Cloud Bridge (Vercel Blob Sync).
- `src/output/`: Web & Discord Export (Interpretation Layer).
- `src/main.py`: Production Pipeline Entry Point.
- `src/backtest.py`: Performance Fidelity Audit Entry Point.

## 2. Resources (SSoT Registry)
- `src/engine/v11/resources/regime_audit.json`: Decision parameters.
- `src/engine/v11/resources/v13_4_weights_registry.json`: Factor weights and Tau calibration.
- `data/macro_historical_dump.csv`: PIT-Compliant Factor DNA.
- `docs/versions/v12/V12_ORTHOGONAL_FACTOR_SPEC.md`: Architecture Spec.
