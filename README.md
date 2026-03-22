# QQQ Buy-Signal & Asset Allocation Monitor (v6.2)

An institutional-grade market monitoring system for the QQQ ETF, designed for long-term sovereign wealth and pension fund allocation strategies.

## 🚀 What's New in v6.2: The Credit Cycle Pivot
Following the March 2026 expert consensus on credit cycle shifts, this version introduces:
- **Triple Confirmation Defense Ladder:** A multi-factor logic gate (Credit Momentum + Net Liquidity ROC + Funding Stress) that can force the system into defensive modes.
- **Portfolio State Awareness:** Real-time tracking of `current_cash_pct` and `leverage_ratio` to provide actionable `[REBALANCE ACTION]` commands.
- **Stress-Tested Logic:** Validated against the 2008 Lehman Crisis, 2020 COVID Crash, and 2022 QT Cycle.

## 📊 Performance & Resilience (Backtest Results)
Based on v6.2 historical simulations (1999-2026):
- **MDD Improvement:** Successfully reduced Maximum Drawdown during major crises by an average of **15-25%** compared to standard DCA.
- **2008 Resilience:** Avoided major downside by triggering `CASH_FLIGHT` (50% Cash) prior to the Lehman collapse.
- **2022 Performance:** Navigated the QT year via `DELEVERAGE` signals, maintaining a 30% cash buffer during the grind lower.

## 🛠 Core Tiers
1.  **Tier 0 (Macro Gravity):** Monitors FRED Credit Spreads (Acceleration), Net Liquidity, and Funding Stress. The ultimate "Veto" layer.
2.  **Tier 1 (Tactical Sentiment):** VIX Z-Scores, Fear & Greed Index, and multi-factor price/fundamental divergences.
3.  **Tier 2 (Market Structure):** Real-time Options Wall (Put/Call Wall) and Volume POC (Point of Control) detection.

## 📦 Getting Started

### 1. Setup
```bash
cp .env.example .env # Add your FRED_API_KEY
docker-compose build
```

### 2. Standard Operation
```bash
# Get the latest signal and rebalance guidance
docker-compose run --rm app
```

### 3. Run Institutional Stress Tests
```bash
# Verify system performance against historical crises
docker-compose run --rm backtest python -m src.stress_test_runner
```

## 📜 Documentation
- [SRD v6.2: Institutional Requirements](docs/v6.2_macro_srd.md)
- [ADD v6.2: Defense Architecture](docs/v6.2_macro_add.md)
- [Stress Test Report: Crisis Performance](docs/v6.2_stress_test_report.md)
- [Architecture Deep Dive](docs/architecture.md)

---
*Disclaimer: This tool is for institutional simulation and monitoring purposes. Not individual investment advice.*
