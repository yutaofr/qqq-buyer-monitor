# Convergence Residual Protection Boundary

## Summary
Residual protection remains boundary-only while account mode is spot-only/no-derivatives.

## Decision
`RESIDUAL_PROTECTION_REMAINS_BOUNDARY_ONLY`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "account_mode": {
    "no_derivatives": true,
    "no_shorting": true,
    "spot_only": true
  },
  "budget_primary_status": false,
  "decision": "RESIDUAL_PROTECTION_REMAINS_BOUNDARY_ONLY",
  "operationalized": false,
  "separate_feasibility_branch_reopen_criteria": [
    "derivatives become executable",
    "carry and slippage model exists",
    "target-specific benefit tests are clean-room validated"
  ],
  "summary": "Residual protection remains boundary-only while account mode is spot-only/no-derivatives."
}
```
