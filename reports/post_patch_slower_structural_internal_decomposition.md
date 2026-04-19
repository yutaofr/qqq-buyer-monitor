# Post-Patch Slower Structural Internal Decomposition

## Summary
Slower structural stress is positive at family level but internally heterogeneous.

## Claim Strength Label
`FAMILY_LEVEL_PRIORITY_REQUIRES_SUBTYPE_SPLIT`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "claim_strength_label": "FAMILY_LEVEL_PRIORITY_REQUIRES_SUBTYPE_SPLIT",
  "heterogeneity_test": {
    "family_level_score_dominated_by_one_event": true,
    "gain_leader": "2008 financial crisis stress",
    "residual_damage_concentrates_in_different_event_than_gains": true,
    "residual_leader": "2022 H1 structural stress",
    "unified_research_objective_would_be_misleading": true
  },
  "subtype_rows": [
    {
      "event_name": "2022 H1 structural stress",
      "exit_system_contribution": 0.125762,
      "hazard_contribution": 0.041905,
      "policy_contribution": 0.171444,
      "policy_improvable_share": 0.067316,
      "positive_gain_share_within_family": 0.331913,
      "re_risk_release_diagnostics": {
        "false_release_damage": 0.0,
        "premature_re_risk_count": 0,
        "recovery_miss_days": 0,
        "release_count": 1
      },
      "residual_loss_share_within_family": 0.504423,
      "residual_negative_loss": 1.272807,
      "residual_unrepaired_share": 0.499757,
      "subtype": "multi-wave structural stress",
      "support_disclosure": "minimum required slower-structural event window"
    },
    {
      "event_name": "2008 financial crisis stress",
      "exit_system_contribution": 0.316331,
      "hazard_contribution": 0.0,
      "policy_contribution": 0.345089,
      "policy_improvable_share": 0.124347,
      "positive_gain_share_within_family": 0.668087,
      "re_risk_release_diagnostics": {
        "false_release_damage": 0.0,
        "premature_re_risk_count": 0,
        "recovery_miss_days": 0,
        "release_count": 0
      },
      "residual_loss_share_within_family": 0.495577,
      "residual_negative_loss": 1.250486,
      "residual_unrepaired_share": 0.450593,
      "subtype": "monotonic structural stress",
      "support_disclosure": "minimum required slower-structural event window"
    }
  ],
  "summary": "Slower structural stress is positive at family level but internally heterogeneous."
}
```
