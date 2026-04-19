# Transition Urgency And Action-Relevance Layer

## Decision
`URGENCY_AND_ACTION_LAYER_IS_PRODUCT_USEFUL`

## Summary
Urgency comes from probability motion and evidence deltas; action relevance comes from transition materiality and alert suppression.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "action_relevance_band_values": [
    "NO_ACTION_ZONE",
    "WATCH_CLOSELY",
    "PREPARE_TO_ADJUST",
    "HIGH_CONVICTION_TRANSITION"
  ],
  "decision": "URGENCY_AND_ACTION_LAYER_IS_PRODUCT_USEFUL",
  "hard_rule_result": "Action band tells the user whether review is warranted; it never specifies a leverage number.",
  "observed_distribution": {
    "action_band_counts": {
      "HIGH_CONVICTION_TRANSITION": 184,
      "NO_ACTION_ZONE": 3367,
      "PREPARE_TO_ADJUST": 837,
      "WATCH_CLOSELY": 2223
    },
    "urgency_counts": {
      "HIGH": 1125,
      "LOW": 3413,
      "RISING": 1890,
      "UNSTABLE": 183
    }
  },
  "required_checks": {
    "action_band_distinct_from_stage_label": true,
    "action_band_not_hidden_leverage_signal": true,
    "escalates_medium_large_transitions": true,
    "suppresses_low_grade_noise": true,
    "urgency_distinct_from_confidence": true
  },
  "summary": "Urgency comes from probability motion and evidence deltas; action relevance comes from transition materiality and alert suppression.",
  "transition_urgency_values": [
    "LOW",
    "RISING",
    "HIGH",
    "UNSTABLE"
  ]
}
```
