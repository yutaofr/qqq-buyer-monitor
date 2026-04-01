# v12.1 Coding Standards & AC Criteria

> **The "How" - Mandate & Guardrails**

## Mandatory AC (Acceptance Criteria)
Every PR must strictly adhere to:
- **AC-0 No Hardcoding**: Parameters from `regime_audit.json` only.
- **AC-1 Causal Isolation**: No look-ahead bias.
- **AC-4 Intent-Action Separation**: Return both `raw_target_beta` and `target_beta`.
- **AC-6 PIT Compliance**: Manual publication lag simulation or ALFRED vintage extraction.
- **AC-10 Gram-Schmidt Engine**: Use residuals for collinear pairs.
- **AC-11 ALFRED Isolation**: Macro backtests must use PIT Initial Releases from ALFRED.
- **AC-12 Relative Survival**: L4 must satisfy `IR_diff >= -0.05` in all natural years.
- **AC-13 Topological Continuity**: No `if/else` for leverage multipliers. $C^1$ continuity mandatory.

## Code Quality
- **Python 3.12+**.
- **Matrix Optimization**: Use JAX/Numba or analytical inverses for high-frequency loops.
- **Chaos Robustness**: Pass Chaos Monkey data corruption tests before release.

