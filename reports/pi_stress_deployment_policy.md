# pi_stress Deployment Policy

## Policy Modes

1. `legacy_fixed_0_50`: rollback-compatible historical trigger.
2. `calibrated_fixed_threshold`: single calibrated posterior threshold, default conservative threshold 0.35.
3. `threshold_policy_with_hysteresis`: recommended governed policy.

## Recommended Policy

```json
{
  "conservative_threshold": 0.35,
  "escalation_threshold": 0.5,
  "fallback_mode": "legacy_fixed_0_50",
  "hysteresis": {
    "enter_after_days": 2,
    "exit_after_days": 3,
    "exit_below_threshold": 0.2,
    "minimum_episode_days": 2
  },
  "mode": "threshold_policy_with_hysteresis",
  "monitoring_hooks": [
    "posterior_drift",
    "threshold_trigger_drift",
    "calibration_drift",
    "data_drift",
    "downstream_beta_pathology"
  ],
  "primary_threshold": 0.25,
  "warning_threshold": 0.2
}
```

Primary threshold: `0.25`.

Alternate conservative threshold: `0.35`.

Escalation threshold: `0.50`.

The primary threshold restores prolonged-stress capture but accepts a higher trigger rate. The conservative threshold reduces false-positive pressure but may reduce early episode coverage. The legacy 0.50 threshold is retained as fallback only; it is not approved as the sole operating policy because it under-captures 2022 H1.

## Monitoring Hooks

The policy artifact explicitly requires monitoring for posterior drift, threshold trigger drift, calibration drift, data drift, and downstream beta pathology.
