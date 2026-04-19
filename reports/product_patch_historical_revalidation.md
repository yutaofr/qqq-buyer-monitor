# Product Patch Historical Revalidation

## Decision
`PATCHED_PRODUCT_DOES_NOT_IMPROVE_ENOUGH`

## Summary
Historical revalidation remains a product-quality exercise: stage path, probability path, urgency, recovery behavior, stress behavior, and boundary honesty are assessed without PnL.

## Machine-Readable Snapshot
```json
{
  "decision": "PATCHED_PRODUCT_DOES_NOT_IMPROVE_ENOUGH",
  "event_validations": [
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.0,
        "mean_prob_boundary": 0.025719
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.0,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2017-12-29",
      "event_name": "Benign expansion period",
      "probability_path": [
        {
          "date": "2017-01-03",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.809136,
            "FAST_CASCADE_BOUNDARY": 0.019304,
            "LATE_CYCLE": 0.108888,
            "RECOVERY": 0.02046,
            "STRESS": 0.042213
          }
        },
        {
          "date": "2017-07-03",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.450194,
            "FAST_CASCADE_BOUNDARY": 0.039942,
            "LATE_CYCLE": 0.312165,
            "RECOVERY": 0.035198,
            "STRESS": 0.162501
          }
        },
        {
          "date": "2017-12-29",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.80595,
            "FAST_CASCADE_BOUNDARY": 0.023908,
            "LATE_CYCLE": 0.090292,
            "RECOVERY": 0.021714,
            "STRESS": 0.058137
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.024159
      },
      "stage_path": [
        {
          "days": 130,
          "stage": "EXPANSION",
          "start": "2017-01-03"
        },
        {
          "days": 3,
          "stage": "LATE_CYCLE",
          "start": "2017-07-11"
        },
        {
          "days": 24,
          "stage": "EXPANSION",
          "start": "2017-07-14"
        },
        {
          "days": 1,
          "stage": "LATE_CYCLE",
          "start": "2017-08-17"
        },
        {
          "days": 61,
          "stage": "EXPANSION",
          "start": "2017-08-18"
        },
        {
          "days": 4,
          "stage": "LATE_CYCLE",
          "start": "2017-11-14"
        },
        {
          "days": 28,
          "stage": "EXPANSION",
          "start": "2017-11-20"
        }
      ],
      "start": "2017-01-03",
      "stress_behavior": {
        "dominant_stress_share": 0.0,
        "mean_prob_stress": 0.066605
      },
      "urgency_path": [
        {
          "days": 197,
          "label": "LOW",
          "share": 0.784861
        },
        {
          "days": 48,
          "label": "RISING",
          "share": 0.191235
        },
        {
          "days": 6,
          "label": "HIGH",
          "share": 0.023904
        }
      ]
    },
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.023529,
        "mean_prob_boundary": 0.125843
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.0,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2008-12-31",
      "event_name": "2008 crisis",
      "probability_path": [
        {
          "date": "2008-09-02",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.631293,
            "FAST_CASCADE_BOUNDARY": 0.052308,
            "LATE_CYCLE": 0.141259,
            "RECOVERY": 0.090302,
            "STRESS": 0.084838
          }
        },
        {
          "date": "2008-10-30",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.002455,
            "FAST_CASCADE_BOUNDARY": 0.271173,
            "LATE_CYCLE": 0.074792,
            "RECOVERY": 0.001492,
            "STRESS": 0.650088
          }
        },
        {
          "date": "2008-12-31",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.155179,
            "FAST_CASCADE_BOUNDARY": 0.024092,
            "LATE_CYCLE": 0.132438,
            "RECOVERY": 0.060452,
            "STRESS": 0.627839
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.019261
      },
      "stage_path": [
        {
          "days": 10,
          "stage": "EXPANSION",
          "start": "2008-09-02"
        },
        {
          "days": 3,
          "stage": "LATE_CYCLE",
          "start": "2008-09-16"
        },
        {
          "days": 2,
          "stage": "FAST_CASCADE_BOUNDARY",
          "start": "2008-09-19"
        },
        {
          "days": 70,
          "stage": "STRESS",
          "start": "2008-09-23"
        }
      ],
      "start": "2008-09-02",
      "stress_behavior": {
        "dominant_stress_share": 0.823529,
        "mean_prob_stress": 0.588652
      },
      "urgency_path": [
        {
          "days": 42,
          "label": "RISING",
          "share": 0.494118
        },
        {
          "days": 26,
          "label": "HIGH",
          "share": 0.305882
        },
        {
          "days": 17,
          "label": "UNSTABLE",
          "share": 0.2
        }
      ]
    },
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.0,
        "mean_prob_boundary": 0.083958
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.0,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2018-12-31",
      "event_name": "Q4 2018 drawdown",
      "probability_path": [
        {
          "date": "2018-10-03",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.835637,
            "FAST_CASCADE_BOUNDARY": 0.020115,
            "LATE_CYCLE": 0.080751,
            "RECOVERY": 0.019119,
            "STRESS": 0.044378
          }
        },
        {
          "date": "2018-11-14",
          "dominant_stage": "LATE_CYCLE",
          "probabilities": {
            "EXPANSION": 0.234217,
            "FAST_CASCADE_BOUNDARY": 0.063037,
            "LATE_CYCLE": 0.334801,
            "RECOVERY": 0.13607,
            "STRESS": 0.231875
          }
        },
        {
          "date": "2018-12-31",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.022287,
            "FAST_CASCADE_BOUNDARY": 0.161318,
            "LATE_CYCLE": 0.353753,
            "RECOVERY": 0.00706,
            "STRESS": 0.455582
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.061081
      },
      "stage_path": [
        {
          "days": 6,
          "stage": "EXPANSION",
          "start": "2018-10-03"
        },
        {
          "days": 8,
          "stage": "LATE_CYCLE",
          "start": "2018-10-11"
        },
        {
          "days": 1,
          "stage": "EXPANSION",
          "start": "2018-10-23"
        },
        {
          "days": 12,
          "stage": "LATE_CYCLE",
          "start": "2018-10-24"
        },
        {
          "days": 3,
          "stage": "EXPANSION",
          "start": "2018-11-09"
        },
        {
          "days": 8,
          "stage": "LATE_CYCLE",
          "start": "2018-11-14"
        },
        {
          "days": 1,
          "stage": "STRESS",
          "start": "2018-11-27"
        },
        {
          "days": 2,
          "stage": "LATE_CYCLE",
          "start": "2018-11-28"
        },
        {
          "days": 4,
          "stage": "EXPANSION",
          "start": "2018-11-30"
        },
        {
          "days": 3,
          "stage": "STRESS",
          "start": "2018-12-07"
        },
        {
          "days": 3,
          "stage": "LATE_CYCLE",
          "start": "2018-12-12"
        },
        {
          "days": 10,
          "stage": "STRESS",
          "start": "2018-12-17"
        }
      ],
      "start": "2018-10-03",
      "stress_behavior": {
        "dominant_stress_share": 0.229508,
        "mean_prob_stress": 0.25295
      },
      "urgency_path": [
        {
          "days": 13,
          "label": "LOW",
          "share": 0.213115
        },
        {
          "days": 14,
          "label": "RISING",
          "share": 0.229508
        },
        {
          "days": 29,
          "label": "HIGH",
          "share": 0.47541
        },
        {
          "days": 5,
          "label": "UNSTABLE",
          "share": 0.081967
        }
      ]
    },
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.176471,
        "mean_prob_boundary": 0.180545
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.0,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2020-04-30",
      "event_name": "COVID fast cascade",
      "probability_path": [
        {
          "date": "2020-02-19",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.734845,
            "FAST_CASCADE_BOUNDARY": 0.038782,
            "LATE_CYCLE": 0.116269,
            "RECOVERY": 0.03055,
            "STRESS": 0.079554
          }
        },
        {
          "date": "2020-03-25",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.003268,
            "FAST_CASCADE_BOUNDARY": 0.144298,
            "LATE_CYCLE": 0.250657,
            "RECOVERY": 0.002439,
            "STRESS": 0.599337
          }
        },
        {
          "date": "2020-04-30",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.365853,
            "FAST_CASCADE_BOUNDARY": 0.029611,
            "LATE_CYCLE": 0.225096,
            "RECOVERY": 0.281217,
            "STRESS": 0.098224
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.064185
      },
      "stage_path": [
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
      "start": "2020-02-19",
      "stress_behavior": {
        "dominant_stress_share": 0.411765,
        "mean_prob_stress": 0.343165
      },
      "urgency_path": [
        {
          "days": 13,
          "label": "LOW",
          "share": 0.254902
        },
        {
          "days": 17,
          "label": "RISING",
          "share": 0.333333
        },
        {
          "days": 19,
          "label": "UNSTABLE",
          "share": 0.372549
        },
        {
          "days": 2,
          "label": "HIGH",
          "share": 0.039216
        }
      ]
    },
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.0,
        "mean_prob_boundary": 0.066661
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.016129,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2022-06-30",
      "event_name": "2022 H1 structural stress",
      "probability_path": [
        {
          "date": "2022-01-03",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.518142,
            "FAST_CASCADE_BOUNDARY": 0.034803,
            "LATE_CYCLE": 0.283199,
            "RECOVERY": 0.033917,
            "STRESS": 0.129939
          }
        },
        {
          "date": "2022-04-01",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.392741,
            "FAST_CASCADE_BOUNDARY": 0.033211,
            "LATE_CYCLE": 0.166485,
            "RECOVERY": 0.29425,
            "STRESS": 0.113313
          }
        },
        {
          "date": "2022-06-30",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.065866,
            "FAST_CASCADE_BOUNDARY": 0.026753,
            "LATE_CYCLE": 0.199132,
            "RECOVERY": 0.047219,
            "STRESS": 0.66103
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.061773
      },
      "stage_path": [
        {
          "days": 2,
          "stage": "EXPANSION",
          "start": "2022-01-03"
        },
        {
          "days": 26,
          "stage": "LATE_CYCLE",
          "start": "2022-01-05"
        },
        {
          "days": 3,
          "stage": "STRESS",
          "start": "2022-02-11"
        },
        {
          "days": 4,
          "stage": "LATE_CYCLE",
          "start": "2022-02-16"
        },
        {
          "days": 22,
          "stage": "STRESS",
          "start": "2022-02-23"
        },
        {
          "days": 11,
          "stage": "EXPANSION",
          "start": "2022-03-25"
        },
        {
          "days": 10,
          "stage": "LATE_CYCLE",
          "start": "2022-04-11"
        },
        {
          "days": 4,
          "stage": "STRESS",
          "start": "2022-04-26"
        },
        {
          "days": 2,
          "stage": "LATE_CYCLE",
          "start": "2022-05-02"
        },
        {
          "days": 40,
          "stage": "STRESS",
          "start": "2022-05-04"
        }
      ],
      "start": "2022-01-03",
      "stress_behavior": {
        "dominant_stress_share": 0.556452,
        "mean_prob_stress": 0.407177
      },
      "urgency_path": [
        {
          "days": 13,
          "label": "LOW",
          "share": 0.104839
        },
        {
          "days": 39,
          "label": "HIGH",
          "share": 0.314516
        },
        {
          "days": 62,
          "label": "RISING",
          "share": 0.5
        },
        {
          "days": 10,
          "label": "UNSTABLE",
          "share": 0.080645
        }
      ]
    },
    {
      "boundary_behavior": {
        "dominant_boundary_share": 0.0,
        "mean_prob_boundary": 0.060344
      },
      "changes_vs_pre_patch": {
        "diffuse_share_delta": 0.0,
        "stress_or_boundary_share_delta": 0.0
      },
      "end": "2022-10-15",
      "event_name": "2022 relapse / recovery",
      "probability_path": [
        {
          "date": "2022-08-15",
          "dominant_stage": "EXPANSION",
          "probabilities": {
            "EXPANSION": 0.72101,
            "FAST_CASCADE_BOUNDARY": 0.022393,
            "LATE_CYCLE": 0.061418,
            "RECOVERY": 0.168071,
            "STRESS": 0.027108
          }
        },
        {
          "date": "2022-09-15",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.280341,
            "FAST_CASCADE_BOUNDARY": 0.105834,
            "LATE_CYCLE": 0.231708,
            "RECOVERY": 0.035621,
            "STRESS": 0.346496
          }
        },
        {
          "date": "2022-10-14",
          "dominant_stage": "STRESS",
          "probabilities": {
            "EXPANSION": 0.042292,
            "FAST_CASCADE_BOUNDARY": 0.047145,
            "LATE_CYCLE": 0.294913,
            "RECOVERY": 0.009666,
            "STRESS": 0.605985
          }
        }
      ],
      "recovery_behavior": {
        "dominant_recovery_share": 0.0,
        "mean_prob_recovery": 0.047616
      },
      "stage_path": [
        {
          "days": 14,
          "
```
