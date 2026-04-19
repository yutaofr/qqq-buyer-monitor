# Post-Patch Policy-Improvable Re-Ranking

## Summary
Families are re-ranked by actual-executed policy-improvable share with boundary exclusions.

## Decision
`POLICY_IMPROVABLE_RANKING_IS_DECISION_READY`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "decision": "POLICY_IMPROVABLE_RANKING_IS_DECISION_READY",
  "event_family_rows": [
    {
      "admissible_for_primary_bounded_research": true,
      "contribution_positive": true,
      "disclosure_only": false,
      "event_family": "recovery-with-relapse",
      "events": [
        "2022 bear rally relapse"
      ],
      "execution_dominated": false,
      "exit_system_contribution": 0.115184,
      "hazard_contribution": 0.0,
      "policy_contribution": 0.125655,
      "policy_improvable_share": 0.145387,
      "research_priority_score": 0.145387,
      "residual_unrepaired_share": 0.706836,
      "status": "PRIMARY_RANKABLE",
      "structurally_capped": false
    },
    {
      "admissible_for_primary_bounded_research": true,
      "contribution_positive": true,
      "disclosure_only": false,
      "event_family": "slower structural stress",
      "events": [
        "2022 H1 structural stress",
        "2008 financial crisis stress"
      ],
      "execution_dominated": false,
      "exit_system_contribution": 0.442093,
      "hazard_contribution": 0.041905,
      "policy_contribution": 0.516533,
      "policy_improvable_share": 0.097055,
      "research_priority_score": 0.097055,
      "residual_unrepaired_share": 0.47412,
      "status": "PRIMARY_RANKABLE",
      "structurally_capped": false
    },
    {
      "admissible_for_primary_bounded_research": true,
      "contribution_positive": true,
      "disclosure_only": false,
      "event_family": "2018-style partially containable drawdown",
      "events": [
        "Q4 2018 drawdown"
      ],
      "execution_dominated": false,
      "exit_system_contribution": 0.071979,
      "hazard_contribution": 0.0,
      "policy_contribution": 0.078835,
      "policy_improvable_share": 0.067592,
      "research_priority_score": 0.067592,
      "residual_unrepaired_share": 0.617617,
      "status": "PRIMARY_RANKABLE",
      "structurally_capped": false
    },
    {
      "admissible_for_primary_bounded_research": false,
      "contribution_positive": false,
      "disclosure_only": true,
      "event_family": "2020-like fast-cascade / dominant overnight gap",
      "events": [
        "COVID fast cascade"
      ],
      "execution_dominated": false,
      "exit_system_contribution": -0.037592,
      "hazard_contribution": -0.047143,
      "policy_contribution": -0.08652,
      "policy_improvable_share": 0.0,
      "research_priority_score": 0.0,
      "residual_unrepaired_share": 0.560198,
      "status": "BOUNDARY_DISCLOSURE_ONLY",
      "structurally_capped": true
    },
    {
      "admissible_for_primary_bounded_research": false,
      "contribution_positive": false,
      "disclosure_only": true,
      "event_family": "2015-style liquidity vacuum / flash impairment",
      "events": [
        "August 2015 liquidity vacuum"
      ],
      "execution_dominated": true,
      "exit_system_contribution": -0.093896,
      "hazard_contribution": 0.0,
      "policy_contribution": -0.102431,
      "policy_improvable_share": 0.0,
      "research_priority_score": 0.0,
      "residual_unrepaired_share": 0.775535,
      "status": "EXECUTION_DOMINATED_DISCLOSURE_ONLY",
      "structurally_capped": false
    },
    {
      "admissible_for_primary_bounded_research": false,
      "contribution_positive": false,
      "disclosure_only": false,
      "event_family": "rapid V-shape ordinary correction",
      "events": [
        "2023 Q3/Q4 V-shape"
      ],
      "execution_dominated": false,
      "exit_system_contribution": 0.0,
      "hazard_contribution": 0.0,
      "policy_contribution": 0.0,
      "policy_improvable_share": 0.0,
      "research_priority_score": 0.0,
      "residual_unrepaired_share": 1.0,
      "status": "SECONDARY_OR_MONITORING_ONLY",
      "structurally_capped": false
    }
  ],
  "primary_budget_anchor": "policy_improvable_share",
  "ranking_rule": [
    "positive_or_non_catastrophic_actual_executed_policy_contribution",
    "policy_improvable_share",
    "interaction_feasibility",
    "non_boundary_status"
  ],
  "summary": "Families are re-ranked by actual-executed policy-improvable share with boundary exclusions."
}
```
