# v12.0 Architecture Principles

> **The "Why" - Core Design Philosophy**

## 1. Orthogonal Reality (v12.0)
- **Three-Layer Matrix**: Discount, Real Economy, Sentiment.
- **Factor Independence**: No information inbreeding. Collinear factors must be decoupled.

## 2. Information Honesty
- **Entropy-First**: Quantify model doubt via Shannon Entropy.
- **Haircut Logic**: `target_beta = raw_target_beta * exp(-H)`. High uncertainty results in automatic de-risking.

## 3. PIT (Point-in-Time) Compliance
- **Zero Future Leakage**: Backtests must simulate historical data availability.
- **Lag Alignment**: Financial (T+1), Real Economy (Release+30d), Earnings (MonthEnd+30d).

## 4. Orthogonalization Engine
- **Gram-Schmidt Process**: Online residual extraction for MOVE and Credit Spreads to satisfy Bayesian conditional independence.
