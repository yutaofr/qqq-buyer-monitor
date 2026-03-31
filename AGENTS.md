# Repository Guidelines (v11 Bayesian Convergence)

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
- `pip install -e .[dev]`: install package and dev tools.
- `python -m src.main`: run the live Bayesian pipeline.
- `python -m src.backtest`: run the v11 performance audit and fidelity backtest.
- `pytest tests/unit/engine/v11 -q`: run core engine tests.
- `pytest tests/integration/engine/v11 -q`: run v11 workflow integration tests.
- `ruff check .`: lint the codebase.

## Coding Style & Naming Conventions
- **Target Python 3.12+**.
- **No Hard-coded Constants**: All decision parameters must be audit-derived (AC-0).
- **Causal Isolation**: No look-ahead bias in data seeding or inference.
- **Unit Stability**: All macro levels must be decimal-normalized (e.g. ERP 0.05, not 5.0).
- **Functional Logic**: Favor pure functions for engine cores to ensure testability.

## Testing Guidelines
- **Validation Before Finality**: No PR is merged without a green `v11_audit` in backtest.
- **Spec-to-Code Parity**: Code must strictly align with the `v11` Bayesian production baseline.
- **Numerical Integrity**: Maintain bit-identical parity between research and production outputs.

## Configuration & Data Notes
- `data/macro_historical_dump.csv`: Canonical SSoT for macro history.
- `data/v11_poc_phase1_results.csv`: Ground truth regimes for model training.
- `src/engine/v11/resources/regime_audit.json`: Audit-derived base betas and sharpe ratios.
