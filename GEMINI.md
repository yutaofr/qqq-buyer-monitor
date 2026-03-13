# GEMINI.md - QQQ Buy-Signal Monitor (v5.0)

## Project Overview
`qqq-monitor` is a sophisticated market monitoring system designed to identify high-probability buy signals for the QQQ ETF. It employs a multi-tiered architecture that integrates macro-economic data, market sentiment, institutional flow proxies, and options market structure (Gamma and Put/Call walls).

### Core Architecture (The Tiered Logic)
- **Tier 0 (Macro/Circuit Breaker):** Monitors FRED credit spreads and Equity Risk Premium (ERP). Can force a "Circuit Breaker" silence if liquidity risks are too high.
- **Tier 1 (Sentiment & Adaptive Stats):** Uses VIX, Fear & Greed, Drawdowns, and Breadth. Employs a **Time-Decay Filter** to distinguish between fast "Panic" and slow "Grind" downswings.
- **Tier 1.5 (Flow & Institutional):** Analyzes FINRA Short Volume proxies and Net Liquidity to identify institutional capitulation and accumulation.
- **Tier 2 (Options Wall Confirmation):** A "Hard Veto" layer that checks if the price is below the **Put Wall** or in a **Negative Gamma** regime.

### Technology Stack
- **Language:** Python 3.12
- **Data Acquisition:** `yfinance` (price/options), FRED API (macro), Scrapers (Fear & Greed).
- **Analysis:** `pandas`, `numpy`, `scipy`.
- **Persistence:** SQLite (`data/signals.db`).
- **Containerization:** Docker & Docker Compose.
- **Quality Assurance:** `pytest`, `ruff` (linting).

---

## Building and Running
All operations **MUST** be performed via Docker to ensure environment consistency and comply with project mandates.

### 1. Setup
Create a `.env` file in the root directory:
```bash
FRED_API_KEY=your_key_here
```

### 2. Build the Project
```bash
docker-compose build
```

### 3. Run Real-time Monitoring
```bash
# Standard CLI report
docker-compose run --rm app python -m src.main

# JSON output for automation
docker-compose run --rm app python -m src.main --json

# View last 20 historical records
docker-compose run --rm app python -m src.main --history 20
```

### 4. Run Backtesting
```bash
docker-compose run --rm app python -m src.backtest
```

### 5. Run Tests
```bash
docker-compose run --rm test
```

---

## Development Conventions

### Coding Style & Linting
- Follow **PEP 8** standards.
- Use `ruff` for linting and formatting. 
- Target Python 3.12+ features (type hinting, `from __future__ import annotations`).
- Line length is configured to **100** characters.

### Testing Practices
- **Mandatory Testing:** All new logic (especially in `src/engine/`) must be accompanied by unit tests in `tests/unit/`.
- **Mocking:** Use `pytest-mock` to mock external API calls (yfinance, FRED).
- **Regression:** Run `docker-compose run --rm test` before any significant change to ensure no regressions in the v5.0 logic.

### Architectural Rules
- **Data Integrity:** All data fetching logic belongs in `src/collector/`. Never fetch data directly inside the engine tiers.
- **Model Consistency:** Use the `MarketData` model in `src/models/` to pass data between the collector and the engine.
- **Pure Logic:** Engine functions in `src/engine/` should ideally be "pure" or deterministic based on the provided `MarketData`, facilitating easier testing.
- **Persistence:** Signals must be persisted to the SQLite database via `src/store/db.py` to support historical Z-score calculations (120-day rolling window).

### Signal Output Levels
- `STRONG_BUY`: High confidence, multi-tier resonance.
- `TRIGGERED`: Standard buy signal with options confirmation.
- `WATCH`: Monitoring for convergence.
- `GREEDY`: Overbought/Extreme Greed signal (Profit taking).
- `NO_SIGNAL`: Neutral/Normal market state.
