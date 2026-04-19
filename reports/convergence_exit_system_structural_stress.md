# Convergence Exit System Structural Stress

## Summary
Subtype sample budgets prevent a general claim. Multi-wave and monotonic paths are kept separate.

## Decision
`EXIT_SYSTEM_IS_VALUABLE_BUT_MAINLY_MULTI_WAVE_SPECIFIC`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "benefit_split_by_structural_subtype": {
    "monotonic structural stress": {
      "claim_strength_constraint": "sample_size_limited",
      "false_upshift_delta": 0.0,
      "wrongly_rerisked_day_delta": 0
    },
    "multi-wave structural stress": {
      "claim_strength_constraint": "sample_size_limited",
      "false_upshift_delta": 1.0,
      "wrongly_rerisked_day_delta": 17
    },
    "structural stress with recovery-relapse behavior": {
      "claim_strength_constraint": "sample_size_limited",
      "false_upshift_delta": 0.0,
      "wrongly_rerisked_day_delta": 0
    }
  },
  "decision": "EXIT_SYSTEM_IS_VALUABLE_BUT_MAINLY_MULTI_WAVE_SPECIFIC",
  "design": {
    "recovery_confirmation_signal": {
      "components": [
        "breadth repair amplitude",
        "realized volatility decay from peak",
        "price repair fraction",
        "persistence requirement",
        "breadth consistency through the ratchet"
      ],
      "role": "stress_exit_confirmation"
    },
    "regime_detection_signal": {
      "role": "stress_presence_detection"
    }
  },
  "monotonic_stress_real_improvement": {
    "receives_real_improvement": false,
    "subtype_conclusion": "descriptive because only one monotonic episode is available in this clean-room event set"
  },
  "multi_wave_stress_improvement": {
    "subtype_conclusion": "descriptive-to-directional, not a universal structural-stress proof",
    "wrongly_rerisked_days_current": 8
  },
  "subtype_sample_budget": [
    {
      "claim_strength_label": "DIRECTIONALLY_INFORMATIVE_BUT_NOT_DECISION_GRADE",
      "date_spans": [
        {
          "end": "2008-12-31",
          "name": "2008 financial crisis stress",
          "start": "2008-09-02"
        }
      ],
      "independent_episodes": 1,
      "sample_sufficiency": "directionally_informative_but_not_decision_grade",
      "subtype": "monotonic structural stress",
      "total_rows": 85
    },
    {
      "claim_strength_label": "DIRECTIONALLY_INFORMATIVE_BUT_NOT_DECISION_GRADE",
      "date_spans": [
        {
          "end": "2022-06-30",
          "name": "2022 H1 structural stress",
          "start": "2022-01-03"
        }
      ],
      "independent_episodes": 1,
      "sample_sufficiency": "directionally_informative_but_not_decision_grade",
      "subtype": "multi-wave structural stress",
      "total_rows": 124
    },
    {
      "claim_strength_label": "DESCRIPTIVE_ONLY",
      "date_spans": [
        {
          "end": "2022-10-15",
          "name": "2022 bear rally relapse",
          "start": "2022-08-15"
        }
      ],
      "independent_episodes": 1,
      "sample_sufficiency": "descriptive_only",
      "subtype": "structural stress with recovery-relapse behavior",
      "total_rows": 44
    }
  ],
  "summary": "Exit repair is useful as a stress-exit confirmer, with subtype limits kept explicit.",
  "variant_event_metrics": [
    {
      "event_name": "2022 H1 structural stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "recovery_reentry_delay": null,
      "subtype": "multi-wave structural stress",
      "variant": "posterior_decline_only",
      "worst_drawdown_after_false_exit": -0.15229453803916504,
      "wrongly_rerisked_unresolved_stress_days": 25
    },
    {
      "event_name": "2022 H1 structural stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "multi-wave structural stress",
      "variant": "current_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.1080747729288628,
      "wrongly_rerisked_unresolved_stress_days": 8
    },
    {
      "event_name": "2022 H1 structural stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "multi-wave structural stress",
      "variant": "stricter_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.050897367799486615,
      "wrongly_rerisked_unresolved_stress_days": 4
    },
    {
      "event_name": "2022 H1 structural stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "recovery_reentry_delay": null,
      "subtype": "multi-wave structural stress",
      "variant": "faster_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.15792542332947246,
      "wrongly_rerisked_unresolved_stress_days": 17
    },
    {
      "event_name": "2008 financial crisis stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "monotonic structural stress",
      "variant": "posterior_decline_only",
      "worst_drawdown_after_false_exit": -0.0680573249615245,
      "wrongly_rerisked_unresolved_stress_days": 9
    },
    {
      "event_name": "2008 financial crisis stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "monotonic structural stress",
      "variant": "current_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.0680573249615245,
      "wrongly_rerisked_unresolved_stress_days": 9
    },
    {
      "event_name": "2008 financial crisis stress",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "monotonic structural stress",
      "variant": "stricter_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.0680573249615245,
      "wrongly_rerisked_unresolved_stress_days": 9
    },
    {
      "event_name": "2008 financial crisis stress",
      "exit_timing_relative_to_local_damage_low": 41,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 1.0,
      "recovery_reentry_delay": 41,
      "subtype": "monotonic structural stress",
      "variant": "faster_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.0680573249615245,
      "wrongly_rerisked_unresolved_stress_days": 10
    },
    {
      "event_name": "2022 bear rally relapse",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "structural stress with recovery-relapse behavior",
      "variant": "posterior_decline_only",
      "worst_drawdown_after_false_exit": -0.06691440605938348,
      "wrongly_rerisked_unresolved_stress_days": 10
    },
    {
      "event_name": "2022 bear rally relapse",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "structural stress with recovery-relapse behavior",
      "variant": "current_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.06691440605938348,
      "wrongly_rerisked_unresolved_stress_days": 10
    },
    {
      "event_name": "2022 bear rally relapse",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "structural stress with recovery-relapse behavior",
      "variant": "stricter_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.06691440605938348,
      "wrongly_rerisked_unresolved_stress_days": 10
    },
    {
      "event_name": "2022 bear rally relapse",
      "exit_timing_relative_to_local_damage_low": null,
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "subtype": "structural stress with recovery-relapse behavior",
      "variant": "faster_repair_confirmer",
      "worst_drawdown_after_false_exit": -0.06691440605938348,
      "wrongly_rerisked_unresolved_stress_days": 10
    }
  ],
  "variants_compared": [
    "posterior_decline_only",
    "current_repair_confirmer",
    "stricter_repair_confirmer",
    "faster_repair_confirmer"
  ]
}
```
