# Repository Guidelines (v11.5 Bayesian Probabilistic Convergence)

## Project Structure & Module Organization
Core application code lives in `src/`.
- `src/engine/v11/`: The sole decision engine. Probabilistic Bayesian inference.
- `src/collector/`: Data ingestion from FRED, yfinance, etc.
- `src/models/`: Shared domain types (CurrentPortfolioState, TargetAllocationState, SignalResult).
- `src/store/`: Persistence (SQLite, Cloud/Vercel Blob).
- `src/output/`: CLI, JSON reports, and Discord notifications.
- `src/main.py`: Production entry point for live daily runs.
- `src/backtest.py`: Unified entry point for backtesting and fidelity audits.

## Build, Test, and Development Commands
**MANDATE**: Never run `npm`, `pip`, `pytest`, or `python` directly on the host. Use Docker.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.main`: Live Bayesian pipeline.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.backtest`: Performance audit.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] pytest tests/unit/engine/v11 -q`: Unit tests.
- `docker-compose up --build`: Full environment validation.

## Coding Style & Naming Conventions (v11.5 Compliance)
- **Target Python 3.12+**.
- **No Hard-coded Constants**: All decision parameters must be audit-derived (AC-0).
- **Causal Isolation**: No look-ahead bias in data seeding or inference (AC-1).
- **Unit Stability**: All macro levels must be decimal-normalized (e.g. ERP 0.05, not 5.0) (AC-2).
- **Intent-Action Separation (AC-4)**: Signal interfaces MUST explicitly return both `raw_target_beta` (Bayesian expectation) and `target_beta` (Inertial-mapped execution target).
- **Smart Priming (AC-5)**: Cold-start (T0) logic MUST align with the first day's raw expectation to prevent default lag.
- **Functional Logic**: Favor pure functions for engine cores to ensure testability.

## Testing Guidelines
- **Validation Before Finality**: No PR is merged without a green `v11_audit` in backtest.
- **Spec-to-Code Parity**: Code must strictly align with `docs/V11_5_EXPERT_SPEC.md`.
- **Numerical Integrity**: Maintain bit-identical parity between research and production outputs.

## Configuration & Data SSoT (Single Source of Truth)
- **Expert Spec**: `docs/V11_5_EXPERT_SPEC.md` & `docs/V11_5_USER_PHILOSOPHY.md`.
- **Macro History**: `data/macro_historical_dump.csv`.
- **Regime Labels**: `data/v11_poc_phase1_results.csv`.
- **Audit Resources**: `src/engine/v11/resources/regime_audit.json`.
