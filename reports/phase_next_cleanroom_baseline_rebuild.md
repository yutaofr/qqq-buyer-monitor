# Phase Next Clean-Room Baseline Rebuild

## Summary
Clean-room baseline rebuilt from QQQ daily OHLCV and repository macro/breadth inputs. Post-Phase-4.2 artifacts are quarantined as references only.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "event_window_metrics": [
    {
      "cap_off_duration_days": 39,
      "cap_on_duration_days": 85,
      "downshift_count": 2,
      "end": "2022-06-30",
      "event_name": "2022 H1 structural stress",
      "event_slice": "slower structural stress",
      "event_window_return": -0.2932863585184974,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "gap_adjusted_loss_contribution": 0.3604695827713466,
      "max_drawdown": -0.32352723887533763,
      "negative_gap_loss": 0.5844899998719963,
      "negative_regular_session_loss": 1.036978295395376,
      "policy_trigger_timing": {
        "new_first_trigger": "2022-01-24",
        "old_first_trigger": "2022-01-24",
        "peak_stress_date": "2022-05-20"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2022-06-16",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": null,
        "old_exit_after_low": null
      },
      "rows": 124,
      "start": "2022-01-03",
      "upshift_count": 1
    },
    {
      "cap_off_duration_days": 37,
      "cap_on_duration_days": 24,
      "downshift_count": 4,
      "end": "2018-12-31",
      "event_name": "Q4 2018 drawdown",
      "event_slice": "2018-style partially containable drawdowns",
      "event_window_return": -0.16715288078417123,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.6666666666666666,
      "gap_adjusted_loss_contribution": 0.30864608846047376,
      "max_drawdown": -0.22607933972641048,
      "negative_gap_loss": 0.23559326179530393,
      "negative_regular_session_loss": 0.5277187340587268,
      "policy_trigger_timing": {
        "new_first_trigger": "2018-10-26",
        "old_first_trigger": "2018-10-26",
        "peak_stress_date": "2018-12-24"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2018-12-24",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": null,
        "old_exit_after_low": null
      },
      "rows": 61,
      "start": "2018-10-03",
      "upshift_count": 3
    },
    {
      "cap_off_duration_days": 13,
      "cap_on_duration_days": 38,
      "downshift_count": 1,
      "end": "2020-04-30",
      "event_name": "COVID fast cascade",
      "event_slice": "2020-like fast cascades",
      "event_window_return": -0.06540906474654162,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "gap_adjusted_loss_contribution": 0.5786385874700565,
      "max_drawdown": -0.2855936032087112,
      "negative_gap_loss": 0.5850925790055248,
      "negative_regular_session_loss": 0.42606117339748517,
      "policy_trigger_timing": {
        "new_first_trigger": "2020-03-02",
        "old_first_trigger": "2020-03-02",
        "peak_stress_date": "2020-03-18"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2020-03-16",
        "new_days_from_low_to_exit": 32,
        "new_exit_after_low": "2020-04-17",
        "old_days_from_low_to_exit": 39,
        "old_exit_after_low": "2020-04-24"
      },
      "rows": 51,
      "start": "2020-02-19",
      "upshift_count": 1
    },
    {
      "cap_off_duration_days": 8,
      "cap_on_duration_days": 13,
      "downshift_count": 1,
      "end": "2015-09-15",
      "event_name": "August 2015 liquidity vacuum",
      "event_slice": "2015-style liquidity vacuum",
      "event_window_return": -0.03637695845233846,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "gap_adjusted_loss_contribution": 0.5300094029398391,
      "max_drawdown": -0.11971631510530512,
      "negative_gap_loss": 0.1652795362213908,
      "negative_regular_session_loss": 0.14656311280450118,
      "policy_trigger_timing": {
        "new_first_trigger": "2015-08-25",
        "old_first_trigger": "2015-08-25",
        "peak_stress_date": "2015-08-26"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2015-08-25",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": 20,
        "old_exit_after_low": "2015-09-14"
      },
      "rows": 21,
      "start": "2015-08-17",
      "upshift_count": 1
    },
    {
      "cap_off_duration_days": 22,
      "cap_on_duration_days": 22,
      "downshift_count": 1,
      "end": "2022-10-15",
      "event_name": "2022 bear rally relapse",
      "event_slice": "recovery-with-relapse",
      "event_window_return": -0.20939337024775595,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "gap_adjusted_loss_contribution": 0.41568350935889076,
      "max_drawdown": -0.21573123640288405,
      "negative_gap_loss": 0.23505151723396034,
      "negative_regular_session_loss": 0.33040636584752303,
      "policy_trigger_timing": {
        "new_first_trigger": "2022-09-15",
        "old_first_trigger": "2022-09-15",
        "peak_stress_date": "2022-10-11"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2022-10-14",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": null,
        "old_exit_after_low": null
      },
      "rows": 44,
      "start": "2022-08-15",
      "upshift_count": 0
    },
    {
      "cap_off_duration_days": 76,
      "cap_on_duration_days": 0,
      "downshift_count": 0,
      "end": "2023-11-15",
      "event_name": "2023 Q3/Q4 V-shape",
      "event_slice": "rapid V-shape",
      "event_window_return": 0.0065110249599660275,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "gap_adjusted_loss_contribution": 0.339815158527497,
      "max_drawdown": -0.10092359519716942,
      "negative_gap_loss": 0.16130798919260514,
      "negative_regular_session_loss": 0.31338534082714,
      "policy_trigger_timing": {
        "new_first_trigger": null,
        "old_first_trigger": null,
        "peak_stress_date": "2023-08-18"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2023-10-26",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": null,
        "old_exit_after_low": null
      },
      "rows": 76,
      "start": "2023-08-01",
      "upshift_count": 0
    },
    {
      "cap_off_duration_days": 9,
      "cap_on_duration_days": 76,
      "downshift_count": 1,
      "end": "2008-12-31",
      "event_name": "2008 financial crisis stress",
      "event_slice": "slower structural stress",
      "event_window_return": -0.3537887606259892,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "gap_adjusted_loss_contribution": 0.34050829632910223,
      "max_drawdown": -0.43848025401275015,
      "negative_gap_loss": 0.6258244845982152,
      "negative_regular_session_loss": 1.2120881047424983,
      "policy_trigger_timing": {
        "new_first_trigger": "2008-09-15",
        "old_first_trigger": "2008-09-15",
        "peak_stress_date": "2008-10-28"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2008-11-20",
        "new_days_from_low_to_exit": null,
        "new_exit_after_low": null,
        "old_days_from_low_to_exit": null,
        "old_exit_after_low": null
      },
      "rows": 85,
      "start": "2008-09-02",
      "upshift_count": 0
    },
    {
      "cap_off_duration_days": 50,
      "cap_on_duration_days": 23,
      "downshift_count": 1,
      "end": "2011-10-31",
      "event_name": "2011 downgrade liquidity shock",
      "event_slice": "2015-style liquidity vacuum",
      "event_window_return": -0.013466628585398488,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "gap_adjusted_loss_contribution": 0.4176044055606548,
      "max_drawdown": -0.16099299805518907,
      "negative_gap_loss": 0.3350397526403607,
      "negative_regular_session_loss": 0.46725004167000594,
      "policy_trigger_timing": {
        "new_first_trigger": "2011-08-08",
        "old_first_trigger": "2011-08-08",
        "peak_stress_date": "2011-08-22"
      },
      "provenance": "clean_room_recomputed_from_traceable_inputs",
      "recovery_timing_metrics": {
        "local_damage_low_date": "2011-08-19",
        "new_days_from_low_to_exit": 25,
        "new_exit_after_low": "2011-09-13",
        "old_days_from_low_to_exit": 21,
        "old_exit_after_low": "2011-09-09"
      },
      "rows": 73,
      "start": "2011-07-20",
      "upshift_count": 1
    }
  ],
  "event_windows": [
    {
      "end": "2022-06-30",
      "event_slice": "slower structural stress",
      "name": "2022 H1 structural stress",
      "start": "2022-01-03"
    },
    {
      "end": "2018-12-31",
      "event_slice": "2018-style partially containable drawdowns",
      "name": "Q4 2018 drawdown",
      "start": "2018-10-03"
    },
    {
      "end": "2020-04-30",
      "event_slice": "2020-like fast cascades",
      "name": "COVID fast cascade",
      "start": "2020-02-19"
    },
    {
      "end": "2015-09-15",
      "event_slice": "2015-style liquidity vacuum",
      "name": "August 2015 liquidity vacuum",
      "start": "2015-08-17"
    },
    {
      "end": "2022-10-15",
      "event_slice": "recovery-with-relapse",
      "name": "2022 bear rally relapse",
      "start": "2022-08-15"
    },
    {
      "end": "2023-11-15",
      "event_slice": "rapid V-shape",
      "name": "2023 Q3/Q4 V-shape",
      "start": "2023-08-01"
    },
    {
      "end": "2008-12-31",
      "event_slice": "slower structural stress",
      "name": "2008 financial crisis stress",
      "start": "2008-09-02"
    },
    {
      "end": "2011-10-31",
      "event_slice": "2015-style liquidity vacuum",
      "name": "2011 downgrade liquidity shock",
      "start": "2011-07-20"
    }
  ],
  "source_policy": {
    "legacy_artifacts_used_as_numeric_truth": false,
    "macro_liquidity_sources": [
      "data/macro_historical_dump.csv"
    ],
    "pit_note": "Daily features are same-day reconstructed for research; execution metrics use next-session state where policy returns are evaluated.",
    "primary_price_source": "data/qqq_history_cache.csv"
  },
  "summary": "Clean-room baseline rebuilt from QQQ daily OHLCV and repository macro/breadth inputs. Post-Phase-4.2 artifacts are quarantined as references only."
}
```
