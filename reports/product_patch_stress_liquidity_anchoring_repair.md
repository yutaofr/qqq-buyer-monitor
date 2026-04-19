# Product Patch Stress Liquidity Anchoring Repair

## Decision
`ACUTE_LIQUIDITY_EVENTS_ARE_NOW_PROPERLY_ANCHORED`

## Summary
Batch 2 does not intentionally broaden the STRESS or LATE_CYCLE model. This workstream is retained as a guardrail to confirm those classes are not materially degraded while RECOVERY is being patched.

## Machine-Readable Snapshot
```json
{
  "classwise_effect": {
    "FAST_CASCADE_BOUNDARY": {
      "accuracy": 0.118943,
      "classwise_brier_component": 0.02253,
      "confidence_gap": 0.121006,
      "dominant_label_frequency": {
        "EXPANSION": 0.004405,
        "FAST_CASCADE_BOUNDARY": 0.118943,
        "LATE_CYCLE": 0.229075,
        "STRESS": 0.647577
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.132159,
        "mean_entropy": 0.64515,
        "mean_top1_margin": 0.333216
      },
      "mean_confidence": 0.239949,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 6455,
            "gap": 0.023388,
            "mean_confidence": 0.038415,
            "observed_frequency": 0.015027
          },
          {
            "bin": "0.2-0.4",
            "count": 132,
            "gap": -0.545119,
            "mean_confidence": 0.273063,
            "observed_frequency": 0.818182
          },
          {
            "bin": "0.4-0.6",
            "count": 19,
            "gap": -0.428043,
            "mean_confidence": 0.466694,
            "observed_frequency": 0.894737
          },
          {
            "bin": "0.6-0.8",
            "count": 5,
            "gap": -0.341394,
            "mean_confidence": 0.658606,
            "observed_frequency": 1.0
          }
        ],
        "max_abs_gap": 0.545119,
        "sample_count": 6611,
        "weighted_gap": 0.035209
      },
      "support": 227
    },
    "LATE_CYCLE": {
      "accuracy": 0.311605,
      "classwise_brier_component": 0.165338,
      "confidence_gap": 0.021684,
      "dominant_label_frequency": {
        "EXPANSION": 0.672099,
        "FAST_CASCADE_BOUNDARY": 0.001481,
        "LATE_CYCLE": 0.311605,
        "STRESS": 0.014815
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.223704,
        "mean_entropy": 0.721059,
        "mean_top1_margin": 0.277851
      },
      "mean_confidence": 0.333289,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 4089,
            "gap": -0.003641,
            "mean_confidence": 0.102742,
            "observed_frequency": 0.106383
          },
          {
            "bin": "0.2-0.4",
            "count": 1753,
            "gap": -0.291195,
            "mean_confidence": 0.282678,
            "observed_frequency": 0.573873
          },
          {
            "bin": "0.4-0.6",
            "count": 586,
            "gap": -0.242308,
            "mean_confidence": 0.481241,
            "observed_frequency": 0.723549
          },
          {
            "bin": "0.6-0.8",
            "count": 180,
            "gap": -0.207889,
            "mean_confidence": 0.664333,
            "observed_frequency": 0.872222
          },
          {
            "bin": "0.8-1.0",
            "count": 3,
            "gap": -0.193354,
            "mean_confidence": 0.806646,
            "observed_frequency": 1.0
          }
        ],
        "max_abs_gap": 0.291195,
        "sample_count": 6611,
        "weighted_gap": 0.106693
      },
      "support": 2025
    },
    "STRESS": {
      "accuracy": 0.847368,
      "classwise_brier_component": 0.039981,
      "confidence_gap": -0.272993,
      "dominant_label_frequency": {
        "EXPANSION": 0.012281,
        "FAST_CASCADE_BOUNDARY": 0.001754,
        "LATE_CYCLE": 0.138596,
        "STRESS": 0.847368
      },
      "entropy_concentration_summary": {
        "diffuse_or_unstable_share": 0.159649,
        "mean_entropy": 0.641926,
        "mean_top1_margin": 0.362305
      },
      "mean_confidence": 0.574375,
      "reliability_curve_summary": {
        "bins": [
          {
            "bin": "0.0-0.2",
            "count": 5503,
            "gap": 0.070896,
            "mean_confidence": 0.071259,
            "observed_frequency": 0.000363
          },
          {
            "bin": "0.2-0.4",
            "count": 427,
            "gap": 0.029356,
            "mean_confidence": 0.279942,
            "observed_frequency": 0.250585
          },
          {
            "bin": "0.4-0.6",
            "count": 300,
            "gap": -0.130477,
            "mean_confidence": 0.50619,
            "observed_frequency": 0.636667
          },
          {
            "bin": "0.6-0.8",
            "count": 333,
            "gap": 0.012133,
            "mean_confidence": 0.699821,
            "observed_frequency": 0.687688
          },
          {
            "bin": "0.8-1.0",
            "count": 48,
            "gap": -0.032818,
            "mean_confidence": 0.821349,
            "observed_frequency": 0.854167
          }
        ],
        "max_abs_gap": 0.130477,
        "sample_count": 6611,
        "weighted_gap": 0.06768
      },
      "support": 570
    }
  },
  "decision": "ACUTE_LIQUIDITY_EVENTS_ARE_NOW_PROPERLY_ANCHORED",
  "event_comparison": {
    "2020 fast cascade": {
      "post_patch_dominant_stage_path": [
        {
          "days": 5,
          "stage": "EXPANSION",
          "start": "2020-02-19"
        },
        {
          "days": 2,
          "stage": "LATE_CYCLE",
          "start": "2020-02-26"
        },
        {
          "days": 2,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2020-02-28"
        },
        {
          "days": 4,
          "stage": "LATE_CYCLE",
          "start": "2020-03-03"
        },
        {
          "days": 7,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2020-03-09"
        },
        {
          "days": 21,
          "stage": "STRESS",
          "start": "2020-03-18"
        },
        {
          "days": 5,
          "stage": "EXPANSION",
          "start": "2020-04-17"
        },
        {
          "days": 1,
          "stage": "LATE_CYCLE",
          "start": "2020-04-24"
        },
        {
          "days": 4,
          "stage": "EXPANSION",
          "start": "2020-04-27"
        }
      ],
      "post_patch_late_cycle_share": 0.137255,
      "post_patch_stress_or_boundary_share": 0.588235,
      "pre_patch_dominant_stage_path": [
        {
          "days": 5,
          "stage": "EXPANSION",
          "start": "2020-02-19"
        },
        {
          "days": 2,
          "stage": "LATE_CYCLE",
          "start": "2020-02-26"
        },
        {
          "days": 2,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2020-02-28"
        },
        {
          "days": 4,
          "stage": "LATE_CYCLE",
          "start": "2020-03-03"
        },
        {
          "days": 7,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2020-03-09"
        },
        {
          "days": 21,
          "stage": "STRESS",
          "start": "2020-03-18"
        },
        {
          "days": 4,
          "stage": "EXPANSION",
          "start": "2020-04-17"
        },
        {
          "days": 2,
          "stage": "LATE_CYCLE",
          "start": "2020-04-23"
        },
        {
          "days": 4,
          "stage": "EXPANSION",
          "start": "2020-04-27"
        }
      ],
      "pre_patch_late_cycle_share": 0.156863,
      "pre_patch_stress_or_boundary_share": 0.588235
    },
    "August 2015 liquidity vacuum": {
      "post_patch_dominant_stage_path": [
        {
          "days": 5,
          "stage": "EXPANSION",
          "start": "2015-08-17"
        },
        {
          "days": 1,
          "stage": "LATE_CYCLE",
          "start": "2015-08-24"
        },
        {
          "days": 5,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2015-08-25"
        },
        {
          "days": 10,
          "stage": "LATE_CYCLE",
          "start": "2015-09-01"
        }
      ],
      "post_patch_late_cycle_share": 0.52381,
      "post_patch_stress_or_boundary_share": 0.238095,
      "pre_patch_dominant_stage_path": [
        {
          "days": 5,
          "stage": "EXPANSION",
          "start": "2015-08-17"
        },
        {
          "days": 1,
          "stage": "LATE_CYCLE",
          "start": "2015-08-24"
        },
        {
          "days": 5,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2015-08-25"
        },
        {
          "days": 10,
          "stage": "LATE_CYCLE",
          "start": "2015-09-01"
        }
      ],
      "pre_patch_late_cycle_share": 0.52381,
      "pre_patch_stress_or_boundary_share": 0.238095
    },
    "ordinary late-cycle deterioration contrast": {
      "post_patch_dominant_stage_path": [
        {
          "days": 11,
          "stage": "EXPANSION",
          "start": "2014-09-15"
        },
        {
          "days": 7,
          "stage": "LATE_CYCLE",
          "start": "2014-09-30"
        },
        {
          "days": 1,
          "stage": "EXPANSION",
          "start": "2014-10-09"
        },
        {
          "days": 6,
          "stage": "LATE_CYCLE",
          "start": "2014-10-10"
        }
      ],
      "post_patch_late_cycle_share": 0.52,
      "post_patch_stress_or_boundary_share": 0.0,
      "pre_patch_dominant_stage_path": [
        {
          "days": 11,
          "stage": "EXPANSION",
          "start": "2014-09-15"
        },
        {
          "days": 7,
          "stage": "LATE_CYCLE",
          "start": "2014-09-30"
        },
        {
          "days": 1,
          "stage": "EXPANSION",
          "start": "2014-10-09"
        },
        {
          "days": 6,
          "stage": "LATE_CYCLE",
          "start": "2014-10-10"
        }
      ],
      "pre_patch_late_cycle_share": 0.52,
      "pre_patch_stress_or_boundary_share": 0.0
    }
  },
  "non_degradation_guardrail": {
    "late_cycle_accuracy_delta": 0.0,
    "not_materially_degraded": true,
    "stress_accuracy_delta": 0.0
  },
  "summary": "Batch 2 does not intentionally broaden the STRESS or LATE_CYCLE model. This workstream is retained as a guardrail to confirm those classes are not materially degraded while RECOVERY is being patched."
}
```
