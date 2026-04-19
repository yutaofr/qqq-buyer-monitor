# Frontier Budget Anchor Reinstatement

## Summary
Policy-improvable share is not reinstated as a hard budget anchor unless transfer tests hold.

## Decision
`POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "decision": "POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED",
  "downgraded_role_if_not": "directional descriptive input with transfer and admissibility gates",
  "is_policy_improvable_share_transferable_enough": false,
  "is_still_best_budget_anchor_available": false,
  "next_cycle_ranking_rule": "no primary ranking at all",
  "soft_constraint_frontier_decision": "SOFT_CONSTRAINT_HEADROOM_EXISTS_BUT_IS_SMALL",
  "summary": "Policy-improvable share is not reinstated as a hard budget anchor unless transfer tests hold."
}
```
