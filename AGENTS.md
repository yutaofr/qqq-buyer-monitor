# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `src/`. Use `src/engine/` for decision logic, `src/collector/` for data ingestion, `src/models/` for shared domain types, `src/store/` for persistence, and `src/output/` for CLI/report rendering. Entry points are `src/main.py` for live recommendations and `src/backtest.py` for historical runs. Tests are split into `tests/unit/` and `tests/integration/`. Research notes, architecture docs, implementation plans, and archived baseline specs live under `docs/`; helper scripts belong in `scripts/`; persistent runtime data is stored in `data/`. Generated charts are written to `artifacts/` and mirrored in `docs/images/` when they are part of the published report.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create a local Python environment.
- `pip install -e .[dev]`: install the package plus pytest and Ruff.
- `python -m src.main`: run the live recommendation pipeline locally.
- `python -m src.backtest`: run the historical backtest.
- `python scripts/run_signal_acceptance_report.py`: regenerate the beta and deployment alignment report.
- `python scripts/plot_dca_performance.py`: regenerate `artifacts/dca_timing_performance.png` for the current DCA timing chart.
- `pytest tests/unit -q`: run the fast unit suite.
- `pytest tests/integration -q`: run end-to-end and pipeline checks.
- `ruff check src tests`: lint imports, upgrades, and common bug patterns.
- `docker compose run --rm app|test|backtest`: use the containerized workflow documented in the README.

## Coding Style & Naming Conventions
Target Python 3.12+ and keep lines within the Ruff limit of 100 characters. Follow standard Python conventions: 4-space indentation, `snake_case` for functions/modules, `PascalCase` for classes, and descriptive constant names in `UPPER_SNAKE_CASE`. Keep logic deterministic and side effects isolated near collectors, storage, and CLI/output layers. The current product boundary is the v8.1 linear pipeline: stock beta recommendation plus incremental deployment timing.

## Testing Guidelines
Pytest discovers files named `test_*.py`. Mirror the source layout when adding tests, and prefer unit tests for pure engine logic plus integration tests for full pipeline behavior. Add regression coverage for any change in recommendation semantics, persistence behavior, or backtest math before merging.

## Commit & Pull Request Guidelines
Recent history uses conventional prefixes such as `fix:`, `refactor:`, and scoped forms like `fix(engine):`. Keep commit subjects imperative and specific. Pull requests should summarize the behavioral change, list the verification commands run, link relevant docs or issues, and include screenshots only when CLI/report output changes materially.

## Configuration & Data Notes
Use `.env` for secrets such as `FRED_API_KEY`; do not commit credentials or generated databases. Treat files in `data/` and `artifacts/` as runtime outputs unless a task explicitly requires updating checked-in fixtures.
