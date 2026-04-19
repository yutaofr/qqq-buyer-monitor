# Frontier Hard vs Soft Constraint Separation

## Summary
Hard account boundaries are separated from tunable policy/state-machine choices.

## Decision
`HARD_AND_SOFT_CONSTRAINTS_ARE_SUFFICIENTLY_SEPARATED`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "constraint_rows": [
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": false,
      "classification": "HARD_CONSTRAINT",
      "item": "one-session execution lag",
      "residual_loss_mass_attributable_to_item": 0.775535
    },
    {
      "belongs_in": "future_redesign_or_disclosure",
      "can_change_within_current_account_assumptions": false,
      "classification": "HARD_CONSTRAINT",
      "item": "overnight gap exposure",
      "residual_loss_mass_attributable_to_item": 0.775535
    },
    {
      "belongs_in": "future_redesign_or_disclosure",
      "can_change_within_current_account_assumptions": false,
      "classification": "HARD_CONSTRAINT",
      "item": "daily signal cadence",
      "residual_loss_mass_attributable_to_item": 0.775535
    },
    {
      "belongs_in": "future_redesign_or_disclosure",
      "can_change_within_current_account_assumptions": false,
      "classification": "HARD_CONSTRAINT",
      "item": "regular-session-only execution",
      "residual_loss_mass_attributable_to_item": 0.775535
    },
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": true,
      "classification": "SOFT_CONSTRAINT",
      "item": "exit persistence rules",
      "residual_loss_mass_attributable_to_item": 0.689051
    },
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": true,
      "classification": "SOFT_CONSTRAINT",
      "item": "release thresholds",
      "residual_loss_mass_attributable_to_item": 0.689051
    },
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": true,
      "classification": "SOFT_CONSTRAINT",
      "item": "rerisk confirmation strictness",
      "residual_loss_mass_attributable_to_item": 0.689051
    },
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": true,
      "classification": "SOFT_CONSTRAINT",
      "item": "hazard timing sensitivity",
      "residual_loss_mass_attributable_to_item": 0.689051
    },
    {
      "belongs_in": "frontier_estimation",
      "can_change_within_current_account_assumptions": true,
      "classification": "SOFT_CONSTRAINT",
      "item": "module aggregation logic",
      "residual_loss_mass_attributable_to_item": 0.689051
    }
  ],
  "decision": "HARD_AND_SOFT_CONSTRAINTS_ARE_SUFFICIENTLY_SEPARATED",
  "summary": "Hard account boundaries are separated from tunable policy/state-machine choices."
}
```
