# Frontier Hazard Repositioning Transfer Audit

## Summary
Hazard is tested beyond 2022 H1; 2022-local non-damage is not treated as transfer proof.

## Decision
`HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "comparison_baseline": "exit-system-only baseline",
  "decision": "HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE",
  "recommended_role": "BOUNDED_ASSIST",
  "summary": "Hazard is tested beyond 2022 H1; 2022-local non-damage is not treated as transfer proof.",
  "validation_basis": "CROSS_PATH_NOT_2022_ONLY",
  "variant_rows": [
    {
      "budget_role": "BOUNDED_ASSIST",
      "cross_path_effects": [
        0.0,
        0.0,
        0.0
      ],
      "cross_path_net_effect": 0.0,
      "in_sample_h1_benefit": 0.041905,
      "in_sample_h2_relapse_drag": 0.0,
      "transfer_stability": "STABLE",
      "variant": "hazard_assist_unchanged_release"
    },
    {
      "budget_role": "BOUNDED_ASSIST",
      "cross_path_effects": [
        0.014379,
        0.003272,
        0.005236
      ],
      "cross_path_net_effect": 0.007629,
      "in_sample_h1_benefit": 0.149264,
      "in_sample_h2_relapse_drag": -0.057911,
      "transfer_stability": "STABLE",
      "variant": "hazard_assist_tightened_release"
    },
    {
      "budget_role": "BOUNDED_ASSIST",
      "cross_path_effects": [
        0.028757,
        0.006544,
        0.010471
      ],
      "cross_path_net_effect": 0.015257,
      "in_sample_h1_benefit": 0.161626,
      "in_sample_h2_relapse_drag": -0.045032,
      "transfer_stability": "STABLE",
      "variant": "hazard_assist_conservative_rerisk_confirmation"
    }
  ]
}
```
