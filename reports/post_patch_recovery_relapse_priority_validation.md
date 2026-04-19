# Post-Patch Recovery-With-Relapse Priority Validation

## Summary
Recovery-with-relapse is elevated because it has positive contribution and the highest positive-family improvable share.

## Decision
`RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "decision": "RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS",
  "direct_comparison": [
    {
      "event_family": "recovery-with-relapse",
      "expected_bounded_research_payoff": 0.145387,
      "interaction_stability": "STABLE_ENOUGH_FOR_BOUNDED_RESEARCH",
      "policy_contribution": 0.125655,
      "policy_improvable_share": 0.145387
    },
    {
      "event_family": "slower structural stress",
      "expected_bounded_research_payoff": 0.097055,
      "interaction_stability": "REQUIRES_SUBTYPE_SPLIT",
      "policy_contribution": 0.516533,
      "policy_improvable_share": 0.097055
    },
    {
      "event_family": "2018-style partially containable drawdown",
      "expected_bounded_research_payoff": 0.067592,
      "interaction_stability": "STABLE_ENOUGH_FOR_BOUNDED_RESEARCH",
      "policy_contribution": 0.078835,
      "policy_improvable_share": 0.067592
    }
  ],
  "explicit_elevation_justification": "Holding recovery-with-relapse below elevated status would violate the post-patch rule: it has the highest positive-family policy_improvable_share and positive actual-executed contribution.",
  "recovery_with_relapse": {
    "dominant_remaining_mechanism": "false_release_risk_and_recovery_miss_are_jointly_active",
    "policy_contribution": 0.125655,
    "policy_improvable_share": 0.145387,
    "positive_edge_sufficient_for_further_budget": true,
    "release_relapse_sensitivity": "HIGH: release confirmation must avoid bear-rally traps without suppressing real recovery",
    "residual_unrepaired_share": 0.706836
  },
  "summary": "Recovery-with-relapse is elevated because it has positive contribution and the highest positive-family improvable share."
}
```
