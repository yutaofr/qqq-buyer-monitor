# Probability Calibration And Distribution Quality

## Decision
`PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD`

## Summary
Stage probabilities are evaluated as probabilities against a market-structure reference label set; no PnL objective is used.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD",
  "entropy_concentration_diagnostics": {
    "concentration_counts": {
      "CONCENTRATED": 3342,
      "DIFFUSE_OR_UNSTABLE": 984,
      "MIXED": 541,
      "MODERATELY_CONCENTRATED": 1744
    },
    "mean_entropy_by_reference_stage": {
      "EXPANSION": 0.456289,
      "FAST_CASCADE_BOUNDARY": 0.646104,
      "LATE_CYCLE": 0.734674,
      "RECOVERY": 0.711714,
      "STRESS": 0.652191
    },
    "mean_top1_by_reference_stage": {
      "EXPANSION": 0.789428,
      "FAST_CASCADE_BOUNDARY": 0.570301,
      "LATE_CYCLE": 0.528158,
      "RECOVERY": 0.525092,
      "STRESS": 0.593013
    }
  },
  "evaluation_layers": [
    {
      "dominant_stage_counts": {
        "EXPANSION": 4721,
        "FAST_CASCADE_BOUNDARY": 40,
        "LATE_CYCLE": 842,
        "RECOVERY": 269,
        "STRESS": 739
      },
      "mean_entropy": 0.606889,
      "multiclass_brier_score": 0.447236,
      "multiclass_ece": 0.093383,
      "rows": 6611,
      "window": "Full history"
    },
    {
      "dominant_stage_counts": {
        "EXPANSION": 10,
        "FAST_CASCADE_BOUNDARY": 3,
        "LATE_CYCLE": 2,
        "STRESS": 70
      },
      "mean_entropy": 0.61394,
      "multiclass_brier_score": 0.681433,
      "multiclass_ece": 0.2021,
      "rows": 85,
      "window": "2008 crisis"
    },
    {
      "dominant_stage_counts": {
        "EXPANSION": 243,
        "LATE_CYCLE": 8
      },
      "mean_entropy": 0.543935,
      "multiclass_brier_score": 0.398524,
      "multiclass_ece": 0.22127,
      "rows": 251,
      "window": "Benign expansion period"
    },
    {
      "dominant_stage_counts": {
        "EXPANSION": 17,
        "LATE_CYCLE": 8,
        "STRESS": 19
      },
      "mean_entropy": 0.717563,
      "multiclass_brier_score": 0.466892,
      "multiclass_ece": 0.227039,
      "rows": 44,
      "window": "2022 relapse / recovery"
    },
    {
      "dominant_stage_counts": {
        "EXPANSION": 5,
        "FAST_CASCADE_BOUNDARY": 10,
        "LATE_CYCLE": 5,
        "RECOVERY": 11,
        "STRESS": 20
      },
      "mean_entropy": 0.686273,
      "multiclass_brier_score": 0.560633,
      "multiclass_ece": 0.199079,
      "rows": 51,
      "window": "COVID fast cascade"
    }
  ],
  "hard_rule_result": "self_iteration_gate_required_if_thresholds_fail",
  "metrics": {
    "boundary_false_confidence_rate": 0.000605,
    "classwise_brier_components": {
      "EXPANSION": 0.133378,
      "FAST_CASCADE_BOUNDARY": 0.021543,
      "LATE_CYCLE": 0.164866,
      "RECOVERY": 0.088606,
      "STRESS": 0.038843
    },
    "dominant_stage_overconfidence_rate": 0.011042,
    "log_loss_nll": 0.800009,
    "mean_normalized_entropy": 0.606889,
    "mean_top1_probability": 0.641557,
    "multiclass_brier_score": 0.447236,
    "multiclass_ece": 0.093383
  },
  "reliability_summaries_by_stage": {
    "EXPANSION": {
      "accuracy": 0.571065,
      "confidence_accuracy_gap": 0.117451,
      "count": 4721,
      "mean_confidence": 0.688517
    },
    "FAST_CASCADE_BOUNDARY": {
      "accuracy": 0.9,
      "confidence_accuracy_gap": -0.417575,
      "count": 40,
      "mean_confidence": 0.482425
    },
    "LATE_CYCLE": {
      "accuracy": 0.752969,
      "confidence_accuracy_gap": -0.253739,
      "count": 842,
      "mean_confidence": 0.49923
    },
    "RECOVERY": {
      "accuracy": 0.973978,
      "confidence_accuracy_gap": -0.551076,
      "count": 269,
      "mean_confidence": 0.422901
    },
    "STRESS": {
      "accuracy": 0.654939,
      "confidence_accuracy_gap": -0.06301,
      "count": 739,
      "mean_confidence": 0.591929
    }
  },
  "selected_iteration": {
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
  },
  "summary": "Stage probabilities are evaluated as probabilities against a market-structure reference label set; no PnL objective is used.",
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
