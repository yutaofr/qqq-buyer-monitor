# Product Patch Calibration Failure Audit

## Decision
`CALIBRATION_FAILURES_ARE_PRECISELY_LOCALIZED`

## Summary
RECOVERY is severely underconfident, STRESS remains only moderately reliable, FAST_CASCADE_BOUNDARY is under-asserted during acute windows, and decision-critical middle states remain too diffuse.

## Machine-Readable Snapshot
```json
{
  "confidence_false_declaration_alignment": {
    "RECOVERY": {
      "confidence_gap": 0.140514,
      "false_recovery_10d": 0.0,
      "logical_alignment": "misaligned_low_confidence_still_allows_false_all_clear"
    },
    "STRESS": {
      "confidence_gap": -0.273493,
      "false_stress_dominant_rate": 0.016941,
      "logical_alignment": "roughly_aligned_but_acute_events_are_still_smoothed"
    }
  },
  "decision": "CALIBRATION_FAILURES_ARE_PRECISELY_LOCALIZED",
  "diffuse_stages": [],
  "false_declaration_rates": {
    "FAST_CASCADE_BOUNDARY": {
      "false_boundary_dominant_rate": 0.000605
    },
    "LATE_CYCLE": {
      "acute_misanchored_as_late_cycle_rate": 0.006353
    },
    "RECOVERY": {
      "false_recovery_10d": 0.0
    },
    "STRESS": {
      "false_stress_dominant_rate": 0.016941
    }
  },
  "overconfident_stages": [
    "RECOVERY",
    "FAST_CASCADE_BOUNDARY"
  ],
  "stage_metrics": {
    "EXPANSION": {
      "accuracy": 0.997411,
      "classwise_brier_component": 0.151969,
      "confidence_gap": -0.195835,
      "dominant_label_frequency": {
        "EXPANSION": 0.997411,
        "LATE_CYCLE": 0.002589
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.006287,
        "mean_entropy": 0.432748,
        "mean_top1_margin": 0.696473
      },
      "mean_confidence": 0.801576,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 1040,
            "gap": 0.08067,
            "mean_confidence": 0.08067,
            "observed_frequency": 0.0
          },
          {
            "bin": "0.2-0.4",
            "count": 789,
            "gap": 0.299619,
            "mean_confidence": 0.305956,
            "observed_frequency": 0.006337
          },
          {
            "bin": "0.4-0.6",
            "count": 1256,
            "gap": 0.395726,
            "mean_confidence": 0.502414,
            "observed_frequency": 0.106688
          },
          {
            "bin": "0.6-0.8",
            "count": 1742,
            "gap": 0.152187,
            "mean_confidence": 0.71361,
            "observed_frequency": 0.561424
          },
          {
            "bin": "0.8-1.0",
            "count": 1784,
            "gap": -0.025399,
            "mean_confidence": 0.864175,
            "observed_frequency": 0.889574
          }
        ],
        "max_abs_gap": 0.395726,
        "sample_count": 6611,
        "weighted_gap": 0.170587
      },
      "support": 2704
    },
    "FAST_CASCADE_BOUNDARY": {
      "accuracy": 0.118943,
      "classwise_brier_component": 0.022539,
      "confidence_gap": 0.120955,
      "dominant_label_frequency": {
        "EXPANSION": 0.004405,
        "FAST_CASCADE_BOUNDARY": 0.118943,
        "LATE_CYCLE": 0.229075,
        "STRESS": 0.647577
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.132159,
        "mean_entropy": 0.646072,
        "mean_top1_margin": 0.333093
      },
      "mean_confidence": 0.239897,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 6455,
            "gap": 0.023491,
            "mean_confidence": 0.038518,
            "observed_frequency": 0.015027
          },
          {
            "bin": "0.2-0.4",
            "count": 132,
            "gap": -0.545212,
            "mean_confidence": 0.27297,
            "observed_frequency": 0.818182
          },
          {
            "bin": "0.4-0.6",
            "count": 19,
            "gap": -0.428126,
            "mean_confidence": 0.466611,
            "observed_frequency": 0.894737
          },
          {
            "bin": "0.6-0.8",
            "count": 5,
            "gap": -0.341456,
            "mean_confidence": 0.658544,
            "observed_frequency": 1.0
          }
        ],
        "max_abs_gap": 0.545212,
        "sample_count": 6611,
        "weighted_gap": 0.035311
      },
      "support": 227
    },
    "LATE_CYCLE": {
      "accuracy": 0.311605,
      "classwise_brier_component": 0.165481,
      "confidence_gap": 0.021532,
      "dominant_label_frequency": {
        "EXPANSION": 0.671605,
        "FAST_CASCADE_BOUNDARY": 0.001481,
        "LATE_CYCLE": 0.311605,
        "STRESS": 0.015309
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.221728,
        "mean_entropy": 0.722294,
        "mean_top1_margin": 0.278146
      },
      "mean_confidence": 0.333137,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 4082,
            "gap": -0.003012,
            "mean_confidence": 0.103064,
            "observed_frequency": 0.106075
          },
          {
            "bin": "0.2-0.4",
            "count": 1760,
            "gap": -0.290675,
            "mean_confidence": 0.28262,
            "observed_frequency": 0.573295
          },
          {
            "bin": "0.4-0.6",
            "count": 586,
            "gap": -0.24088,
            "mean_confidence": 0.480963,
            "observed_frequency": 0.721843
          },
          {
            "bin": "0.6-0.8",
            "count": 180,
            "gap": -0.208647,
            "mean_confidence": 0.663576,
            "observed_frequency": 0.872222
          },
          {
            "bin": "0.8-1.0",
            "count": 3,
            "gap": -0.194006,
            "mean_confidence": 0.805994,
            "observed_frequency": 1.0
          }
        ],
        "max_abs_gap": 0.290675,
        "sample_count": 6611,
        "weighted_gap": 0.106365
      },
      "support": 2025
    },
    "RECOVERY": {
      "accuracy": 0.0,
      "classwise_brier_component": 0.122978,
      "confidence_gap": 0.140514,
      "dominant_label_frequency": {
        "EXPANSION": 0.83318,
        "LATE_CYCLE": 0.092166,
        "STRESS": 0.074654
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.217512,
        "mean_entropy": 0.680184,
        "mean_top1_margin": 0.42356
      },
      "mean_confidence": 0.140514,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 6432,
            "gap": -0.099704,
            "mean_confidence": 0.042709,
            "observed_frequency": 0.142413
          },
          {
            "bin": "0.2-0.4",
            "count": 179,
            "gap": -0.721562,
            "mean_confidence": 0.222572,
            "observed_frequency": 0.944134
          }
        ],
        "max_abs_gap": 0.721562,
        "sample_count": 6611,
        "weighted_gap": 0.116541
      },
      "support": 1085
    },
    "STRESS": {
      "accuracy": 0.847368,
      "classwise_brier_component": 0.040004,
      "confidence_gap": -0.273493,
      "dominant_label_frequency": {
        "EXPANSION": 0.012281,
        "FAST_CASCADE_BOUNDARY": 0.001754,
        "LATE_CYCLE": 0.138596,
        "STRESS": 0.847368
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.157895,
        "mean_entropy": 0.643689,
        "mean_top1_margin": 0.362026
      },
      "mean_confidence": 0.573876,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 5505,
            "gap": 0.071174,
            "mean_confidence": 0.071537,
            "observed_frequency": 0.000363
          },
          {
            "bin": "0.2-0.4",
            "count": 425,
            "gap": 0.028195,
            "mean_confidence": 0.279959,
            "observed_frequency": 0.251765
          },
          {
            "bin": "0.4-0.6",
            "count": 302,
            "gap": -0.129649,
            "mean_confidence": 0.506112,
            "observed_frequency": 0.635762
          },
          {
            "bin": "0.6-0.8",
            "count": 331,
            "gap": 0.010966,
            "mean_confidence": 0.699788,
            "observed_frequency": 0.688822
          },
          {
            "bin": "0.8-1.0",
            "count": 48,
            "gap": -0.033143,
            "mean_confidence": 0.821024,
            "observed_frequency": 0.854167
          }
        ],
        "max_abs_gap": 0.129649,
        "sample_count": 6611,
        "weighted_gap": 0.067792
      },
      "support": 570
    }
  },
  "summary": "RECOVERY is severely underconfident, STRESS remains only moderately reliable, FAST_CASCADE_BOUNDARY is under-asserted during acute windows, and decision-critical middle states remain too diffuse.",
  "underconfident_stages": [
    "EXPANSION",
    "STRESS"
  ]
}
```
