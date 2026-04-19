# Patch Structural Boundary Role Separation

## Summary
Structural boundary metrics are preserved as boundary constraints and excluded from policy value scoring.

## Decision
`STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY`

## Machine-Readable Snapshot
```json
{
  "basis_classification": "MARKET_STRUCTURE_ATTRIBUTION",
  "decision": "STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY",
  "structural_metrics": [
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "execution_dominated_share": 0.778639,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.75,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "execution_dominated_share": 0.730009,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.530009,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "execution_dominated_share": 0.308646,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.308646,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "execution_dominated_share": 0.36047,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.36047,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "execution_dominated_share": 0.540508,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.340508,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "recovery-with-relapse",
      "event_name": "2022 bear rally relapse",
      "execution_dominated_share": 0.415684,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.415684,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    },
    {
      "event_class": "rapid V-shape ordinary correction",
      "event_name": "2023 Q3/Q4 V-shape",
      "execution_dominated_share": 0.339815,
      "may_enter_policy_value_score": false,
      "metric_names": [
        "structural_non_defendability_share",
        "execution_dominated_share",
        "largest_overnight_gap",
        "gap_loss_share"
      ],
      "prior_downstream_uses_must_be_downgraded": true,
      "remains_valid_as_market_structure_attribution": true,
      "removed_from_policy_aggregation": true,
      "structural_non_defendability_share": 0.339815,
      "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
      "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring"
    }
  ],
  "summary": "Structural boundary metrics are preserved as boundary constraints and excluded from policy value scoring."
}
```
