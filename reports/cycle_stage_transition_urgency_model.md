# Cycle Stage Transition Urgency Model

## Decision
`TRANSITION_URGENCY_MODEL_IS_USEFUL_AND_DISTINCT`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "TRANSITION_URGENCY_MODEL_IS_USEFUL_AND_DISTINCT",
  "drivers": [
    "change in hazard",
    "change in breadth",
    "change in volatility",
    "stress persistence",
    "repair evidence",
    "relapse warning intensity"
  ],
  "hard_rule": "Transition urgency may not be collapsed into stage confidence.",
  "separation_rule": "Transition urgency is computed from deltas, persistence, and relapse intensity; stage confidence is computed from label evidence.",
  "urgency_labels": [
    "HIGH",
    "LOW",
    "RISING",
    "UNSTABLE"
  ]
}
```
