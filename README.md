# QQQ Buy-Signal & Strategic Allocation Monitor (v6.3)

An institutional-grade market monitoring system for the QQQ ETF, designed for long-term sovereign wealth and pension fund allocation strategies. v6.3 introduces the **Strategic TAA Mirroring** layer.

## 🚀 What's New in v6.3: Strategic Asset Allocation
Following the v6.2 credit cycle pivot, this version shifts focus from signal generation to **Active Portfolio Risk Management**:
- **Multi-Asset TAA Mirroring:** Dynamically rebalances between Reality (Cash/QQQ/QLD) and Ideal (TAA Matrix) states.
- **Daily T+0 Risk Rebalancing:** Separates weekly cash-flow (DCA) from daily risk alignment, ensuring strict Beta fidelity.
- **Institutional Beta Audit (AC-4):** Implements returns-based realized beta tracking with a Mean Absolute Deviation of **0.0020**, exceeding institutional standards.
- **QLD Leverage Simulation:** Accurate modeling of ProShares Ultra QQQ (QLD) including SRD 4.2 compliant daily expense ratio drag.

## 📊 Performance & Resilience (v6.3 Backtest)
Based on full-cycle historical simulations (1999-2026):
- **MDD Improvement:** Tactical TAA reduced Maximum Drawdown by **5.0% (absolute)** compared to pure QQQ DCA, even when including leveraged assets.
- **Defense Coverage:** Maintained defensive regimes (`CASH_FLIGHT` / `DELEVERAGE`) for **241 weeks** across 27 years, successfully bypassing major crash cores.
- **Statistical Edge:** Average T+60 forward returns of **4.1%** following tactical add signals.

## 🛠 Core Tiers
1.  **Tier 0 (Macro Commander):** Monitors Credit Acceleration, Net Liquidity, and Funding Stress. Defines the **Structural Regime**.
2.  **Tier 1 (Tactical Sentiment):** VIX Z-Scores, Fear & Greed, and multi-factor valuation/price divergences.
3.  **Tier 2 (Market Structure):** Real-time Options Walls (Put/Call Walls) and Gamma Flip detection.
4.  **Strategic Layer:** Map states to TAA Matrix (Cash/QQQ/QLD) and execute daily atomic rebalancing.

## 📦 Getting Started

### 1. Setup
```bash
cp .env.example .env # Add your FRED_API_KEY
docker-compose build
```

### 2. Live Signal & Rebalance Audit
```bash
# Get the latest signal, TAA mirroring guidance, and Beta Audit
docker-compose run --rm app
```

### 3. Institutional Stress & Fidelity Testing
```bash
# Run multi-scenario stress tests with AC-4 Beta Fidelity reports
docker-compose run --rm backtest python scripts/stress_test_runner.py
```

## 📜 Documentation
- [SRD v6.3: Strategic Asset Allocation](docs/v6.3_strategic_allocation_srd.md)
- [ADD v6.3: TAA Mirroring Architecture](docs/v6.3_strategic_allocation_add.md)
- [Full Backtest Report (1999-2026)](docs/v6.3_full_backtest_report.md)
- [Institutional Stress Test Report](docs/v6.3_stress_test_report.md)

---
*Disclaimer: This tool is for institutional simulation and monitoring purposes. Not individual investment advice.*
