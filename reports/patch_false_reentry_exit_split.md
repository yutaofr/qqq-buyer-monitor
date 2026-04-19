# Patch False Reentry Exit Split

## Summary
False re-entry/exit count diagnostics are physically separated from actual-executed damage accounting.

## Decision
`FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT`

## Machine-Readable Snapshot
```json
{
  "damage_accounting_family": {
    "accounting_basis": "ACTUAL_EXECUTED_ONLY",
    "admissible_downstream": true,
    "rows": [
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "event_name": "COVID fast cascade",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.010523
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "event_name": "August 2015 liquidity vacuum",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "2018-style partially containable drawdown",
        "event_name": "Q4 2018 drawdown",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "slower structural stress",
        "event_name": "2022 H1 structural stress",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "slower structural stress",
        "event_name": "2008 financial crisis stress",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "recovery-with-relapse",
        "event_name": "2022 bear rally relapse",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      },
      {
        "accounting_basis": "ACTUAL_EXECUTED_ONLY",
        "admissible_downstream": true,
        "event_class": "rapid V-shape ordinary correction",
        "event_name": "2023 Q3/Q4 V-shape",
        "false_exit_damage_metric": 0.0,
        "false_reentry_damage_metric": 0.0
      }
    ]
  },
  "decision": "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT",
  "operational_diagnostic_family": {
    "allowed_downstream_role": "DIAGNOSTIC_ONLY",
    "may_enter_budget_or_verdict_scoring": false,
    "rows": [
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 1
        },
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "event_name": "COVID fast cascade",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 1
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 0
        },
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "event_name": "August 2015 liquidity vacuum",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 0
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 0
        },
        "event_class": "2018-style partially containable drawdown",
        "event_name": "Q4 2018 drawdown",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 0
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 1
        },
        "event_class": "slower structural stress",
        "event_name": "2022 H1 structural stress",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 1
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 0
        },
        "event_class": "slower structural stress",
        "event_name": "2008 financial crisis stress",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 0
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 0
        },
        "event_class": "recovery-with-relapse",
        "event_name": "2022 bear rally relapse",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 0
      },
      {
        "allowed_downstream_role": "DIAGNOSTIC_ONLY",
        "count_by_module_interaction_path": {
          "full_stack_entry_while_benign": 0,
          "full_stack_release_while_unresolved": 0
        },
        "event_class": "rapid V-shape ordinary correction",
        "event_name": "2023 Q3/Q4 V-shape",
        "false_exit_count_metric": 0,
        "false_reentry_count_metric": 0
      }
    ]
  },
  "split_metrics": [
    {
      "damage_version_admissible_downstream": true,
      "new_count_version": "operational_diagnostic_family.false_reentry_count_metric / false_exit_count_metric",
      "new_damage_version": "damage_accounting_family.false_reentry_damage_metric / false_exit_damage_metric",
      "old_definition": "false_exit_or_false_reentry_count mixed with damage-bearing stack metrics",
      "old_uses_must_be_invalidated": true
    }
  ],
  "summary": "False re-entry/exit count diagnostics are physically separated from actual-executed damage accounting."
}
```
