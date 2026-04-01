# Repository Guidelines (v12.0 Orthogonal-Core)

## Project Structure & Module Organization
Core application code lives in `src/`.
- `src/engine/v11/`: The decision engine. **v12.0 Bayesian Orthogonal Inference**.
- `src/collector/`: Data ingestion from FRED, yf, **Shiller TTM EPS**.
- `src/models/`: Shared domain types (PortfolioState, SignalResult).
- `src/store/`: Persistence (CSV DNA, JSON Prior, Vercel Blob).
- `src/output/`: Web UI, JSON reports, Discord notifications.
- `src/main.py`: Production entry point for **v12.0 Orthogonal Inferencing**.
- `src/backtest.py`: Unified entry point for **PIT-Compliant Fidelity Audits**.

## Build, Test, and Development Commands
**MANDATE**: Never run `npm`, `pip`, `pytest`, or `python` directly on the host. Use Docker.
- `docker-compose up --build`: Full environment validation.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.main`: Live v12.0 pipeline.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.backtest --evaluation-start 2010-01-01`: PIT-Compliant Performance audit.
- `docker run --rm -v $(pwd):/app -w /app [IMAGE] pytest tests/unit/engine/v11 -q`: Engine unit tests.

## Coding Style & Naming Conventions (v12.0 Compliance)
- **Target Python 3.12+**.
- **Orthogonal Reality (AC-8)**: 10 factors organized into 3 non-overlapping layers (Discount, Real Economy, Sentiment).
- **PIT (Point-in-Time) Integrity (AC-6)**: Strict **Lag Alignment Protocol**. Backtests must use data as initially released.
- **Gram-Schmidt Engine (AC-10)**: Collinear factors (MOVE/Spread) must be orthogonalized using expanding-window residuals.
- **Shannon Entropy (AC-7)**: Risk is priced via Shannon Entropy. High H = Low Beta Haircut.
- **Intent-Action Separation (AC-4)**: Signals MUST return both `raw_target_beta` (inference) and `target_beta` (post-entropy & inertial).
- **Numerical Integrity (AC-2)**: All macro levels MUST be decimal-normalized (e.g. ERP 0.05).
- **No Hard-coded Constants (AC-0)**: All parameters derived from `regime_audit.json`.

## Testing & Audit Guidelines
- **Validation Before Finality**: No PR is merged without a green **Gate 3 Audit** (Extreme Regime Recall >= 90%).
- **Spec-to-Code Parity**: Code must strictly align with `docs/V12_ORTHOGONAL_FACTOR_SPEC.md`.
- **Numerical Integrity**: Maintain bit-identical parity between PIT-research and production outputs.

## Configuration & Data SSoT (Single Source of Truth)
- **Expert Spec**: `docs/V12_ORTHOGONAL_FACTOR_SPEC.md` & `docs/core/PRD.md`.
- **Macro History**: `data/macro_historical_dump.csv` (10-Factor Canonical Schema).
- **Audit Resources**: `src/engine/v11/resources/regime_audit.json`.
