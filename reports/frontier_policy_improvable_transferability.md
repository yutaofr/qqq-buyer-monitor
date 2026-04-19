# Frontier Policy-Improvable Transferability

## Summary
Policy-improvable share changes materially across blind-ish holdouts.

## Decision
`POLICY_IMPROVABLE_SHARE_IS_NOT_TRANSFERABLE_ENOUGH`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "decision": "POLICY_IMPROVABLE_SHARE_IS_NOT_TRANSFERABLE_ENOUGH",
  "hard_rule_result": "policy_improvable_share_may_not_directly_drive_next_cycle_primary_budget_allocation",
  "line_rows": [
    {
      "held_out_estimated_policy_improvable_share": 0.033796,
      "held_out_rank": 3,
      "material_collapse": true,
      "original_policy_improvable_share": 0.145387,
      "original_rank": 1,
      "path_specificity": "PATH_SPECIFIC_OR_WEAK",
      "ranking_stability": "COLLAPSED",
      "research_line": "recovery-with-relapse refinement",
      "sign_stability": "SIGN_STABLE",
      "top_rank_survives_holdout": false
    },
    {
      "held_out_estimated_policy_improvable_share": 0.067454,
      "held_out_rank": 2,
      "material_collapse": false,
      "original_policy_improvable_share": 0.124347,
      "original_rank": 2,
      "path_specificity": "ROBUST_ENOUGH",
      "ranking_stability": "STABLE",
      "research_line": "2008 subtype-specific structural repair",
      "sign_stability": "SIGN_STABLE",
      "top_rank_survives_holdout": true
    },
    {
      "held_out_estimated_policy_improvable_share": 0.09597,
      "held_out_rank": 1,
      "material_collapse": false,
      "original_policy_improvable_share": 0.067316,
      "original_rank": 4,
      "path_specificity": "PATH_SPECIFIC_OR_WEAK",
      "ranking_stability": "MATERIAL_CHANGE",
      "research_line": "2022 H1 subtype-specific structural repair",
      "sign_stability": "SIGN_STABLE",
      "top_rank_survives_holdout": true
    },
    {
      "held_out_estimated_policy_improvable_share": 0.0,
      "held_out_rank": 5,
      "material_collapse": true,
      "original_policy_improvable_share": 0.016454,
      "original_rank": 5,
      "path_specificity": "PATH_SPECIFIC_OR_WEAK",
      "ranking_stability": "COLLAPSED",
      "research_line": "hazard as slow-stress timing assistant",
      "sign_stability": "SIGN_UNSTABLE",
      "top_rank_survives_holdout": true
    },
    {
      "held_out_estimated_policy_improvable_share": 0.033658,
      "held_out_rank": 4,
      "material_collapse": true,
      "original_policy_improvable_share": 0.067592,
      "original_rank": 3,
      "path_specificity": "PATH_SPECIFIC_OR_WEAK",
      "ranking_stability": "COLLAPSED",
      "research_line": "2018-style refinement",
      "sign_stability": "SIGN_STABLE",
      "top_rank_survives_holdout": true
    }
  ],
  "ranking_order_stability": {
    "any_material_change": true,
    "any_sign_instability": true,
    "max_rank_change": 3,
    "mean_rank_change": 1.2
  },
  "summary": "Policy-improvable share changes materially across blind-ish holdouts.",
  "validation_designs": [
    "leave_one_event_family_out",
    "leave_one_major_window_out",
    "subtype_holdouts",
    "cross_validation_of_ranking_order_across_event_subsets"
  ]
}
```
