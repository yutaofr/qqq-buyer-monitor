# pi_stress Phase 3 Posterior Family Comparison

## Selection Rule

Rank by economic decision-surface quality: regime separability, ordinary-correction behavior, stress/crisis/recovery behavior, threshold robustness, downstream proxy placeholder, and explainability. Brier/AUC alone are not sufficient.

## Family Summary

| Family | Type | Stress vs ordinary gap | Ordinary band | Threshold sensitivity | Gates | Ranking score |
|---|---|---:|---:|---:|---:|---:|
| `C9_baseline_reference` | C9-style binary structural confirmation | 0.1459 | 0.0479 | 0.9340 | 4/7 | 4.3970 |
| `multiclass_regime_posterior` | Multi-class regime posterior model | 0.2034 | 0.1617 | 0.8771 | 5/7 | 4.9791 |
| `hierarchical_stress_posterior` | Hierarchical posterior | 0.2151 | 0.0019 | 0.3267 | 7/7 | 8.2368 |
| `two_stage_anomaly_severity` | Two-stage anomaly and crisis-severity model | 0.2805 | 0.0010 | 0.2079 | 7/7 | 8.2451 |
| `ordinal_state_transition_posterior` | Ordinal stress model with transition memory | 0.2108 | 0.0116 | 0.4838 | 6/7 | 6.8212 |

## Gate Results

| Family | Gate | Status |
|---|---|---|
| `C9_baseline_reference` | Gate1_ordinary_correction_separation | FAIL |
| `C9_baseline_reference` | Gate2_structural_stress_capture | PASS |
| `C9_baseline_reference` | Gate3_acute_crisis_capture | PASS |
| `C9_baseline_reference` | Gate4_recovery_distinction | FAIL |
| `C9_baseline_reference` | Gate5_threshold_robustness | FAIL |
| `C9_baseline_reference` | Gate6_downstream_beta_compatibility | PASS |
| `C9_baseline_reference` | Gate7_explainability | PASS |
| `multiclass_regime_posterior` | Gate1_ordinary_correction_separation | FAIL |
| `multiclass_regime_posterior` | Gate2_structural_stress_capture | PASS |
| `multiclass_regime_posterior` | Gate3_acute_crisis_capture | PASS |
| `multiclass_regime_posterior` | Gate4_recovery_distinction | PASS |
| `multiclass_regime_posterior` | Gate5_threshold_robustness | PASS |
| `multiclass_regime_posterior` | Gate6_downstream_beta_compatibility | FAIL |
| `multiclass_regime_posterior` | Gate7_explainability | PASS |
| `hierarchical_stress_posterior` | Gate1_ordinary_correction_separation | PASS |
| `hierarchical_stress_posterior` | Gate2_structural_stress_capture | PASS |
| `hierarchical_stress_posterior` | Gate3_acute_crisis_capture | PASS |
| `hierarchical_stress_posterior` | Gate4_recovery_distinction | PASS |
| `hierarchical_stress_posterior` | Gate5_threshold_robustness | PASS |
| `hierarchical_stress_posterior` | Gate6_downstream_beta_compatibility | PASS |
| `hierarchical_stress_posterior` | Gate7_explainability | PASS |
| `two_stage_anomaly_severity` | Gate1_ordinary_correction_separation | PASS |
| `two_stage_anomaly_severity` | Gate2_structural_stress_capture | PASS |
| `two_stage_anomaly_severity` | Gate3_acute_crisis_capture | PASS |
| `two_stage_anomaly_severity` | Gate4_recovery_distinction | PASS |
| `two_stage_anomaly_severity` | Gate5_threshold_robustness | PASS |
| `two_stage_anomaly_severity` | Gate6_downstream_beta_compatibility | PASS |
| `two_stage_anomaly_severity` | Gate7_explainability | PASS |
| `ordinal_state_transition_posterior` | Gate1_ordinary_correction_separation | PASS |
| `ordinal_state_transition_posterior` | Gate2_structural_stress_capture | PASS |
| `ordinal_state_transition_posterior` | Gate3_acute_crisis_capture | PASS |
| `ordinal_state_transition_posterior` | Gate4_recovery_distinction | FAIL |
| `ordinal_state_transition_posterior` | Gate5_threshold_robustness | PASS |
| `ordinal_state_transition_posterior` | Gate6_downstream_beta_compatibility | PASS |
| `ordinal_state_transition_posterior` | Gate7_explainability | PASS |

## Hypothesis Test

`YES`: {'c9_stress_vs_ordinary_gap': 0.14586838149777737, 'best_stress_vs_ordinary_gap': 0.28047340426025424, 'c9_ordinary_band': 0.04794188861985472, 'best_ordinary_band': 0.0009685230024213075}
