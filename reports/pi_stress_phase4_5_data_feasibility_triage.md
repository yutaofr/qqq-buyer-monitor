# Phase 4.5 Data Feasibility & Triage

## Objective
Determine what real state-data can actually be acquired, backfilled, aligned causally, and tested for ordinary-correction marginal value.

## 0A. Cross-sectional stress state
- Breadth: `READY_FOR_DISCOVERY`. High frequency, clean history back to 2000.
- Dispersion: `READY_FOR_DISCOVERY`.
- Realized correlation: `PROXY_ONLY_DISCOVERY`. Requires complex matrix backfill, using index proxies for now.

## 0B. Volatility-surface / panic-structure state
- VIX term structure: `READY_FOR_DISCOVERY`. Historical CBOE data available, minor alignment complexity.
- Convexity-demand regime: `NOT_READY_THIS_PHASE`. Insufficient historical depth.

## 0C. Credit / liquidity regime state
- High-yield spread stress: `READY_FOR_DISCOVERY`. FRED data robust.
- Liquidity withdrawal: `PROXY_ONLY_DISCOVERY`.

## 0D. Cross-asset divergence state
- Equity/rates divergence: `READY_FOR_DISCOVERY`.
- Gold/equity divergence: `READY_FOR_DISCOVERY`.

## Triage Verdict
The phase should lean heavily toward data engineering and taxonomy/label work first, as we have enough `READY_FOR_DISCOVERY` series to begin constrained discovery loops.
