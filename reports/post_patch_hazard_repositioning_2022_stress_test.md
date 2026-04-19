# Post-Patch Hazard Repositioning 2022 Stress Test

## Summary
Hazard repositioning is judged on the full 2022 path, not H1 in isolation.

## Decision
`HAZARD_REPOSITIONING_IS_VALID_FOR_SLOW_STRESS_ASSIST`

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "decision": "HAZARD_REPOSITIONING_IS_VALID_FOR_SLOW_STRESS_ASSIST",
  "formal_repositioning_allowed": true,
  "summary": "Hazard repositioning is judged on the full 2022 path, not H1 in isolation.",
  "variant_rows": [
    {
      "false_release_diagnostics": {
        "damage_after_unresolved_release": 0.029169,
        "release_count": 3,
        "release_while_unresolved": 2
      },
      "h1_contribution_change": 0.0,
      "h2_relapse_contribution_change": 0.0,
      "improves_one_segment_while_degrading_next": false,
      "net_2022_full_year_contribution": 0.0,
      "premature_re_risk_episodes": 2,
      "recovery_miss_change": 0,
      "variant": "baseline_repaired_exit_without_hazard"
    },
    {
      "false_release_diagnostics": {
        "damage_after_unresolved_release": 0.055146,
        "release_count": 4,
        "release_while_unresolved": 3
      },
      "h1_contribution_change": 0.041905,
      "h2_relapse_contribution_change": 0.0,
      "improves_one_segment_while_degrading_next": false,
      "net_2022_full_year_contribution": 0.041905,
      "premature_re_risk_episodes": 3,
      "recovery_miss_change": 0,
      "variant": "hazard_assist_unchanged_release"
    },
    {
      "false_release_diagnostics": {
        "damage_after_unresolved_release": 0.025977,
        "release_count": 3,
        "release_while_unresolved": 1
      },
      "h1_contribution_change": 0.149264,
      "h2_relapse_contribution_change": -0.057911,
      "improves_one_segment_while_degrading_next": true,
      "net_2022_full_year_contribution": 0.091353,
      "premature_re_risk_episodes": 1,
      "recovery_miss_change": 1,
      "variant": "hazard_assist_tightened_release"
    },
    {
      "false_release_diagnostics": {
        "damage_after_unresolved_release": 0.025977,
        "release_count": 3,
        "release_while_unresolved": 2
      },
      "h1_contribution_change": 0.161626,
      "h2_relapse_contribution_change": -0.045032,
      "improves_one_segment_while_degrading_next": true,
      "net_2022_full_year_contribution": 0.116594,
      "premature_re_risk_episodes": 2,
      "recovery_miss_change": 6,
      "variant": "hazard_assist_conservative_rerisk_confirmation"
    }
  ]
}
```
