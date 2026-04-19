# Phase 4.5 Identifiability & Sample-Budget Control

## 3A. Effective Sample Budget
Under the 4-class reduced hierarchy, raw support and contiguous episode counts are mathematically viable. Crisis-vs-structural support is merged to avoid ambiguity leakage.

## 3B. Complexity Budget
- Maximum allowed Stage 1 complexity: Linear or single-layer constrained.
- Maximum allowed Stage 2 complexity: Bayesian posterior updates only, no hidden recurrent states.
- Transition/healing states are softened and merged into recovery.

## 3C. Two-stage Identifiability Audit
Testing Stage 2 with raw signals vs. Stage 1 outputs.
Under full 6-class complexity, the overlap audit showed massive price-topology and volatility overlap, making Stage 1 unidentifiable.
By constraining to the reduced hierarchy, Stage 1 provides stable, orthogonal incremental value.

**Verdict**: `IDENTIFIABLE_ONLY_UNDER_REDUCED_COMPLEXITY`
