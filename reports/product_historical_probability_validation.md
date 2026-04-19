# Historical Validation As Probability Product

## Decision
`HISTORICAL_PROBABILITY_PRODUCT_IS_MEANINGFULLY_VALID`

## Summary
Historical validation is expressed as stage path, probability path, urgency path, and ambiguity notes. PnL is not a validation layer.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "HISTORICAL_PROBABILITY_PRODUCT_IS_MEANINGFULLY_VALID",
  "event_validations": [
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2017-12-29",
      "error_ambiguity_notes": [
        "Diffuse probability share: 5.2%."
      ],
      "event_name": "Benign expansion period",
      "event_slice": "benign expansion period",
      "overreacted_or_underwarned": "No major overreaction or under-warning detected by the stage-process audit.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2017-01-03",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.7977,
            "FAST_CASCADE_BOUNDARY": 0.0191,
            "LATE_CYCLE": 0.1075,
            "RECOVERY": 0.034,
            "STRESS": 0.0417
          }
        },
        {
          "date": "2017-05-03",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.8708,
            "FAST_CASCADE_BOUNDARY": 0.0155,
            "LATE_CYCLE": 0.0488,
            "RECOVERY": 0.0312,
            "STRESS": 0.0337
          }
        },
        {
          "date": "2017-08-31",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.6066,
            "FAST_CASCADE_BOUNDARY": 0.0416,
            "LATE_CYCLE": 0.1817,
            "RECOVERY": 0.0473,
            "STRESS": 0.1228
          }
        },
        {
          "date": "2017-12-29",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.7979,
            "FAST_CASCADE_BOUNDARY": 0.0237,
            "LATE_CYCLE": 0.0894,
            "RECOVERY": 0.0315,
            "STRESS": 0.0576
          }
        }
      ],
      "qualitative_event_summary": "Benign expansion period: dominant stage path centered on EXPANSION; urgency mix {'LOW': 197, 'RISING': 48, 'HIGH': 6}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 251,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2017-01-03",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2017-05-03",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2017-08-31",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2017-12-29",
          "dominant_stage": "EXPANSION"
        }
      ],
      "start": "2017-01-03",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2017-01-03",
          "transition_urgency": "LOW"
        },
        {
          "date": "2017-05-03",
          "transition_urgency": "LOW"
        },
        {
          "date": "2017-08-31",
          "transition_urgency": "LOW"
        },
        {
          "date": "2017-12-29",
          "transition_urgency": "LOW"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2008-12-31",
      "error_ambiguity_notes": [
        "Diffuse probability share: 11.8%.",
        "Secondary stage rotated, so the window should be read as a process.",
        "Boundary warnings are separated from ordinary stage labels."
      ],
      "event_name": "2008 crisis",
      "event_slice": "2008 crisis",
      "overreacted_or_underwarned": "High urgency was frequent; acceptable only if event window was genuinely unstable.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2008-09-02",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.6045,
            "FAST_CASCADE_BOUNDARY": 0.0518,
            "LATE_CYCLE": 0.1387,
            "RECOVERY": 0.1207,
            "STRESS": 0.0842
          }
        },
        {
          "date": "2008-10-10",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0025,
            "FAST_CASCADE_BOUNDARY": 0.2081,
            "LATE_CYCLE": 0.2236,
            "RECOVERY": 0.0015,
            "STRESS": 0.5643
          }
        },
        {
          "date": "2008-11-19",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0055,
            "FAST_CASCADE_BOUNDARY": 0.11,
            "LATE_CYCLE": 0.2322,
            "RECOVERY": 0.0038,
            "STRESS": 0.6486
          }
        },
        {
          "date": "2008-12-31",
          "dominant_stage": "STRESS",
          "secondary_stage": "EXPANSION",
          "stage_probabilities": {
            "EXPANSION": 0.1455,
            "FAST_CASCADE_BOUNDARY": 0.0226,
            "LATE_CYCLE": 0.1247,
            "RECOVERY": 0.1138,
            "STRESS": 0.5934
          }
        }
      ],
      "qualitative_event_summary": "2008 crisis: dominant stage path centered on STRESS; urgency mix {'RISING': 42, 'HIGH': 26, 'UNSTABLE': 17}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 85,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2008-09-02",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2008-10-10",
          "dominant_stage": "STRESS"
        },
        {
          "date": "2008-11-19",
          "dominant_stage": "STRESS"
        },
        {
          "date": "2008-12-31",
          "dominant_stage": "STRESS"
        }
      ],
      "start": "2008-09-02",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2008-09-02",
          "transition_urgency": "RISING"
        },
        {
          "date": "2008-10-10",
          "transition_urgency": "UNSTABLE"
        },
        {
          "date": "2008-11-19",
          "transition_urgency": "HIGH"
        },
        {
          "date": "2008-12-31",
          "transition_urgency": "RISING"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2018-12-31",
      "error_ambiguity_notes": [
        "Diffuse probability share: 45.9%.",
        "Secondary stage rotated, so the window should be read as a process.",
        "Boundary warnings are separated from ordinary stage labels."
      ],
      "event_name": "Q4 2018 drawdown",
      "event_slice": "2018 drawdown",
      "overreacted_or_underwarned": "High urgency was frequent; acceptable only if event window was genuinely unstable.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2018-10-03",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.8203,
            "FAST_CASCADE_BOUNDARY": 0.0198,
            "LATE_CYCLE": 0.0793,
            "RECOVERY": 0.037,
            "STRESS": 0.0436
          }
        },
        {
          "date": "2018-10-31",
          "dominant_stage": "LATE_CYCLE",
          "secondary_stage": "FAST_CASCADE_BOUNDARY",
          "stage_probabilities": {
            "EXPANSION": 0.0389,
            "FAST_CASCADE_BOUNDARY": 0.328,
            "LATE_CYCLE": 0.3971,
            "RECOVERY": 0.0067,
            "STRESS": 0.2293
          }
        },
        {
          "date": "2018-11-29",
          "dominant_stage": "RECOVERY",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.1552,
            "FAST_CASCADE_BOUNDARY": 0.0522,
            "LATE_CYCLE": 0.2633,
            "RECOVERY": 0.3096,
            "STRESS": 0.2197
          }
        },
        {
          "date": "2018-12-31",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0223,
            "FAST_CASCADE_BOUNDARY": 0.1615,
            "LATE_CYCLE": 0.3544,
            "RECOVERY": 0.0051,
            "STRESS": 0.4567
          }
        }
      ],
      "qualitative_event_summary": "Q4 2018 drawdown: dominant stage path centered on LATE_CYCLE; urgency mix {'LOW': 7, 'RISING': 20, 'HIGH': 29, 'UNSTABLE': 5}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 61,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2018-10-03",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2018-10-31",
          "dominant_stage": "LATE_CYCLE"
        },
        {
          "date": "2018-11-29",
          "dominant_stage": "RECOVERY"
        },
        {
          "date": "2018-12-31",
          "dominant_stage": "STRESS"
        }
      ],
      "start": "2018-10-03",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2018-10-03",
          "transition_urgency": "LOW"
        },
        {
          "date": "2018-10-31",
          "transition_urgency": "HIGH"
        },
        {
          "date": "2018-11-29",
          "transition_urgency": "RISING"
        },
        {
          "date": "2018-12-31",
          "transition_urgency": "HIGH"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2020-04-30",
      "error_ambiguity_notes": [
        "Diffuse probability share: 29.4%.",
        "Secondary stage rotated, so the window should be read as a process.",
        "Boundary warnings are separated from ordinary stage labels."
      ],
      "event_name": "COVID fast cascade",
      "event_slice": "2020 fast cascade",
      "overreacted_or_underwarned": "No major overreaction or under-warning detected by the stage-process audit.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2020-02-19",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.7193,
            "FAST_CASCADE_BOUNDARY": 0.038,
            "LATE_CYCLE": 0.1139,
            "RECOVERY": 0.051,
            "STRESS": 0.0779
          }
        },
        {
          "date": "2020-03-13",
          "dominant_stage": "FAST_CASCADE_BOUNDARY",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0028,
            "FAST_CASCADE_BOUNDARY": 0.4222,
            "LATE_CYCLE": 0.2899,
            "RECOVERY": 0.0015,
            "STRESS": 0.2835
          }
        },
        {
          "date": "2020-04-07",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0265,
            "FAST_CASCADE_BOUNDARY": 0.0759,
            "LATE_CYCLE": 0.1001,
            "RECOVERY": 0.0153,
            "STRESS": 0.7821
          }
        },
        {
          "date": "2020-04-30",
          "dominant_stage": "RECOVERY",
          "secondary_stage": "EXPANSION",
          "stage_probabilities": {
            "EXPANSION": 0.2808,
            "FAST_CASCADE_BOUNDARY": 0.0226,
            "LATE_CYCLE": 0.175,
            "RECOVERY": 0.4458,
            "STRESS": 0.0757
          }
        }
      ],
      "qualitative_event_summary": "COVID fast cascade: dominant stage path centered on STRESS; urgency mix {'LOW': 2, 'RISING': 28, 'UNSTABLE': 19, 'HIGH': 2}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 51,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2020-02-19",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2020-03-13",
          "dominant_stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2020-04-07",
          "dominant_stage": "STRESS"
        },
        {
          "date": "2020-04-30",
          "dominant_stage": "RECOVERY"
        }
      ],
      "start": "2020-02-19",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2020-02-19",
          "transition_urgency": "LOW"
        },
        {
          "date": "2020-03-13",
          "transition_urgency": "UNSTABLE"
        },
        {
          "date": "2020-04-07",
          "transition_urgency": "RISING"
        },
        {
          "date": "2020-04-30",
          "transition_urgency": "RISING"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2022-06-30",
      "error_ambiguity_notes": [
        "Diffuse probability share: 18.5%.",
        "Secondary stage rotated, so the window should be read as a process."
      ],
      "event_name": "2022 H1 structural stress",
      "event_slice": "2022 H1 structural stress",
      "overreacted_or_underwarned": "No major overreaction or under-warning detected by the stage-process audit.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2022-01-03",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.5063,
            "FAST_CASCADE_BOUNDARY": 0.034,
            "LATE_CYCLE": 0.2751,
            "RECOVERY": 0.0576,
            "STRESS": 0.127
          }
        },
        {
          "date": "2022-03-03",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0812,
            "FAST_CASCADE_BOUNDARY": 0.0631,
            "LATE_CYCLE": 0.2302,
            "RECOVERY": 0.0183,
            "STRESS": 0.6072
          }
        },
        {
          "date": "2022-05-02",
          "dominant_stage": "LATE_CYCLE",
          "secondary_stage": "STRESS",
          "stage_probabilities": {
            "EXPANSION": 0.0543,
            "FAST_CASCADE_BOUNDARY": 0.0518,
            "LATE_CYCLE": 0.4499,
            "RECOVERY": 0.0083,
            "STRESS": 0.4357
          }
        },
        {
          "date": "2022-06-30",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0603,
            "FAST_CASCADE_BOUNDARY": 0.0252,
            "LATE_CYCLE": 0.1859,
            "RECOVERY": 0.1095,
            "STRESS": 0.6191
          }
        }
      ],
      "qualitative_event_summary": "2022 H1 structural stress: dominant stage path centered on STRESS; urgency mix {'LOW': 5, 'HIGH': 39, 'RISING': 70, 'UNSTABLE': 10}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 124,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2022-01-03",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2022-03-03",
          "dominant_stage": "STRESS"
        },
        {
          "date": "2022-05-02",
          "dominant_stage": "LATE_CYCLE"
        },
        {
          "date": "2022-06-30",
          "dominant_stage": "STRESS"
        }
      ],
      "start": "2022-01-03",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2022-01-03",
          "transition_urgency": "LOW"
        },
        {
          "date": "2022-03-03",
          "transition_urgency": "RISING"
        },
        {
          "date": "2022-05-02",
          "transition_urgency": "UNSTABLE"
        },
        {
          "date": "2022-06-30",
          "transition_urgency": "RISING"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2022-10-15",
      "error_ambiguity_notes": [
        "Diffuse probability share: 18.2%.",
        "Secondary stage rotated, so the window should be read as a process."
      ],
      "event_name": "2022 relapse / recovery",
      "event_slice": "2022 relapse recovery",
      "overreacted_or_underwarned": "High urgency was frequent; acceptable only if event window was genuinely unstable.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2022-08-15",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "RECOVERY",
          "stage_probabilities": {
            "EXPANSION": 0.6496,
            "FAST_CASCADE_BOUNDARY": 0.02,
            "LATE_CYCLE": 0.0541,
            "RECOVERY": 0.2519,
            "STRESS": 0.0243
          }
        },
        {
          "date": "2022-09-02",
          "dominant_stage": "LATE_CYCLE",
          "secondary_stage": "EXPANSION",
          "stage_probabilities": {
            "EXPANSION": 0.3484,
            "FAST_CASCADE_BOUNDARY": 0.068,
            "LATE_CYCLE": 0.3795,
            "RECOVERY": 0.0549,
            "STRESS": 0.1493
          }
        },
        {
          "date": "2022-09-26",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0873,
            "FAST_CASCADE_BOUNDARY": 0.0773,
            "LATE_CYCLE": 0.2417,
            "RECOVERY": 0.0077,
            "STRESS": 0.5861
          }
        },
        {
          "date": "2022-10-14",
          "dominant_stage": "STRESS",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0421,
            "FAST_CASCADE_BOUNDARY": 0.0469,
            "LATE_CYCLE": 0.2937,
            "RECOVERY": 0.0138,
            "STRESS": 0.6035
          }
        }
      ],
      "qualitative_event_summary": "2022 relapse / recovery: dominant stage path centered on STRESS; urgency mix {'LOW': 7, 'HIGH': 26, 'RISING': 8, 'UNSTABLE': 3}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 44,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2022-08-15",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2022-09-02",
          "dominant_stage": "LATE_CYCLE"
        },
        {
          "date": "2022-09-26",
          "dominant_stage": "STRESS"
        },
        {
          "date": "2022-10-14",
          "dominant_stage": "STRESS"
        }
      ],
      "start": "2022-08-15",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2022-08-15",
          "transition_urgency": "LOW"
        },
        {
          "date": "2022-09-02",
          "transition_urgency": "HIGH"
        },
        {
          "date": "2022-09-26",
          "transition_urgency": "HIGH"
        },
        {
          "date": "2022-10-14",
          "transition_urgency": "RISING"
        }
      ]
    },
    {
      "boundary_state_used_honestly": true,
      "confidence_stability_plausible": true,
      "dominant_stage_sensible": true,
      "end": "2015-09-15",
      "error_ambiguity_notes": [
        "Diffuse probability share: 38.1%.",
        "Secondary stage rotated, so the window should be read as a process.",
        "Boundary warnings are separated from ordinary stage labels."
      ],
      "event_name": "August 2015 liquidity vacuum",
      "event_slice": "2015 liquidity vacuum",
      "overreacted_or_underwarned": "No major overreaction or under-warning detected by the stage-process audit.",
      "policy_pnl_primary_validation": false,
      "primary_validation_language": "stage_probability_process_quality",
      "probability_path_table": [
        {
          "date": "2015-08-17",
          "dominant_stage": "EXPANSION",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.5544,
            "FAST_CASCADE_BOUNDARY": 0.0343,
            "LATE_CYCLE": 0.2873,
            "RECOVERY": 0.0546,
            "STRESS": 0.0693
          }
        },
        {
          "date": "2015-08-26",
          "dominant_stage": "FAST_CASCADE_BOUNDARY",
          "secondary_stage": "LATE_CYCLE",
          "stage_probabilities": {
            "EXPANSION": 0.0993,
            "FAST_CASCADE_BOUNDARY": 0.5957,
            "LATE_CYCLE": 0.1922,
            "RECOVERY": 0.0108,
            "STRESS": 0.102
          }
        },
        {
          "date": "2015-09-04",
          "dominant_stage": "LATE_CYCLE",
          "secondary_stage": "STRESS",
          "stage_probabilities": {
            "EXPANSION": 0.119,
            "FAST_CASCADE_BOUNDARY": 0.1305,
            "LATE_CYCLE": 0.4735,
            "RECOVERY": 0.0255,
            "STRESS": 0.2515
          }
        },
        {
          "date": "2015-09-15",
          "dominant_stage": "LATE_CYCLE",
          "secondary_stage": "EXPANSION",
          "stage_probabilities": {
            "EXPANSION": 0.2373,
            "FAST_CASCADE_BOUNDARY": 0.0498,
            "LATE_CYCLE": 0.3193,
            "RECOVERY": 0.1801,
            "STRESS": 0.2135
          }
        }
      ],
      "qualitative_event_summary": "August 2015 liquidity vacuum: dominant stage path centered on LATE_CYCLE; urgency mix {'LOW': 8, 'RISING': 5, 'HIGH': 3, 'UNSTABLE': 5}. Assessment is stage-process-first and excludes strategy PnL.",
      "rows": 21,
      "secondary_stage_sensible": true,
      "stage_path_table": [
        {
          "date": "2015-08-17",
          "dominant_stage": "EXPANSION"
        },
        {
          "date": "2015-08-26",
          "dominant_stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2015-09-04",
          "dominant_stage": "LATE_CYCLE"
        },
        {
          "date": "2015-09-15",
          "dominant_stage": "LATE_CYCLE"
        }
      ],
      "start": "2015-08-17",
      "urgency_moved_before_or_during_migration": true,
      "urgency_path_table": [
        {
          "date": "2015-08-17",
          "transition_urgency": "LOW"
        },
        {
          "date": "2015-08-26",
          "transition_urgency": "UNSTABLE"
        },
        {
          "date": "2015-09-04",
          "transition_urgency": "RISING"
        },
        {
          "date": "2015-09-15",
          "transition_urgency": "LOW"
        }
      ]
    }
  ],
  "policy_pnl_used_as_primary_validation": false,
  "primary_validation_language": "stage_probability_process_quality",
  "summary": "Historical validation is expressed as stage path, probability path, urgency path, and ambiguity notes. PnL is not a validation layer."
}
```
