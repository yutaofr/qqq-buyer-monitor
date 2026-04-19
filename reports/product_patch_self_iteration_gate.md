# Product Patch Self Iteration Gate

## Decision
`SELF_ITERATION_COMPLETED_BUT_PRODUCT_REMAINS_LIMITED`

## Summary
Self-iteration was performed by comparing multiple bounded patch variants and selecting the best candidate under the product criteria rather than a PnL objective.

## Machine-Readable Snapshot
```json
{
  "criteria": [
    {
      "criterion": "false recovery declaration rate improves",
      "failure": true,
      "patch_applied": "recovery_compliance_guarded",
      "result_after_patch": 0.0
    },
    {
      "criterion": "RECOVERY calibration gap improves",
      "failure": false,
      "patch_applied": "recovery_compliance_guarded",
      "result_after_patch": 0.157712
    },
    {
      "criterion": "STRESS / LATE_CYCLE are not materially degraded",
      "failure": false,
      "patch_applied": "recovery_compliance_guarded",
      "result_after_patch": {
        "late_cycle_accuracy_delta": 0.0,
        "not_materially_degraded": true,
        "stress_accuracy_delta": 0.0
      }
    },
    {
      "criterion": "probability diffusion is not replaced by fake confidence",
      "failure": false,
      "patch_applied": "recovery_compliance_guarded",
      "result_after_patch": {
        "average_entropy_by_stage": {
          "EXPANSION": 0.551947,
          "FAST_CASCADE_BOUNDARY": 0.719811,
          "LATE_CYCLE": 0.745645,
          "STRESS": 0.641287
        },
        "confidence_concentration_profile": {
          "CONCENTRATED": 3621,
          "DIFFUSE_OR_UNSTABLE": 835,
          "MIXED": 512,
          "MODERATELY_CONCENTRATED": 1643
        },
        "critical_stage_diffuse_share": 0.05748,
        "diffuse_or_unstable_count": 835,
        "dominant_minus_secondary_margin": {
          "EXPANSION": 0.537688,
          "FAST_CASCADE_BOUNDARY": 0.182852,
          "LATE_CYCLE": 0.227738,
          "STRESS": 0.376463
        },
        "dominant_stage_overconfidence_rate": 0.033429,
        "one_day_reversal_rate": 0.003783
      }
    },
    {
      "criterion": "index.html remains misaligned or incomplete",
      "failure": false,
      "patch_applied": "index.html and web exporter realigned",
      "result_after_patch": "INDEX_HTML_AND_UI_ARE_FULLY_ALIGNED"
    },
    {
      "criterion": "full product path remains inconsistent",
      "failure": false,
      "patch_applied": "README/export/UI path audit and repair",
      "result_after_patch": "FULL_PRODUCT_PATH_IS_INTERNALLY_CONSISTENT"
    }
  ],
  "decision": "SELF_ITERATION_COMPLETED_BUT_PRODUCT_REMAINS_LIMITED",
  "iteration_attempts": [
    {
      "passes_patch_targets": false,
      "score": 0.021173,
      "variant": "recovery_compliance_light"
    },
    {
      "passes_patch_targets": false,
      "score": 0.032258,
      "variant": "recovery_compliance_balanced"
    },
    {
      "passes_patch_targets": false,
      "score": 0.040044,
      "variant": "recovery_compliance_guarded"
    }
  ],
  "summary": "Self-iteration was performed by comparing multiple bounded patch variants and selecting the best candidate under the product criteria rather than a PnL objective."
}
```
