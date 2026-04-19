# Final Decision 2008 Narrow Transfer Check

## Summary
The selected 2008 persistence variant is tested only against 2022 H1 and Q4 2018 analog paths.

## Decision
`2008_REFINEMENT_FAILS_TRANSFER_CHECK`

## Scope Discipline
This report is part of the final two-track decision phase. It does not restore candidate maturity, freezeability, deployment readiness, or a primary budget line.

## Machine-Readable Snapshot
```json
{
  "decision": "2008_REFINEMENT_FAILS_TRANSFER_CHECK",
  "held_out_gain": 0.0,
  "heldout_rows": [
    {
      "baseline_contribution": 0.125762,
      "event_name": "2022 H1 structural stress",
      "held_out_gain": 0.0,
      "neighboring_path_damage_increases": false,
      "residual_unrepaired_share_delta": 0.0,
      "selected_variant_contribution": 0.125762
    },
    {
      "baseline_contribution": 0.071979,
      "event_name": "Q4 2018 drawdown",
      "held_out_gain": 0.0,
      "neighboring_path_damage_increases": false,
      "residual_unrepaired_share_delta": 0.0,
      "selected_variant_contribution": 0.071979
    }
  ],
  "in_sample_gain": 0.017922,
  "neighboring_path_damage_increases": false,
  "rank_stability_check": {
    "event_gain_rows": [
      {
        "event_name": "2008 financial crisis stress",
        "gain": 0.017922
      },
      {
        "event_name": "2022 H1 structural stress",
        "gain": 0.0
      },
      {
        "event_name": "Q4 2018 drawdown",
        "gain": 0.0
      }
    ],
    "positive_event_count": 1,
    "rank_stability": "UNSTABLE",
    "reduced_line_set": [
      "current baseline persistence rule",
      "slightly earlier persistence lock variant"
    ]
  },
  "refinement_admissibility": "COLLAPSES",
  "selected_variant": "slightly earlier persistence lock variant",
  "sign_flips": true,
  "summary": "The selected 2008 persistence variant is tested only against 2022 H1 and Q4 2018 analog paths.",
  "track_a_status": "CLOSED",
  "transfer_ratio": 0.0
}
```
