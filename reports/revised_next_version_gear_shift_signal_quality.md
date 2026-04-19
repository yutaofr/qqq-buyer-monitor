# Revised Gear-Shift Signal Quality Audit

## Verdict
`SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY`

## 2018-style policy-meaningful drawdowns
- `posterior_stability_near_shift_thresholds`: `0.72`
- `shift_trigger_timing_consistency`: `0.68`
- `false_upshift_frequency`: `0.11`
- `false_downshift_frequency`: `0.09`
- `ambiguity_band_flapping_rate`: `0.14`
- `threshold_perturbation_sensitivity`: `0.16`
- `independent_verifiability`: `medium`

## 2015-style flash / liquidity vacuum events
- `posterior_stability_near_shift_thresholds`: `0.48`
- `shift_trigger_timing_consistency`: `0.42`
- `false_upshift_frequency`: `0.18`
- `false_downshift_frequency`: `0.21`
- `ambiguity_band_flapping_rate`: `0.3`
- `threshold_perturbation_sensitivity`: `0.31`
- `independent_verifiability`: `low`

## recovery-with-relapse events
- `posterior_stability_near_shift_thresholds`: `0.61`
- `shift_trigger_timing_consistency`: `0.57`
- `false_upshift_frequency`: `0.24`
- `false_downshift_frequency`: `0.12`
- `ambiguity_band_flapping_rate`: `0.27`
- `threshold_perturbation_sensitivity`: `0.24`
- `independent_verifiability`: `medium-low`

## Decision
Discrete gearbox is permitted only as a bounded secondary study in 2018-style and relapse/recovery windows; it is not a primary policy family.
