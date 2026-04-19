# Frontier Slower Structural Subtype Transfer Audit

## Summary
Subtype splitting improves clarity but raises path-fragility risk.

## Decision
`SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_USEFUL_BUT_PATH_FRAGILE`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "answers": {
    "does_2008_gain_transfer_to_2022_h1": {
      "sign_stable": true,
      "target_policy_improvable_share": 0.067316,
      "transfer_ratio": 0.541356
    },
    "does_2022_h1_structure_transfer_to_2008": {
      "sign_stable": true,
      "target_policy_improvable_share": 0.124347,
      "transfer_ratio": 1.847213
    },
    "primary_status_allowed": false,
    "subtype_splitting_role": "scientific_clarity_with_curve_fitting_risk"
  },
  "decision": "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_USEFUL_BUT_PATH_FRAGILE",
  "subtype_rows": [
    {
      "cross_subtype_target": "2022 H1 structural stress",
      "cross_subtype_transfer_result": {
        "sign_stable": true,
        "target_policy_improvable_share": 0.067316,
        "transfer_ratio": 0.541356
      },
      "event_name": "2008 financial crisis stress",
      "gains_subtype_specific_only": true,
      "in_sample_policy_contribution": 0.345089,
      "in_sample_policy_improvable_share": 0.124347,
      "residual_concentration_path_specific": false,
      "scientifically_admissible": "BOUNDED_SECONDARY_ONLY",
      "subtype": "monotonic structural stress"
    },
    {
      "cross_subtype_target": "2008 financial crisis stress",
      "cross_subtype_transfer_result": {
        "sign_stable": true,
        "target_policy_improvable_share": 0.124347,
        "transfer_ratio": 1.847213
      },
      "event_name": "2022 H1 structural stress",
      "gains_subtype_specific_only": false,
      "in_sample_policy_contribution": 0.171444,
      "in_sample_policy_improvable_share": 0.067316,
      "residual_concentration_path_specific": false,
      "scientifically_admissible": "TRANSFER_AWARE_ADMISSIBLE",
      "subtype": "multi-wave structural stress"
    }
  ],
  "summary": "Subtype splitting improves clarity but raises path-fragility risk."
}
```
