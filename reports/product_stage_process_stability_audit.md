# Stage-Process Stability Audit

## Decision
`STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE`

## Summary
The stage process is measured as a low-frequency human regime process, with flapping and alert fatigue treated as product failures.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE",
  "interpretation": {
    "are_transitions_persistent": true,
    "does_process_flap_too_often": false,
    "does_smoothing_hide_real_deterioration": false,
    "human_read": "Suitable for daily post-close review if action bands remain sparse."
  },
  "metrics": {
    "alert_fatigue_proxy_rate": 0.038572,
    "confidence_stability_decay_before_regime_shifts": {
      "mean_decay": 0.019831,
      "mean_margin_20d_before": 0.386815,
      "mean_margin_5d_after": 0.366983
    },
    "false_recovery_declaration_rate": 0.171004,
    "false_stress_escalation_rate": 0.016639,
    "mean_stage_persistence_days": 18.415042,
    "one_day_reversal_rate": 0.00575,
    "one_day_reversals": 38,
    "stage_flapping_rate": 0.05416,
    "transition_clustering_rate": 0.916201,
    "unstable_transition_frequency": 0.197852
  },
  "summary": "The stage process is measured as a low-frequency human regime process, with flapping and alert fatigue treated as product failures.",
  "thresholds": {
    "acceptable_multiclass_brier": 0.46,
    "acceptable_multiclass_ece": 0.18,
    "max_alert_fatigue_proxy_rate": 0.12,
    "max_one_day_reversal_rate": 0.01,
    "max_stage_flapping_rate": 0.055,
    "unacceptable_boundary_false_confidence_rate": 0.035,
    "unacceptable_overconfidence_rate": 0.08
  }
}
```
