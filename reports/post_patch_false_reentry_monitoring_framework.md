# Post-Patch False Re-Entry Monitoring Framework

## Summary
False re-entry stays live as count monitoring even when realized damage is small.

## Decision
`FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "carry_forward_rules": [
    "track count and damage separately in every future event-window audit",
    "raise governance attention on nonzero count even when realized damage is below threshold",
    "do not use count directly in verdict or budget scoring"
  ],
  "decision": "FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY",
  "event_family_thresholds": [
    {
      "concern_count_threshold": 1,
      "concern_damage_threshold": 0.01,
      "event_family": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 1,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "recovery-with-relapse",
      "event_name": "2022 bear rally relapse",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    },
    {
      "concern_count_threshold": 2,
      "concern_damage_threshold": 0.01,
      "event_family": "rapid V-shape ordinary correction",
      "event_name": "2023 Q3/Q4 V-shape",
      "nonzero_count_low_damage_governance_attention": true,
      "observed_false_reentry_count": 0,
      "observed_false_reentry_damage": 0.0
    }
  ],
  "false_reentry_count_metric": {
    "definition": "count of releases/re-risk transitions while unresolved stress remains active",
    "downstream_role": "MONITORING_ONLY",
    "may_enter_budget_scoring": false
  },
  "false_reentry_damage_metric": {
    "accounting_basis": "ACTUAL_EXECUTED_ONLY",
    "definition": "actual-executed negative return after false release or premature re-risk",
    "downstream_role": "DAMAGE_CONTEXT_ONLY"
  },
  "interpretation_rule": "low historical false_reentry_damage does NOT imply the issue is solved.",
  "summary": "False re-entry stays live as count monitoring even when realized damage is small."
}
```
