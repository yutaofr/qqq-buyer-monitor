# Architecture Design Document: QQQ Monitor (v5.0)

This document provides a technical deep-dive into the internal architecture, data contracts, and design patterns of the `qqq-monitor` system.

---

## 1. System Components & Responsibility

The system follows a classic **Pipes and Filters** architecture, where data is collected, transformed, and aggregated through a series of specialized engines.

| Component | Responsibility |
| :--- | :--- |
| **Collector Layer** (`src/collector/`) | Fetching raw data from `yfinance`, `FRED`, and `CNN`. Handles retries and basic parsing. |
| **Model Layer** (`src/models/`) | Defines the "Data Contract" between collectors and engines (`MarketData`, `SignalResult`). |
| **Engine Layer** (`src/engine/`) | The core logic. Tier-0 (Macro), Tier-1 (Sentiment), Tier-1.5 (Divergence), and Tier-2 (Options). |
| **Store Layer** (`src/store/`) | Persistence using SQLite. Manages historical time-series for Z-score and Divergence calculations. |
| **Output Layer** (`src/output/`) | Formatting results for CLI (Human) or JSON (Machine/API). |

---

## 2. Data Flow & Execution Sequence

```mermaid
sequenceDiagram
    participant Main as main.py
    participant Col as Collector Layer
    participant DB as SQLite Store
    participant T0 as Tier-0 (Macro)
    participant T1 as Tier-1 (Sentiment)
    participant T2 as Tier-2 (Options)
    participant Agg as Aggregator

    Main->>DB: Load History (120 days)
    Main->>DB: Load Latest Macro State (Cache)
    Main->>Col: Fetch Price, VIX, F&G, Options, Macro
    Col-->>Main: Raw Data Pack
    Main->>Main: Calculate Z-Scores & Adaptive Stats
    Main->>T0: check_macro_regime (Credit Spread, ERP)
    T0-->>Main: Regime Status (Crisis/Normal/Defense/Aggressive)
    Main->>T1: calculate_tier1 (MarketData)
    T1->>T1: Descent Velocity Filter (Panic vs Grind)
    T1->>T1: Divergence Check (Price vs VIX/Breadth)
    T1-->>Main: Tier1Result (0-100 Score + Bonuses)
    Main->>T2: calculate_tier2 (Price, OptionsChain)
    T2-->>Main: Tier2Result (Adjustment + Hard Veto Flags)
    Main->>Agg: aggregate(T1, T2, Regime, PrevSignal)
    Agg->>Agg: Dynamic Thresholding (Schmitt Trigger)
    Agg-->>Main: SignalResult (STRONG_BUY to NO_SIGNAL)
    Main->>DB: Save SignalResult (JSON Blob)
    Main->>DB: Update Macro State Cache
    Main->>Main: Output Result (CLI/JSON)
```

---

## 3. Data Contracts

### 3.1 MarketData (Input Model)
The canonical object passed to all engine functions.
- **Identifiers**: `date`, `price`.
- **Tier 1 Alpha**: `vix`, `fear_greed`, `adv_dec_ratio`, `ma200`, `high_52w`.
- **v5.0 Meta**: `vix_zscore`, `drawdown_zscore`, `days_since_52w_high`.
- **Macro/Flow**: `credit_spread`, `forward_pe`, `net_liquidity`, `short_vol_ratio`.

### 3.2 SignalResult (Output Model)
The immutable record of a single execution.
- **Signal**: Enum (`STRONG_BUY`, `TRIGGERED`, `WATCH`, `GREEDY`, `NO_SIGNAL`).
- **Final Score**: Aggregated Tier-1 score + Tier-2 adjustment.
- **Explanation**: Contextual Chinese-language explanation of why the signal was generated.
- **Nested Results**: Includes full `Tier1Result` and `Tier2Result` for auditability.

---

## 4. Persistence Schema

### 4.1 `signals` Table
Stores the historical result of every run.
- `date`: TEXT PRIMARY KEY (ISO format).
- `signal`: TEXT (The enum value).
- `final_score`: INTEGER.
- `json_blob`: TEXT (The full `SignalResult` serialized as JSON).

### 4.2 `macro_states` Table
Acts as a cache for low-frequency macro data (FRED/Analyst Revisions).
- Allows the system to run in **Degraded Mode** if APIs fail.

---

## 5. Resilience & Error Handling

The system is designed for "Graceful Degradation":

1.  **Source Failures**: If `yfinance` or `FRED` fails, the system uses **Neutral Defaults** (e.g., VIX=20.0, F&G=50) or **Cached Values** from the `macro_states` table.
2.  **Options Fallback**: If the `yfinance` options chain lacks Greeks, the system employs a **Black-Scholes Fallback** to calculate Gamma and identify the Gamma Flip level.
3.  **Hard Vetoes**: Architectural constraints ensure that even if scoring is high, a "Hard Veto" (e.g., Price < Put Wall) will strictly prevent a `TRIGGERED` signal.

---

## 6. Adaptive Thresholding (Schmitt Trigger)

To prevent signal flickering at threshold boundaries, the `Aggregator` implements a **Hysteresis** pattern:
- **Sticky Trigger**: If the previous state was `TRIGGERED`, the threshold to stay in `TRIGGERED` is lowered by 5 points.
- **Regime Shift**: Thresholds are dynamically adjusted based on the `Market Regime` (STORM vs QUIET) identified in Tier 1.
