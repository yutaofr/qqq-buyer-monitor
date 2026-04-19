# Frontier Soft-Constraint Frontier Estimation

## Summary
Soft headroom exists, but transfer discounts prevent treating in-sample share as full budget space.

## Decision
`SOFT_CONSTRAINT_HEADROOM_EXISTS_BUT_IS_SMALL`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "candidate_rows": [
    {
      "current_policy_improvable_share": 0.145387,
      "frontier_assessment": "small_but_worth_bounded_work",
      "hard_constraint_blocked_portion": 0.043616,
      "likely_additional_gain_ceiling": 0.033796,
      "research_line": "recovery-with-relapse refinement",
      "soft_constraint_tuning_portion": 0.045797
    },
    {
      "current_policy_improvable_share": 0.124347,
      "frontier_assessment": "small_but_worth_bounded_work",
      "hard_constraint_blocked_portion": 0.055956,
      "likely_additional_gain_ceiling": 0.051293,
      "research_line": "2008 subtype-specific structural repair",
      "soft_constraint_tuning_portion": 0.051293
    },
    {
      "current_policy_improvable_share": 0.067316,
      "frontier_assessment": "already_near_practical_frontier",
      "hard_constraint_blocked_portion": 0.026926,
      "likely_additional_gain_ceiling": 0.018175,
      "research_line": "2022 H1 subtype-specific structural repair",
      "soft_constraint_tuning_portion": 0.018175
    },
    {
      "current_policy_improvable_share": 0.016454,
      "frontier_assessment": "already_near_practical_frontier",
      "hard_constraint_blocked_portion": 0.005759,
      "likely_additional_gain_ceiling": 0.0,
      "research_line": "hazard as slow-stress timing assistant",
      "soft_constraint_tuning_portion": 0.001604
    },
    {
      "current_policy_improvable_share": 0.067592,
      "frontier_assessment": "small_but_worth_bounded_work",
      "hard_constraint_blocked_portion": 0.013518,
      "likely_additional_gain_ceiling": 0.024333,
      "research_line": "2018-style refinement",
      "soft_constraint_tuning_portion": 0.024333
    }
  ],
  "decision": "SOFT_CONSTRAINT_HEADROOM_EXISTS_BUT_IS_SMALL",
  "dominant_driver_decision": "NO_DRIVER_HAS_MEANINGFUL_HEADROOM_LEFT",
  "summary": "Soft headroom exists, but transfer discounts prevent treating in-sample share as full budget space."
}
```
