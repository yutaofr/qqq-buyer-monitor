# v12.0 Architecture Principles

> **The "Why" - Core Design Philosophy**

## 1. Orthogonal Reality (v12.0)

- **Three-Layer Matrix**: Discount, Real Economy, Sentiment.
- **Factor Independence**: No information inbreeding. Collinear factors must be decoupled.

## 2. Information Honesty (v12.1-FIXED)

- **Bayesian Integrity**: Strict adherence to $Posterior \propto Prior \times Likelihood$. No linear mixtures or artificial momentum caps that trap the system in high-entropy states.
- **Temperature Calibration (Tau=3.0)**: Use Log-Likelihood scaling to smooth Naive Bayes overconfidence, ensuring a realistic probability distribution.
- **Entropy-First**: Quantify model doubt via Shannon Entropy.
- **Gaussian Haircut (Non-linear)**: `target_beta = raw_beta * exp(-0.6 * (H_norm * log(states))^2)`. Accelerated de-risking in conflict zones (H > 0.7) to protect capital while preventing suicidal cuts.

## 3. Real-Economy Gravity

- **Physical Sensing**: 12-factor augmented space (including PMI Mom, Labor Slack).
- **Rational Damping**: 21d EWMA smoothing for monthly macro signals to prevent daily decision jitters.

## 4. Cascading Defense & Redlines

- **Tiered Quality (Veto)**: Level 1 (Credit) sensor failure results in immediate entropy spike.
- **ULTIMA Circuit Breaker**: 21-day cognitive deadlock triggers sensor surgical cut (back to core credit).
- **User Redline**: Final target_beta is floor-locked at 0.5. Business survival precedes statistical inference.
- **Sidecar-Tractor Parity**: QQQ Sidecar model must align with Tractor's "Left Tail Risk" convention. Physical coefficient signs ($C_{growth} \le 0, C_{liquidity} \le 0$) are inviolable architecture constraints.

## 5. PIT (Point-in-Time) Compliance

- **8-Year Hydration**: Minimum 2000+ sample memory required for prior self-consistency.
- **Zero Future Leakage**: Sequential replay strictly mimics T+0 observability.

## 4. Orthogonalization Engine

- **Gram-Schmidt Process**: Online residual extraction for MOVE and Credit Spreads to satisfy Bayesian conditional independence.
