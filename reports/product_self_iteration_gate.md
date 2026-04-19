# Self-Iteration Gate

## Decision
`SELF_ITERATION_NOT_REQUIRED_PRODUCT_MEETS_STANDARD`

## Summary
Self-iteration is explicit and threshold-driven; the product may not stop at an interesting but unstable process.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "SELF_ITERATION_NOT_REQUIRED_PRODUCT_MEETS_STANDARD",
  "failed_criteria": [],
  "hard_rule_result": "The product either meets the standard or explicitly fails.",
  "iteration_attempts": [
    {
      "alert_fatigue_proxy_rate": 0.038572,
      "boundary_passthrough": 0.88,
      "config_name": "calibrated_product",
      "iteration": 1,
      "multiclass_brier_score": 0.447236,
      "multiclass_ece": 0.093383,
      "passes": true,
      "smoothing_alpha": 0.36,
      "stage_flapping_rate": 0.05416,
      "temperature": 0.9
    }
  ],
  "iteration_triggers": {
    "action_relevance_behaves_like_leverage": false,
    "dashboard_read_time_exceeds_60_seconds": false,
    "documentation_mission_drifted": false,
    "one_day_reversal_rate_too_high": false,
    "probability_calibration_fails_thresholds": false,
    "stage_flapping_exceeds_threshold": false,
    "urgency_not_separate_from_confidence": false
  },
  "summary": "Self-iteration is explicit and threshold-driven; the product may not stop at an interesting but unstable process."
}
```
