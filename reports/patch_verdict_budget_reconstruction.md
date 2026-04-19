# Patch Verdict Budget Reconstruction

## Summary
Budget and verdict inputs are rebuilt from separate policy-value and structural-constraint vectors.

## Decision
`VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN`

## Machine-Readable Snapshot
```json
{
  "damage_accounting_inputs": {
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
  "decision": "VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN",
  "diagnostic_count_inputs": {
    "source": "false_reentry_exit_split.operational_diagnostic_family",
    "used_in_budget_scoring": false
  },
  "policy_value_vector": {
    "allowed_in_budget_scoring": true,
    "basis": "ACTUAL_EXECUTED_ONLY",
    "rows": [
      {
        "budget_score_component": -0.102431,
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "policy_contribution": -0.102431,
        "policy_improvable_share": 0.0,
        "residual_unrepaired_share": 0.775535
      },
      {
        "budget_score_component": 0.078835,
        "event_class": "2018-style partially containable drawdown",
        "policy_contribution": 0.078835,
        "policy_improvable_share": 0.067592,
        "residual_unrepaired_share": 0.617617
      },
      {
        "budget_score_component": -0.08652,
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "policy_contribution": -0.08652,
        "policy_improvable_share": 0.0,
        "residual_unrepaired_share": 0.560198
      },
      {
        "budget_score_component": 0.0,
        "event_class": "rapid V-shape ordinary correction",
        "policy_contribution": 0.0,
        "policy_improvable_share": 0.0,
        "residual_unrepaired_share": 1.0
      },
      {
        "budget_score_component": 0.125655,
        "event_class": "recovery-with-relapse",
        "policy_contribution": 0.125655,
        "policy_improvable_share": 0.145387,
        "residual_unrepaired_share": 0.706836
      },
      {
        "budget_score_component": 0.516533,
        "event_class": "slower structural stress",
        "policy_contribution": 0.516533,
        "policy_improvable_share": 0.097055,
        "residual_unrepaired_share": 0.47412
      }
    ]
  },
  "reconstructed_budget_allocation_metrics": {
    "bounded_budget_focus_event_class": "slower structural stress",
    "not_deployment_readiness": true,
    "not_freezeability": true,
    "not_maturity": true,
    "primary_language_scope": "bounded budget priority only"
  },
  "reconstructed_verdict_driving_kpi": {
    "all_scored_inputs_actual_executed_only": true,
    "mixed_inputs_excluded": true,
    "structural_inputs_excluded_from_score": true
  },
  "structural_constraint_vector": {
    "allowed_role": "boundary constraint / override / disclosure context",
    "basis": "MARKET_STRUCTURE_ATTRIBUTION",
    "rows": [
      {
        "boundary_only": true,
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "event_name": "COVID fast cascade",
        "execution_dominated_share": 0.778639,
        "structural_non_defendability_share": 0.75
      },
      {
        "boundary_only": true,
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "event_name": "August 2015 liquidity vacuum",
        "execution_dominated_share": 0.730009,
        "structural_non_defendability_share": 0.530009
      },
      {
        "boundary_only": true,
        "event_class": "2018-style partially containable drawdown",
        "event_name": "Q4 2018 drawdown",
        "execution_dominated_share": 0.308646,
        "structural_non_defendability_share": 0.308646
      },
      {
        "boundary_only": true,
        "event_class": "slower structural stress",
        "event_name": "2022 H1 structural stress",
        "execution_dominated_share": 0.36047,
        "structural_non_defendability_share": 0.36047
      },
      {
        "boundary_only": true,
        "event_class": "slower structural stress",
        "event_name": "2008 financial crisis stress",
        "execution_dominated_share": 0.540508,
        "structural_non_defendability_share": 0.340508
      },
      {
        "boundary_only": true,
        "event_class": "recovery-with-relapse",
        "event_name": "2022 bear rally relapse",
        "execution_dominated_share": 0.415684,
        "structural_non_defendability_share": 0.415684
      },
      {
        "boundary_only": true,
        "event_class": "rapid V-shape ordinary correction",
        "event_name": "2023 Q3/Q4 V-shape",
        "execution_dominated_share": 0.339815,
        "structural_non_defendability_share": 0.339815
      }
    ],
    "used_in_policy_value_score": false
  },
  "summary": "Budget and verdict inputs are rebuilt from separate policy-value and structural-constraint vectors."
}
```
