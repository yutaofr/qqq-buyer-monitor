# State Machine Divergence Window Enumeration

## Summary
Theoretical target and actual executed leverage diverge in every audited major event because execution is next-session delayed.

## Machine-Readable Snapshot
```json
{
  "divergence_windows": [
    {
      "actual_executed_leverage_path": [
        {
          "date": "2020-02-27",
          "leverage": 2.0
        },
        {
          "date": "2020-03-02",
          "leverage": 1.1
        },
        {
          "date": "2020-04-14",
          "leverage": 0.8
        },
        {
          "date": "2020-04-17",
          "leverage": 0.9
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": true,
      "affected_pre_gap_exposure_reduction": true,
      "affected_recovery_miss": true,
      "average_divergence_magnitude": 0.6,
      "contribution_impact_actual_minus_theoretical": -0.044457,
      "cumulative_divergence_exposure": 2.4,
      "divergence_peak_damage_relation": "during_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "widened",
      "duration_trading_days": 4,
      "end_date": "2020-04-17",
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "largest_gap_date": "2020-03-16",
      "maximum_absolute_divergence": 1.1,
      "peak_damage_date": "2020-03-16",
      "start_date": "2020-02-27",
      "theoretical_target_leverage_path": [
        {
          "date": "2020-02-27",
          "leverage": 1.1
        },
        {
          "date": "2020-03-02",
          "leverage": 0.8
        },
        {
          "date": "2020-04-14",
          "leverage": 0.9
        },
        {
          "date": "2020-04-17",
          "leverage": 2.0
        }
      ]
    },
    {
      "actual_executed_leverage_path": [
        {
          "date": "2015-08-25",
          "leverage": 2.0
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": false,
      "affected_pre_gap_exposure_reduction": false,
      "affected_recovery_miss": false,
      "average_divergence_magnitude": 1.2,
      "contribution_impact_actual_minus_theoretical": -0.004509,
      "cumulative_divergence_exposure": 1.2,
      "divergence_peak_damage_relation": "during_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "narrowed_or_flat",
      "duration_trading_days": 1,
      "end_date": "2015-08-25",
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "largest_gap_date": "2015-08-24",
      "maximum_absolute_divergence": 1.2,
      "peak_damage_date": "2015-08-25",
      "start_date": "2015-08-25",
      "theoretical_target_leverage_path": [
        {
          "date": "2015-08-25",
          "leverage": 0.8
        }
      ]
    },
    {
      "actual_executed_leverage_path": [
        {
          "date": "2018-10-26",
          "leverage": 2.0
        },
        {
          "date": "2018-11-27",
          "leverage": 0.8
        },
        {
          "date": "2018-12-11",
          "leverage": 0.9
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": true,
      "affected_pre_gap_exposure_reduction": true,
      "affected_recovery_miss": false,
      "average_divergence_magnitude": 0.466667,
      "contribution_impact_actual_minus_theoretical": -0.030873,
      "cumulative_divergence_exposure": 1.4,
      "divergence_peak_damage_relation": "before_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "narrowed_or_flat",
      "duration_trading_days": 3,
      "end_date": "2018-12-11",
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "largest_gap_date": "2018-10-26",
      "maximum_absolute_divergence": 1.2,
      "peak_damage_date": "2018-12-24",
      "start_date": "2018-10-26",
      "theoretical_target_leverage_path": [
        {
          "date": "2018-10-26",
          "leverage": 0.8
        },
        {
          "date": "2018-11-27",
          "leverage": 0.9
        },
        {
          "date": "2018-12-11",
          "leverage": 0.8
        }
      ]
    },
    {
      "actual_executed_leverage_path": [
        {
          "date": "2022-01-05",
          "leverage": 2.0
        },
        {
          "date": "2022-01-19",
          "leverage": 1.1
        },
        {
          "date": "2022-01-24",
          "leverage": 2.0
        },
        {
          "date": "2022-04-08",
          "leverage": 0.8
        },
        {
          "date": "2022-04-19",
          "leverage": 0.9
        },
        {
          "date": "2022-04-26",
          "leverage": 2.0
        },
        {
          "date": "2022-06-07",
          "leverage": 0.8
        },
        {
          "date": "2022-06-10",
          "leverage": 0.9
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": false,
      "affected_pre_gap_exposure_reduction": true,
      "affected_recovery_miss": false,
      "average_divergence_magnitude": 0.7,
      "contribution_impact_actual_minus_theoretical": -0.085142,
      "cumulative_divergence_exposure": 5.6,
      "divergence_peak_damage_relation": "before_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "narrowed_or_flat",
      "duration_trading_days": 8,
      "end_date": "2022-06-10",
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "largest_gap_date": "2022-02-24",
      "maximum_absolute_divergence": 1.2,
      "peak_damage_date": "2022-06-16",
      "start_date": "2022-01-05",
      "theoretical_target_leverage_path": [
        {
          "date": "2022-01-05",
          "leverage": 1.1
        },
        {
          "date": "2022-01-19",
          "leverage": 2.0
        },
        {
          "date": "2022-01-24",
          "leverage": 0.8
        },
        {
          "date": "2022-04-08",
          "leverage": 0.9
        },
        {
          "date": "2022-04-19",
          "leverage": 2.0
        },
        {
          "date": "2022-04-26",
          "leverage": 0.8
        },
        {
          "date": "2022-06-07",
          "leverage": 0.9
        },
        {
          "date": "2022-06-10",
          "leverage": 0.8
        }
      ]
    },
    {
      "actual_executed_leverage_path": [
        {
          "date": "2008-09-15",
          "leverage": 2.0
        },
        {
          "date": "2008-12-31",
          "leverage": 0.8
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": true,
      "affected_pre_gap_exposure_reduction": true,
      "affected_recovery_miss": true,
      "average_divergence_magnitude": 0.65,
      "contribution_impact_actual_minus_theoretical": -0.03815,
      "cumulative_divergence_exposure": 1.3,
      "divergence_peak_damage_relation": "during_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "narrowed_or_flat",
      "duration_trading_days": 2,
      "end_date": "2008-12-31",
      "event_class": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "largest_gap_date": "2008-10-24",
      "maximum_absolute_divergence": 1.2,
      "peak_damage_date": "2008-11-20",
      "start_date": "2008-09-15",
      "theoretical_target_leverage_path": [
        {
          "date": "2008-09-15",
          "leverage": 0.8
        },
        {
          "date": "2008-12-31",
          "leverage": 0.9
        }
      ]
    },
    {
      "actual_executed_leverage_path": [
        {
          "date": "2022-09-15",
          "leverage": 2.0
        }
      ],
      "affected_false_reentry": true,
      "affected_loss_contribution_attribution": true,
      "affected_post_gap_damage": false,
      "affected_pre_gap_exposure_reduction": false,
      "affected_recovery_miss": false,
      "average_divergence_magnitude": 1.2,
      "contribution_impact_actual_minus_theoretical": -0.019984,
      "cumulative_divergence_exposure": 1.2,
      "divergence_peak_damage_relation": "before_peak_damage",
      "divergence_widened_or_narrowed_during_stress": "narrowed_or_flat",
      "duration_trading_days": 1,
      "end_date": "2022-09-15",
      "event_class": "recovery-with-relapse",
      "event_name": "2022 bear rally relapse",
      "largest_gap_date": "2022-09-13",
      "maximum_absolute_divergence": 1.2,
      "peak_damage_date": "2022-10-14",
      "start_date": "2022-09-15",
      "theoretical_target_leverage_path": [
        {
          "date": "2022-09-15",
          "leverage": 0.8
        }
      ]
    }
  ],
  "summary": "Theoretical target and actual executed leverage diverge in every audited major event because execution is next-session delayed.",
  "summary_statistics": {
    "average_divergence_magnitude": 0.802778,
    "divergence_concentration_by_event_class": [
      {
        "cum_abs": 2.4,
        "days": 4,
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "windows": 1
      },
      {
        "cum_abs": 1.2,
        "days": 1,
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "windows": 1
      },
      {
        "cum_abs": 1.4,
        "days": 3,
        "event_class": "2018-style partially containable drawdown",
        "windows": 1
      },
      {
        "cum_abs": 6.8999999999999995,
        "days": 10,
        "event_class": "slower structural stress",
        "windows": 2
      },
      {
        "cum_abs": 1.2,
        "days": 1,
        "event_class": "recovery-with-relapse",
        "windows": 1
      }
    ],
    "total_days_with_divergence": 19,
    "total_number_of_divergence_windows": 6,
    "worst_divergence_magnitude": 1.2
  }
}
```
