# v12.0 Coding Standards & AC Criteria

> **The "How" - Mandate & Guardrails**

## Mandatory AC (Acceptance Criteria)
Every PR must strictly adhere to:
- **AC-0 No Hardcoding**: Parameters from `regime_audit.json` only.
- **AC-1 Causal Isolation**: No look-ahead bias.
- **AC-2 Decimal Normalize**: Macro levels must be decimal units (0.05, not 5.0).
- **AC-4 Intent-Action Separation**: Return both `raw_target_beta` and `target_beta`.
- **AC-6 PIT Compliance**: Manual publication lag simulation for Tier 1-4 data.
- **AC-8 Factor Orthogonality**: Assign each factor to a specific orthogonal layer.
- **AC-10 Gram-Schmidt Engine**: Use expanding-window residuals for collinear pairs.

## Code Quality
- **Python 3.12+**.
- **Ruff Compliance**: 0 warnings or errors from `ruff check .`. Must pass CI linting.
- **Functional Logic**: Favor pure functions for Bayesian cores.
- **Numerical Integrity**: Maintain bit-identical parity between research and production.
