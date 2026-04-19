# Cycle Stage Dashboard Spec

## Decision
`DASHBOARD_SPEC_IS_READY_FOR_IMPLEMENTATION`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "components": [
    "current stage label",
    "stage confidence",
    "transition urgency",
    "hazard score raw plus context",
    "breadth health status",
    "volatility regime status",
    "repair / relapse status",
    "boundary warning",
    "short rationale text",
    "change vs yesterday",
    "discretionary beta thinking note without hard leverage number"
  ],
  "decision": "DASHBOARD_SPEC_IS_READY_FOR_IMPLEMENTATION",
  "forbidden_dashboard_outputs": [
    "hard leverage number",
    "automatic policy order",
    "turning-point prediction claim"
  ],
  "human_interpretability_test": {
    "passes": true,
    "reason": "The first screen can be read as stage, confidence, urgency, evidence, and one qualitative guidance note.",
    "target_read_time_seconds": 60
  },
  "latest_mock": {
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
  "what_the_system_does_not_know": [
    "It does not know exact turning dates.",
    "It does not know next-session gap execution.",
    "It does not know the user's account-level constraints."
  ]
}
```
