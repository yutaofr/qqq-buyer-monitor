# QQQ Buy-Signal & Strategic Allocation Monitor (v6.4)

An institutional-grade market monitoring system for the QQQ ETF, designed for long-term sovereign wealth and pension fund allocation strategies. v6.4 introduces the **Personal Allocation Search** layer.

## 🚀 What's New in v6.4: Personal Allocation Search
Following the v6.3 strategic allocation layer, this version shifts focus from institutional mirroring to a **30% personal drawdown budget**:
- **State-Conditioned Candidate Search:** Dynamically scores allowed QQQ/QLD/Cash bands per `AllocationState`.
- **Daily T+0 Risk Rebalancing:** Separates weekly cash-flow deployment from daily risk alignment, preserving beta fidelity.
- **Personal Beta Audit (AC-4):** Implements returns-based realized beta tracking with a Mean Absolute Deviation of **0.0069** in the full backtest.
- **QLD Leverage Simulation:** Accurate modeling of ProShares Ultra QQQ (QLD) including SRD 4.2 compliant daily expense ratio drag.
- **30% MDD Budget (AC-5):** Hard-gates unsafe candidates and falls back to 100% cash when required.

## 📊 Performance & Resilience (v6.4 Backtest)
Based on full-cycle historical simulations (1999-2026):
- **MDD Improvement:** Personal allocation reduced Maximum Drawdown by **5.0% (absolute)** compared to pure QQQ DCA.
- **Defense Coverage:** Maintained defensive regimes (`CASH_FLIGHT` / `DELEVERAGE`) across the full sample, with hard-gated safe fallback behavior when needed.
- **Statistical Edge:** Average T+60 forward returns remain positive after tactical add signals.

## 🧭 Recommended Default Matrix
The v6.4 system uses the following default `QQQ:QLD:Cash` operating matrix, while still allowing the runtime selector to search within the SRD-approved band:

- `FAST_ACCUMULATE`: `4:4:2`
- `BASE_DCA`: `6:1:3`
- `SLOW_ACCUMULATE`: `6:0:4`
- `WATCH_DEFENSE`: `7:0:3`
- `DELEVERAGE`: `6:0:4`
- `CASH_FLIGHT`: `7:0:3` or `100% Cash` in hard-gate rejection

## 🛠 Core Tiers
1.  **Tier 0 (Macro Commander):** Monitors Credit Acceleration, Net Liquidity, and Funding Stress. Defines the **Structural Regime**.
2.  **Tier 1 (Tactical Sentiment):** VIX Z-Scores, Fear & Greed, and multi-factor valuation/price divergences.
3.  **Tier 2 (Market Structure):** Real-time Options Walls (Put/Call Walls) and Gamma Flip detection.
4.  **Strategic Layer:** Search the approved `QQQ:QLD:Cash` bands and execute daily atomic rebalancing.

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
- [SRD v6.4: Personal Allocation](docs/v6.4_personal_allocation_srd.md)
- [ADD v6.4: Personal Allocation Implementation](docs/v6.4_personal_allocation_add.md)
- [Allocator-Style Backtest Report (v6.4)](docs/backtest_report.md)
- [Architecture Design Document (v6.4)](docs/architecture.md)

---
*Disclaimer: This tool is for institutional simulation and monitoring purposes. Not individual investment advice.*
