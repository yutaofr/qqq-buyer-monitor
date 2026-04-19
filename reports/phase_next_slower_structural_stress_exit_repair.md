# Phase Next Slower Structural Stress Exit Repair

## Decision
`REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING`

## Summary
Stress presence and stress exit are separated. Exit now requires breadth, volatility, price, and persistence repair evidence.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "decision": "REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING",
  "design": {
    "recovery_confirmation_signal": {
      "components": [
        "breadth_recovery_amplitude",
        "realized_volatility_decay",
        "price_repair_fraction",
        "persistence_days"
      ],
      "main_logic": "evidence_ratchet_not_calendar_hysteresis",
      "role": "stress_exit_confirmation"
    },
    "regime_detection_signal": {
      "inputs": [
        "price_damage",
        "realized_volatility",
        "gap_pressure",
        "breadth_proxy"
      ],
      "role": "stress_presence_detection"
    }
  },
  "experiment": {
    "new_exit_logic": {
      "description": "composite_repair_confirmation",
      "event_rows": [
        {
          "event_name": "2022 H1 structural stress",
          "false_downshift_frequency": 0.0,
          "false_upshift_frequency": 0.0,
          "recovery_reentry_delay_days": null,
          "shift_trigger_timing_consistency_days": null,
          "time_spent_wrongly_rerisked_during_unresolved_stress": 8,
          "worst_slice_drawdown_after_false_exit": -0.1080747729288628
        },
        {
          "event_name": "2008 financial crisis stress",
          "false_downshift_frequency": 0.0,
          "false_upshift_frequency": 0.0,
          "recovery_reentry_delay_days": null,
          "shift_trigger_timing_consistency_days": null,
          "time_spent_wrongly_rerisked_during_unresolved_stress": 9,
          "worst_slice_drawdown_after_false_exit": -0.0680573249615245
        }
      ]
    },
    "old_exit_logic": {
      "description": "posterior_decline_only",
      "event_rows": [
        {
          "event_name": "2022 H1 structural stress",
          "false_downshift_frequency": 0.0,
          "false_upshift_frequency": 1.0,
          "recovery_reentry_delay_days": null,
          "shift_trigger_timing_consistency_days": null,
          "time_spent_wrongly_rerisked_during_unresolved_stress": 25,
          "worst_slice_drawdown_after_false_exit": -0.15229453803916504
        },
        {
          "event_name": "2008 financial crisis stress",
          "false_downshift_frequency": 0.0,
          "false_upshift_frequency": 0.0,
          "recovery_reentry_delay_days": null,
          "shift_trigger_timing_consistency_days": null,
          "time_spent_wrongly_rerisked_during_unresolved_stress": 9,
          "worst_slice_drawdown_after_false_exit": -0.0680573249615245
        }
      ]
    }
  },
  "summary": "Stress presence and stress exit are separated. Exit now requires breadth, volatility, price, and persistence repair evidence.",
  "summary_metrics": {
    "new": {
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.0,
      "recovery_reentry_delay": null,
      "shift_trigger_timing_consistency": 0.0,
      "time_spent_wrongly_rerisked_during_unresolved_stress": 8.5,
      "worst_slice_drawdown_after_false_exit": -0.08806604894519365
    },
    "old": {
      "false_downshift_frequency": 0.0,
      "false_upshift_frequency": 0.5,
      "recovery_reentry_delay": null,
      "shift_trigger_timing_consistency": 0.0,
      "time_spent_wrongly_rerisked_during_unresolved_stress": 17.0,
      "worst_slice_drawdown_after_false_exit": -0.11017593150034477
    }
  }
}
```
