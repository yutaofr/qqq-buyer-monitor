# Cycle Stage Stack-To-Stage Translation

## Decision
`STACK_TO_STAGE_TRANSLATION_IS_HUMAN_USABLE`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "STACK_TO_STAGE_TRANSLATION_IS_HUMAN_USABLE",
  "latest_stage_output": {
    "boundary_warning": {
      "is_boundary_warning": false,
      "not_to_infer": null,
      "trigger_evidence": {
        "gap_pressure": 0.0026,
        "hazard_delta": 0.0013,
        "volatility_percentile": 0.9008
      },
      "warning_language": null
    },
    "current_stage_label": "LATE_CYCLE",
    "date": "2026-04-16",
    "evidence_panel": {
      "boundary_warnings": {
        "gap_pressure": 0.0026
      },
      "breadth_health_proxy": {
        "context": "weak_or_deteriorating",
        "delta": -0.0382,
        "value": 0.3835
      },
      "exit_repair_activation_state": {
        "repair_active": false,
        "repair_confirmation": false,
        "repair_persistence_days": 0,
        "stress_persistence_days": 0
      },
      "hazard_score": {
        "context": "elevated_or_rising",
        "delta": 0.0013,
        "value": 0.3363
      },
      "relapse_indicators": {
        "relapse_flag": false
      },
      "structural_stress_indicators": {
        "stress_score": 0.0682,
        "structural_stress": false
      },
      "volatility_proxy_percentile": {
        "context": "elevated_or_unstable",
        "delta": 0.0278,
        "value": 0.9008
      }
    },
    "human_guidance_layer": {
      "hard_leverage_number": null,
      "qualitative_beta_language": "beta can be considered moderate; aggressiveness deserves review"
    },
    "short_rationale": "LATE_CYCLE with LOW urgency: hazard=0.34, stress=0.07, breadth=0.38, vol_pct=0.90. This is a stage assessment, not a leverage order.",
    "stage_confidence": 0.78,
    "transition_urgency": "LOW"
  },
  "legibility_examples": {
    "FAST_CASCADE_BOUNDARY": "gap pressure or volatility acceleration makes the state a hard-constraint warning.",
    "LATE_CYCLE_instead_of_STRESS": "hazard and breadth deterioration exist, but repair lock or structural stress is not confirmed.",
    "RECOVERY_instead_of_EXPANSION": "repair evidence follows recent stress, so relapse risk remains visible."
  },
  "old_stack_to_new_stage_comparison": {
    "new_role": "the same evidence now informs stage label, confidence, transition urgency, and warning language",
    "not_a_rename": true,
    "old_role": "hazard/stress/repair previously informed cap, release, or beta policy state",
    "primary_product": "human-readable stage assessment"
  }
}
```
