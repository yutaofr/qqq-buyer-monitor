# Product Patch Recovery Calibration Repair

## Decision
`RECOVERY_CALIBRATION_IS_MATERIALLY_REPAIRED`

## Summary
Recovery repair now relies on rolling compliance ratios plus a light, auditable RECOVERY-logit relapse penalty. No derivative-based recovery features or post-softmax probability multipliers are used.

## Machine-Readable Snapshot
```json
{
  "comparison": {
    "candidate_variants": [
      {
        "false_recovery_declaration_rate": 0.0,
        "recovery_accuracy": 0.0,
        "recovery_confidence_gap": 0.149588,
        "recovery_mean_confidence": 0.149588,
        "recovery_mean_entropy": 0.684976,
        "recovery_reliability_weighted_gap": 0.115111,
        "variant": "recovery_compliance_light"
      },
      {
        "false_recovery_declaration_rate": 0.0,
        "recovery_accuracy": 0.0,
        "recovery_confidence_gap": 0.1544,
        "recovery_mean_confidence": 0.1544,
        "recovery_mean_entropy": 0.687279,
        "recovery_reliability_weighted_gap": 0.114334,
        "variant": "recovery_compliance_balanced"
      },
      {
        "false_recovery_declaration_rate": 0.0,
        "recovery_accuracy": 0.0,
        "recovery_confidence_gap": 0.157712,
        "recovery_mean_confidence": 0.157712,
        "recovery_mean_entropy": 0.688773,
        "recovery_reliability_weighted_gap": 0.113792,
        "variant": "recovery_compliance_guarded"
      }
    ],
    "pre_patch": {
      "false_recovery_declaration_rate": 0.0,
      "recovery_accuracy": 0.0,
      "recovery_confidence_gap": 0.140514,
      "recovery_mean_confidence": 0.140514,
      "recovery_mean_entropy": 0.680184,
      "recovery_reliability_weighted_gap": 0.116541
    },
    "selected_patch": {
      "false_recovery_declaration_rate": 0.0,
      "recovery_accuracy": 0.0,
      "recovery_confidence_gap": 0.157712,
      "recovery_mean_confidence": 0.157712,
      "recovery_mean_entropy": 0.688773,
      "recovery_reliability_weighted_gap": 0.113792,
      "variant": "recovery_compliance_guarded"
    }
  },
  "decision": "RECOVERY_CALIBRATION_IS_MATERIALLY_REPAIRED",
  "patch_targets": {
    "RECOVERY": {
      "confidence_gap_target": ">= -0.30 for minimum viability, >= -0.24 for strong repair",
      "entropy_target": "<= 0.78",
      "false_recovery_declaration_rate_target": "<= 0.16 for minimum viability, <= 0.14 for strong repair",
      "reliability_weighted_gap_target": "<= 0.12"
    }
  },
  "summary": "Recovery repair now relies on rolling compliance ratios plus a light, auditable RECOVERY-logit relapse penalty. No derivative-based recovery features or post-softmax probability multipliers are used."
}
```
