# Post-Patch Bounded Budget Allocation

## Summary
Budget allocation is reconstructed from improvable share, contribution, boundary status, and interaction feasibility.

## Decision
`BOUNDED_BUDGET_ALLOCATION_IS_NOW_DECISION_READY`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "allocation_rule": [
    "policy_improvable_share",
    "actual_executed_positive_contribution_or_plausible_bounded_upside",
    "non_boundary_status",
    "validated_interaction_feasibility"
  ],
  "budget_lines": [
    {
      "bucket": "primary bounded research",
      "rationale": "subtype-specific structural repair avoids hiding 2008/2022 heterogeneity",
      "research_line": "slower structural subtype-specific work: 2008 financial crisis stress"
    },
    {
      "bucket": "bounded secondary research",
      "rationale": "retained as subtype-specific work because residual composition differs from the gain leader",
      "research_line": "slower structural subtype-specific work: 2022 H1 structural stress"
    },
    {
      "bucket": "bounded secondary research",
      "rationale": "broad family label is downgraded because subtype split is required",
      "research_line": "slower structural stress exit refinement"
    },
    {
      "bucket": "co-primary / elevated secondary research",
      "rationale": "Holding recovery-with-relapse below elevated status would violate the post-patch rule: it has the highest positive-family policy_improvable_share and positive actual-executed contribution.",
      "research_line": "recovery-with-relapse refinement"
    },
    {
      "bucket": "bounded secondary research",
      "rationale": "full-year 2022 interaction test controls admissibility",
      "research_line": "hazard as slow-stress timing assistant"
    },
    {
      "bucket": "bounded secondary research",
      "rationale": "positive contribution, lower improvable share than recovery-with-relapse",
      "research_line": "2018-style drawdown refinement"
    },
    {
      "bucket": "boundary / disclosure only",
      "rationale": "account-boundary item under spot-only daily-signal assumptions",
      "research_line": "2020-like bounded observation only"
    },
    {
      "bucket": "boundary / disclosure only",
      "rationale": "liquidity-vacuum and execution-dominated under current assumptions",
      "research_line": "2015-style bounded observation only"
    },
    {
      "bucket": "monitoring only",
      "rationale": "count diagnostic remains live but cannot score budget",
      "research_line": "false re-entry monitoring"
    },
    {
      "bucket": "monitoring only",
      "rationale": "not active unless separately justified by execution research evidence",
      "research_line": "execution gate placeholder"
    }
  ],
  "decision": "BOUNDED_BUDGET_ALLOCATION_IS_NOW_DECISION_READY",
  "policy_improvable_ranking_snapshot": [
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
  "summary": "Budget allocation is reconstructed from improvable share, contribution, boundary status, and interaction feasibility."
}
```
