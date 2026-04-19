# Post-Patch Priority Logic Reset

## Summary
Budget logic is reset to opportunity space, not residual pain.

## Decision
`PRIORITY_LOGIC_RESET_SUCCEEDED`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "decision": "PRIORITY_LOGIC_RESET_SUCCEEDED",
  "definitions": {
    "policy_contribution": "actual-executed realized contribution of the current policy stack versus baseline",
    "policy_improvable_share": "bounded expected research payoff space under actual-executed accounting",
    "residual_unrepaired_share": "remaining loss mass, including structurally non-defendable or execution-bound components"
  },
  "required_statement": "residual_unrepaired_share may describe pain, but may not by itself justify primary budget priority.",
  "research_priority_score": {
    "formula": "policy_improvable_share * contribution_quality_multiplier * interaction_feasibility_multiplier * non_boundary_multiplier",
    "primary_anchor": "policy_improvable_share",
    "residual_unrepaired_share_role": "secondary_descriptive_only",
    "secondary_inputs": [
      "actual_executed_policy_contribution_quality",
      "interaction_feasibility",
      "non_boundary_status"
    ]
  },
  "summary": "Budget logic is reset to opportunity space, not residual pain."
}
```
