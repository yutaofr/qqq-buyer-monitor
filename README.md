# QQQ Buy-Signal & Strategic Allocation Monitor (v8.1)

A production-grade QQQ/QLD/Cash recommendation engine built around the **v8.1 Linear Pipeline Architecture**.

The system now has a strict boundary:
- It recommends **target portfolio beta**.
- It recommends **incremental cash deployment pace**.
- It does **not** calculate dollar amounts.
- It does **not** manage a wallet or execute trades.

## v8.1 Architecture

### Tier-0 Macro Regime
`assess_structural_regime()` classifies the structural regime from credit spreads and ERP:
`EUPHORIC | NEUTRAL | RICH_TIGHTENING | TRANSITION_STRESS | CRISIS`.

Tier-0 is the top-level constraint:
- Hard constraint on the **Risk Controller** beta ceiling.
- Soft constraint on the **Deployment Controller** pace.

### Risk Controller
Determines the allowed exposure ceiling from **Class A macro data** plus the Tier-0 regime.
Outputs `RiskDecision` with:
- `risk_state`
- `target_exposure_ceiling`
- `target_cash_floor`
- `tier0_applied`

Key semantics:
- `EUPHORIC` unlocks `RISK_ON` and allows `>1.0` target beta when the registry has compliant candidates.
- `CRISIS` and hard drawdown breaches map to `RISK_EXIT`, but the stock beta floor remains `0.5`.
- If a scoped risk-state registry slice is misconfigured, runtime falls back to the global `0.5 beta` floor candidate instead of silently collapsing to `0.0`.

### Deployment Controller
Determines how to deploy **new incoming cash** under Tier-0 soft ceilings.
Outputs one of:
`DEPLOY_SLOW | DEPLOY_BASE | DEPLOY_FAST | DEPLOY_PAUSE`.

Key v8.1 semantics:
- `RICH_TIGHTENING` slows default deployment but still allows left-side entry when capitulation is strong.
- `CRISIS` fully pauses incremental deployment.

### Beta Recommendation
`build_beta_recommendation()` replaces the old amount-based execution surface.

The output is recommendation-only:
- `target_beta`
- recommended `QQQ / QLD / Cash`
- `should_adjust`
- `adjustment_reason`

## Key Changes vs v7.0
- **Linear pipeline:** `Tier-0 → Risk → Search → Recommend`
- **No amount output:** removed `build_execution_actions()` and all dollar deployment calculations
- **Tier-0 hard/soft constraints:** structural regime now directly shapes both stock beta and cash deployment pace
- **Pure math candidate search:** v8 selection respects `max_beta_ceiling` and drawdown budget before recommendation

## 📊 Research Backtest Snapshot
The legacy `--mode portfolio` path is retained as a mixed research tool, not as the production acceptance gate.

Latest verified real-history runs:
- `python -m src.backtest --mode portfolio`
  - Tactical Max Drawdown: `-28.2%`
  - Baseline DCA Max Drawdown: `-35.1%`
  - MDD Improvement: `6.9%` absolute improvement
  - Realized Beta: `0.19`
  - Turnover Ratio: `119.58`
  - Left-side windows preserved: `RICH_TIGHTENING left-side windows = 647`
  - CRISIS deployment breaches: `0`
- `python scripts/run_signal_acceptance_report.py`
  - Target beta alignment: `MAE=0.0559`, `RMSE=0.1688`, `within_tol=88.97%`
  - Deployment alignment: `exact=99.96%`, `within_one_step=99.99%`

Production acceptance should instead be based on the two signal-alignment audits below.

## 🧭 Certified Candidate Reference (v8.1)
v8.1 no longer uses the old `AllocationState` operating matrix at runtime. It selects from the certified registry:

- `RISK_NEUTRAL`: `neutral-base-001` (`70/10/20`, beta `0.90`) or `neutral-low-drift` (`80/5/15`, beta `0.90`)
- `RISK_REDUCED`: `reduced-tight-001` (`80/0/20`, beta `0.80`) or `reduced-base-001` (`50/0/50`, beta `0.50`)
- `RISK_DEFENSE`: `defense-001` (`50/0/50`, beta `0.50`) or `defense-002` (`50/15/35`, beta `0.80`)
- `RISK_EXIT`: `exit-floor-001` (`50/0/50`, beta `0.50`)
- `RISK_ON`: `euphoric-base-001` (`60/25/15`, beta `1.10`) or `euphoric-max-001` (`80/20/0`, beta `1.20`)

## 🛠 Core Tiers
1.  **Tier 0 (Macro Commander):** Monitors Credit Acceleration, Net Liquidity, and Funding Stress. Defines the **Structural Regime**.
2.  **Tier 1 (Tactical Sentiment):** VIX Z-Scores, Fear & Greed, and multi-factor valuation/price divergences.
3.  **Tier 2 (Market Structure):** Real-time Options Walls (Put/Call Walls) and Gamma Flip detection.
4.  **Strategic Layer:** Load certified candidates, respect the beta ceiling, and emit recommendation-only outputs.

## 🧭 Decision Architecture (Historical v6.4 Appendix)

The current production architecture is the v8.1 linear pipeline documented above. The `docs/v8.0_linear_pipeline_*` files are archived baseline references for the v8.0/v8.1 redesign.
The diagram below is retained only as legacy background for the pre-v8 multi-tier state-machine implementation.

The system operates as a **Multi-Tiered Deterministic State Machine**, where high-order macroeconomic "Structural" states act as constraints on lower-order "Tactical" states, eventually resolving into an optimized asset allocation through a filtered search space.

```mermaid
flowchart TD
    %% INPUT LAYER
    subgraph Raw_Inputs [Indicator & Data Layer]
        direction LR
        subgraph Macro_Data [Macro & Liquidity]
            WALCL[Fed Assets: WALCL]
            TGA[Treasury: WDTGAL]
            RRP[Reverse Repo: RRPONTSYD]
            CS[Credit Spread: BAMLH0A0HYM2]
            RY[Real Yield: DFII10]
            FPE[Forward P/E Ratio]
        end
        subgraph Market_Data [Price & Sentiment]
            PX[QQQ Price / OHLCV]
            VIX[VIX Level / Z-Score]
            FG[Fear & Greed Index]
            BR[A/D Breadth Ratio]
            MA[MA50 & MA200 SMAs]
            MFI[Money Flow Index - MFI]
            RSI[Relative Strength Index - RSI]
        end
        subgraph Options_Data [Market Structure]
            OI[Options Open Interest]
            G_FLIP[Gamma Flip Level]
            PW[Put Wall Strike]
            CW[Call Wall Strike]
            POC[Volume Point of Control - POC]
        end
        subgraph Fundamental_Lead [Fundamental Lead]
            ERB[Earnings Revision Breadth]
            FCF[FCF Yield]
        end
    end

    %% TIER 0: MACRO COMMANDER
    subgraph Tier0 [Tier 0: Structural Regime]
        direction TB
        WALCL & TGA & RRP --> LIQ_ROC[Liquidity Rate of Change]
        CS --> CS_ACCEL[Credit Spread Acceleration]
        FPE & RY --> ERP[Equity Risk Premium]
        FS[Funding Stress] --> BYPASS{Defensive Bypass?}
        
        CS_ACCEL & LIQ_ROC --> BYPASS
        BYPASS -- High Stress --> L3[L3: CASH_FLIGHT]
        BYPASS -- Med Stress --> L2[L2: DELEVERAGE]
        BYPASS -- Low Stress --> L1[L1: WATCH_DEFENSE]
        
        CS & ERP --> REGIME[Structural Regime Decision]
        REGIME --> S_STATES["CRISIS | TRANSITION_STRESS | NEUTRAL | EUPHORIC"]
    end

    %% TIER 1: TACTICAL ENGINE
    subgraph Tier1 [Tier 1: Tactical Scoring]
        direction TB
        PX & MA --> S1[52w Drawdown & MA200 Dev]
        VIX & FG & BR --> S2[Sentiment & Breadth Gradient]
        
        %% Divergence Sub-Engine
        PX & MFI & RSI & ERB --> DIV[Divergence Sub-Engine]
        DIV --> DIV_BONUS[Bonus Score: +5 to +20]
        
        %% Valuation Sub-Engine
        FPE & FCF --> VAL[Valuation Sub-Engine]
        VAL --> VAL_ADJ[Adjustment: -10 to +15]

        S1 & S2 & DIV_BONUS & VAL_ADJ --> T1_SCORE[Tier 1 Score: 0-100]
        
        PX --> VELOCITY["Descent Velocity: PANIC | GRIND | CALM"]
        T1_SCORE & VELOCITY --> TACTICAL_STATE["Tactical: PANIC | CAPITULATION | STRESS | CALM"]
    end

    %% TIER 2: MARKET STRUCTURE
    subgraph Tier2 [Tier 2: Confirmation Layer]
        PW & CW & POC --> WALLS[Support Confirmed / Broken / POC Bonus]
        G_FLIP & PX --> GAMMA[Gamma Positive / Negative]
        WALLS & GAMMA --> T2_ADJ[Tier 2 Adjustment: -30 to +15]
    end

    %% AGGREGATION & SEARCH
    subgraph Strategy [v6.4 Personal Allocation Search]
        S_STATES & TACTICAL_STATE --> ALLOC_STATE[Allocation State]
        ALLOC_STATE --> CANDIDATES[SRD-6.4 QQQ:QLD:Cash Bands]
        
        CANDIDATES --> BACKTEST[Live Path Mini-Backtest]
        PX --> BACKTEST
        
        BACKTEST --> AC5_GATE{AC-5: MDD < 30%?}
        AC5_GATE -- NO --> SAFE_FALLBACK["Global Safe: 100% Cash"]
        AC5_GATE -- YES --> RANKING["Ranking: CAGR > MDD > Beta Fidelity"]
    end

    %% FINAL EXECUTION
    RANKING --> FINAL["Final Decision: QQQ : QLD : Cash"]
    L3 & L2 & L1 --> FINAL
    SAFE_FALLBACK --> FINAL
    T2_ADJ --> FINAL
```

### Key Architectural Transitions
1.  **Defensive Bypass (The Kill Switch):** Before any logical processing, the system checks for **Credit Acceleration** (HY OAS velocity), **Liquidity Drains** (Fed Assets - TGA - RRP), and **Funding Stress**. If high-velocity stress is detected, it enters `CASH_FLIGHT` or `DELEVERAGE` immediately.
2.  **Structural Regime (The Macro Commander):** Credit Spreads and **Equity Risk Premium (ERP)** define the structural regime. In the current research build, historical Tier-0 is primarily driven by canonical credit-spread history, with ERP used when available. A `CRISIS` state (Spread > 650bps or ERP < 1.0%) forces risk containment regardless of tactical indicators.
3.  **Tactical State (The Sentiment Filter):** Combines standard metrics with **Divergence (RSI/MFI/ERB)** and **Valuation (PE/FCF)** sub-engines to distinguish between a "Grind Down" and a "Panic."
4.  **v6.4 Selection Engine (The Personal Layer):** Performs a real-time **Candidate Scoring** mechanism using mini-backtests. Any allocation that has historically exceeded a **30% Drawdown (AC-5)** is discarded. Among survivors, it selects for the highest **CAGR** while ensuring **Beta Fidelity (AC-4)**.

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

## Signal Audit Workflow

The production system has two independent decision surfaces and they should be audited separately:

1. `target_beta`: stock of assets risk-budget recommendation
2. `deployment_state`: incremental cash entry timing and pace

Use an expectation matrix CSV with a `date` column plus one or both of:
- `expected_target_beta`
- `expected_deployment_state`

Optional runtime-state inputs may also be supplied in the same file. This allows state-conditioned expectation surfaces instead of naive date-only labels:
- `rolling_drawdown`
- `available_new_cash`
- `erp`
- `capitulation_score`
- `tactical_stress_score`

Run the audits:

```bash
# Audit both decision surfaces against an expected signal matrix
python -m src.backtest --mode both --expectations data/expected_signals.csv

# Audit only target-beta alignment
python -m src.backtest --mode beta --expectations data/expected_beta.csv

# Audit only deployment alignment
python -m src.backtest --mode deployment --expectations data/expected_deployment.csv
```

The workflow prints canonical macro coverage and expectation-matrix coverage before the audit summaries.

Acceptance audits should use the canonical research macro dataset. Synthetic `dev-fixture` macro data is blocked by default and only allowed with `--allow-synthetic-macro` for smoke tests. The legacy `--mode portfolio` path remains available for research, but production acceptance should be based on the two signal-alignment audits above.

For a fully reproducible real-history acceptance run, build the expectation matrix from raw market conditions and score both decision surfaces in one step:

```bash
python scripts/run_signal_acceptance_report.py \
  --cache-path data/qqq_history_cache.csv \
  --macro-path data/macro_historical_dump.csv \
  --registry-path data/candidate_registry_v7.json \
  --save-dir /tmp/qqq-monitor-acceptance
```

The script:
- builds a realistic expectation matrix from actual market drawdown, credit spread, credit acceleration, liquidity, and funding stress
- audits `target_beta` and `deployment_state` against that matrix
- asserts the production envelope stays within `0.5 <= beta <= 1.2`
- can save the expectation matrix, joined daily alignment, and JSON summary for review

## 📜 Documentation
- [SRD v8.0 baseline: Linear Pipeline](docs/v8.0_linear_pipeline_srd.md)
- [ADD v8.0 baseline: Implementation Design](docs/v8.0_linear_pipeline_add.md)
- [SDT v8.0 baseline: Test Design](docs/v8.0_linear_pipeline_sdt.md)
- [Architecture Review: SRD vs ADD](docs/v8_architecture_review.md)
- [Allocator-Style Backtest Report](docs/backtest_report.md)

---
*Disclaimer: This tool is for institutional simulation and monitoring purposes. Not individual investment advice.*
