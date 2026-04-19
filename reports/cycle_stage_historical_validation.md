# Cycle Stage Historical Validation

## Decision
`HISTORICAL_STAGE_CLASSIFICATION_IS_MEANINGFULLY_CORRECT`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "HISTORICAL_STAGE_CLASSIFICATION_IS_MEANINGFULLY_CORRECT",
  "event_validations": [
    {
      "confidence_path_table": [
        {
          "confidence": 0.64,
          "date": "2017-01-03"
        },
        {
          "confidence": 0.84,
          "date": "2017-05-03"
        },
        {
          "confidence": 0.56,
          "date": "2017-08-31"
        },
        {
          "confidence": 0.84,
          "date": "2017-12-29"
        }
      ],
      "confidence_profile": {
        "max": 0.84,
        "median": 0.76,
        "min": 0.54
      },
      "dominant_stage": "EXPANSION",
      "end": "2017-12-29",
      "event_name": "Benign expansion / normal period",
      "event_slice": "benign expansion",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2017-01-03",
          "stage": "EXPANSION"
        },
        {
          "date": "2017-05-03",
          "stage": "EXPANSION"
        },
        {
          "date": "2017-08-31",
          "stage": "LATE_CYCLE"
        },
        {
          "date": "2017-12-29",
          "stage": "EXPANSION"
        }
      ],
      "stage_transition_count": 18,
      "start": "2017-01-03",
      "summary_judgment": "Benign expansion / normal period: dominant label EXPANSION; peak stress 0.16; peak gap pressure 0.02. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2017-01-03",
          "urgency": "RISING"
        },
        {
          "date": "2017-05-03",
          "urgency": "LOW"
        },
        {
          "date": "2017-08-31",
          "urgency": "RISING"
        },
        {
          "date": "2017-12-29",
          "urgency": "LOW"
        }
      ],
      "urgency_profile": {
        "HIGH": 2,
        "LOW": 117,
        "RISING": 132
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.78,
          "date": "2008-09-02"
        },
        {
          "confidence": 0.859,
          "date": "2008-10-10"
        },
        {
          "confidence": 0.823,
          "date": "2008-11-19"
        },
        {
          "confidence": 0.78,
          "date": "2008-12-31"
        }
      ],
      "confidence_profile": {
        "max": 0.92,
        "median": 0.833,
        "min": 0.708
      },
      "dominant_stage": "STRESS",
      "end": "2008-12-31",
      "event_name": "2008 financial crisis stress",
      "event_slice": "financial crisis",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2008-09-02",
          "stage": "STRESS"
        },
        {
          "date": "2008-10-10",
          "stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2008-11-19",
          "stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2008-12-31",
          "stage": "STRESS"
        }
      ],
      "stage_transition_count": 16,
      "start": "2008-09-02",
      "summary_judgment": "2008 financial crisis stress: dominant label STRESS; peak stress 1.00; peak gap pressure 0.11. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2008-09-02",
          "urgency": "HIGH"
        },
        {
          "date": "2008-10-10",
          "urgency": "UNSTABLE"
        },
        {
          "date": "2008-11-19",
          "urgency": "HIGH"
        },
        {
          "date": "2008-12-31",
          "urgency": "HIGH"
        }
      ],
      "urgency_profile": {
        "HIGH": 73,
        "UNSTABLE": 12
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.84,
          "date": "2018-10-03"
        },
        {
          "confidence": 0.817,
          "date": "2018-10-31"
        },
        {
          "confidence": 0.7,
          "date": "2018-11-29"
        },
        {
          "confidence": 0.92,
          "date": "2018-12-31"
        }
      ],
      "confidence_profile": {
        "max": 0.92,
        "median": 0.78,
        "min": 0.66
      },
      "dominant_stage": "STRESS",
      "end": "2018-12-31",
      "event_name": "Q4 2018 drawdown",
      "event_slice": "drawdown",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2018-10-03",
          "stage": "EXPANSION"
        },
        {
          "date": "2018-10-31",
          "stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2018-11-29",
          "stage": "STRESS"
        },
        {
          "date": "2018-12-31",
          "stage": "STRESS"
        }
      ],
      "stage_transition_count": 5,
      "start": "2018-10-03",
      "summary_judgment": "Q4 2018 drawdown: dominant label STRESS; peak stress 0.56; peak gap pressure 0.05. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2018-10-03",
          "urgency": "LOW"
        },
        {
          "date": "2018-10-31",
          "urgency": "HIGH"
        },
        {
          "date": "2018-11-29",
          "urgency": "HIGH"
        },
        {
          "date": "2018-12-31",
          "urgency": "HIGH"
        }
      ],
      "urgency_profile": {
        "HIGH": 32,
        "LOW": 6,
        "RISING": 21,
        "UNSTABLE": 2
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.56,
          "date": "2020-02-19"
        },
        {
          "confidence": 0.9,
          "date": "2020-03-13"
        },
        {
          "confidence": 0.92,
          "date": "2020-04-07"
        },
        {
          "confidence": 0.73,
          "date": "2020-04-30"
        }
      ],
      "confidence_profile": {
        "max": 0.92,
        "median": 0.84,
        "min": 0.56
      },
      "dominant_stage": "FAST_CASCADE_BOUNDARY",
      "end": "2020-04-30",
      "event_name": "COVID fast cascade",
      "event_slice": "fast cascade",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2020-02-19",
          "stage": "LATE_CYCLE"
        },
        {
          "date": "2020-03-13",
          "stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2020-04-07",
          "stage": "STRESS"
        },
        {
          "date": "2020-04-30",
          "stage": "RECOVERY"
        }
      ],
      "stage_transition_count": 5,
      "start": "2020-02-19",
      "summary_judgment": "COVID fast cascade: dominant label FAST_CASCADE_BOUNDARY; peak stress 1.00; peak gap pressure 0.22. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2020-02-19",
          "urgency": "LOW"
        },
        {
          "date": "2020-03-13",
          "urgency": "UNSTABLE"
        },
        {
          "date": "2020-04-07",
          "urgency": "HIGH"
        },
        {
          "date": "2020-04-30",
          "urgency": "LOW"
        }
      ],
      "urgency_profile": {
        "HIGH": 14,
        "LOW": 8,
        "RISING": 9,
        "UNSTABLE": 20
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.56,
          "date": "2022-01-03"
        },
        {
          "confidence": 0.789,
          "date": "2022-03-03"
        },
        {
          "confidence": 0.92,
          "date": "2022-05-02"
        },
        {
          "confidence": 0.92,
          "date": "2022-06-30"
        }
      ],
      "confidence_profile": {
        "max": 0.92,
        "median": 0.781,
        "min": 0.56
      },
      "dominant_stage": "STRESS",
      "end": "2022-06-30",
      "event_name": "2022 H1 structural stress",
      "event_slice": "structural stress",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2022-01-03",
          "stage": "LATE_CYCLE"
        },
        {
          "date": "2022-03-03",
          "stage": "STRESS"
        },
        {
          "date": "2022-05-02",
          "stage": "STRESS"
        },
        {
          "date": "2022-06-30",
          "stage": "STRESS"
        }
      ],
      "stage_transition_count": 13,
      "start": "2022-01-03",
      "summary_judgment": "2022 H1 structural stress: dominant label STRESS; peak stress 0.81; peak gap pressure 0.08. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2022-01-03",
          "urgency": "RISING"
        },
        {
          "date": "2022-03-03",
          "urgency": "HIGH"
        },
        {
          "date": "2022-05-02",
          "urgency": "UNSTABLE"
        },
        {
          "date": "2022-06-30",
          "urgency": "HIGH"
        }
      ],
      "urgency_profile": {
        "HIGH": 76,
        "RISING": 41,
        "UNSTABLE": 7
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.81,
          "date": "2022-08-15"
        },
        {
          "confidence": 0.66,
          "date": "2022-09-02"
        },
        {
          "confidence": 0.92,
          "date": "2022-09-26"
        },
        {
          "confidence": 0.92,
          "date": "2022-10-14"
        }
      ],
      "confidence_profile": {
        "max": 0.92,
        "median": 0.81,
        "min": 0.56
      },
      "dominant_stage": "STRESS",
      "end": "2022-10-15",
      "event_name": "2022 bear rally relapse",
      "event_slice": "relapse recovery",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2022-08-15",
          "stage": "RECOVERY"
        },
        {
          "date": "2022-09-02",
          "stage": "LATE_CYCLE"
        },
        {
          "date": "2022-09-26",
          "stage": "STRESS"
        },
        {
          "date": "2022-10-14",
          "stage": "STRESS"
        }
      ],
      "stage_transition_count": 5,
      "start": "2022-08-15",
      "summary_judgment": "2022 bear rally relapse: dominant label STRESS; peak stress 0.70; peak gap pressure 0.06. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2022-08-15",
          "urgency": "LOW"
        },
        {
          "date": "2022-09-02",
          "urgency": "RISING"
        },
        {
          "date": "2022-09-26",
          "urgency": "HIGH"
        },
        {
          "date": "2022-10-14",
          "urgency": "HIGH"
        }
      ],
      "urgency_profile": {
        "HIGH": 20,
        "LOW": 5,
        "RISING": 15,
        "UNSTABLE": 4
      }
    },
    {
      "confidence_path_table": [
        {
          "confidence": 0.64,
          "date": "2015-08-17"
        },
        {
          "confidence": 0.883,
          "date": "2015-08-26"
        },
        {
          "confidence": 0.786,
          "date": "2015-09-04"
        },
        {
          "confidence": 0.7,
          "date": "2015-09-15"
        }
      ],
      "confidence_profile": {
        "max": 0.888,
        "median": 0.78,
        "min": 0.64
      },
      "dominant_stage": "STRESS",
      "end": "2015-09-15",
      "event_name": "August 2015 liquidity vacuum",
      "event_slice": "liquidity vacuum",
      "primary_validation_language": "stage_usefulness_not_policy_pnl",
      "stage_path_table": [
        {
          "date": "2015-08-17",
          "stage": "EXPANSION"
        },
        {
          "date": "2015-08-26",
          "stage": "FAST_CASCADE_BOUNDARY"
        },
        {
          "date": "2015-09-04",
          "stage": "STRESS"
        },
        {
          "date": "2015-09-15",
          "stage": "STRESS"
        }
      ],
      "stage_transition_count": 3,
      "start": "2015-08-17",
      "summary_judgment": "August 2015 liquidity vacuum: dominant label STRESS; peak stress 0.57; peak gap pressure 0.11. Validated as a stage path, not as policy PnL.",
      "urgency_path_table": [
        {
          "date": "2015-08-17",
          "urgency": "RISING"
        },
        {
          "date": "2015-08-26",
          "urgency": "UNSTABLE"
        },
        {
          "date": "2015-09-04",
          "urgency": "RISING"
        },
        {
          "date": "2015-09-15",
          "urgency": "LOW"
        }
      ],
      "urgency_profile": {
        "LOW": 6,
        "RISING": 10,
        "UNSTABLE": 5
      }
    }
  ],
  "policy_pnl_used_as_primary_validation": false,
  "primary_validation_language": "stage_usefulness_not_policy_pnl"
}
```
