# Feature Engineering Alignment

## Decision
`FEATURE_STACK_IS_ALIGNED_WITH_NAVIGATOR_OBJECTIVE`

## Summary
The product-facing feature stack retains only stage, transition, repair, relapse, and boundary evidence; beta/allocation features are frozen out.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "FEATURE_STACK_IS_ALIGNED_WITH_NAVIGATOR_OBJECTIVE",
  "feature_families": {
    "boundary_pressure_gap_stress_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "FAST_CASCADE_BOUNDARY"
      ],
      "noise_amplification": "five-day negative gap pressure avoids one-tick panic",
      "post_close_stable": true,
      "role": "boundary logic"
    },
    "breadth_derived_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "EXPANSION",
        "LATE_CYCLE",
        "STRESS",
        "RECOVERY"
      ],
      "noise_amplification": "10-day delta suppresses minor oscillation",
      "post_close_stable": true,
      "role": "level and repair confirmation"
    },
    "hazard_derived_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "LATE_CYCLE",
        "STRESS",
        "FAST_CASCADE_BOUNDARY"
      ],
      "noise_amplification": "controlled by 5-day delta and smoothing",
      "post_close_stable": true,
      "role": "level and transition"
    },
    "relapse_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "STRESS",
        "RECOVERY"
      ],
      "noise_amplification": "requires recent repair and renewed deterioration",
      "post_close_stable": true,
      "role": "transition and warning"
    },
    "repair_confirmation_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "RECOVERY"
      ],
      "noise_amplification": "requires recent stress plus breadth or volatility repair",
      "post_close_stable": true,
      "role": "transition and repair"
    },
    "stress_persistence_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "STRESS"
      ],
      "noise_amplification": "run-length state reduces flapping",
      "post_close_stable": true,
      "role": "level and persistence"
    },
    "target_beta_allocation_features": {
      "classification": "REMOVE_OR_FREEZE",
      "informs_stages": [],
      "noise_amplification": "not admitted into product stage engine",
      "post_close_stable": false,
      "role": "legacy automatic-policy translation only"
    },
    "volatility_percentile_delta_features": {
      "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
      "informs_stages": [
        "LATE_CYCLE",
        "STRESS",
        "RECOVERY",
        "FAST_CASCADE_BOUNDARY"
      ],
      "noise_amplification": "rolling percentile plus delta, not raw VIX twitch",
      "post_close_stable": true,
      "role": "level, transition, boundary"
    }
  },
  "hard_rule_result": "No retained product feature is justified solely by old policy contribution.",
  "summary": "The product-facing feature stack retains only stage, transition, repair, relapse, and boundary evidence; beta/allocation features are frozen out."
}
```
