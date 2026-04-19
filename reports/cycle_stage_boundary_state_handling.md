# Cycle Stage Boundary State Handling

## Decision
`BOUNDARY_STATE_HANDLING_IS_HONEST_AND_USEFUL`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "BOUNDARY_STATE_HANDLING_IS_HONEST_AND_USEFUL",
  "detection_criteria": [
    "five-day negative gap pressure >= 7%",
    "extreme volatility percentile with accelerating hazard",
    "high stress with gap pressure"
  ],
  "hard_rule": "Boundary state may not masquerade as a solved decision regime.",
  "not_to_infer": "Do not infer that the system solved survivability, exact turning points, or target leverage.",
  "trigger_evidence": [
    "gap_pressure",
    "volatility_percentile",
    "hazard_delta",
    "stress_score"
  ],
  "warning_language": "Fast-cascade or gap-dominated conditions are active; automatic strategy logic is not trustworthy here.",
  "why_not_ordinary_stage": "The dominant issue is execution/account-boundary realism, not cycle-stage finesse."
}
```
