# Boundary-State Layer

## Decision
`BOUNDARY_LAYER_IS_HONEST_AND_CLEAR`

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "dashboard_visual_distinction": "separate boundary banner and warning copy, not an ordinary stage tile",
  "decision": "BOUNDARY_LAYER_IS_HONEST_AND_CLEAR",
  "evidence_shown": [
    "boundary_pressure",
    "volatility_percentile",
    "hazard_delta_5d",
    "relapse_flag"
  ],
  "hard_rule_result": "Boundary warnings are never presented as the system knowing what to do.",
  "not_to_infer": [
    "automatic orders",
    "hard leverage target",
    "exact turning-point prediction",
    "solved execution/account physics"
  ],
  "observed_boundary_day_share": 0.006051,
  "trigger_conditions": [
    "five-day negative gap pressure >= 7%",
    "extreme volatility percentile with fast hazard acceleration",
    "high stress score with meaningful gap pressure"
  ],
  "warning_text": "FAST_CASCADE_BOUNDARY is a boundary warning, not a solved decision regime."
}
```
