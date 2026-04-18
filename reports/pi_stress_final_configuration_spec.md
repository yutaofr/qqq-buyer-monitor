# pi_stress Final Configuration Spec

## FINAL_SELECTED_CONFIGURATION

This is the single evaluated end-state configuration. It is not approved for deployment because the hard gate fails.

```json
{
  "hysteresis_config": null,
  "rollback_mode": "legacy_topology stress posterior mode plus legacy_fixed_0_50 policy, emergency restoration only",
  "selected_calibrator": "platt",
  "selected_candidate": "C9_structural_confirmation_isotonic",
  "selected_policy_mode": "calibrated_fixed_threshold",
  "selected_threshold": 0.35
}
```

## Policy Contract

The policy uses only the calibrated pi_stress posterior and a fixed threshold. No calendar episode patching and no raw macro or market feature gate is part of the configuration.
