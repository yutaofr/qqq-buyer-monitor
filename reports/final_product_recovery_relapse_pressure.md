# Final Product Recovery Relapse Pressure

RECOVERY is now paired with a user-facing relapse pressure field and caution banner. The field uses existing repair/relapse diagnostics rather than inventing a disconnected signal family.

## Machine-Readable Snapshot
```json
{
  "decision": "RECOVERY_RELAPSE_PRESSURE_IS_PRODUCTIZED",
  "display_levels": [
    "LOW",
    "ELEVATED",
    "HIGH"
  ],
  "relapse_pressure_field": "relapse_pressure",
  "structured_mock_evidence": {
    "action_band": "PREPARE_TO_ADJUST",
    "boundary_warning": {
      "evidence_shown": {
        "boundary_pressure": 0.0,
        "hazard_delta_5d": 0.05,
        "relapse_flag": true,
        "volatility_percentile": 0.67
      },
      "is_active": false,
      "not_to_infer": null,
      "visual_treatment": "hidden",
      "warning_text": null
    },
    "evidence_panel": {
      "boundary_pressure_gap_stress": {
        "boundary_pressure": 0.0,
        "is_gap_stress_relevant": false
      },
      "breadth_health_status": {
        "status": "weak",
        "ten_day_delta": -0.05,
        "value": 0.45
      },
      "hazard_percentile_context": {
        "five_day_delta": 0.05,
        "percentile": 0.6752,
        "status": "normal"
      },
      "hazard_score": 0.44,
      "repair_relapse_status": {
        "relapse_flag": true,
        "repair_confirmation": true,
        "repair_persistence_days": 6
      },
      "structural_stress_status": {
        "is_active": false,
        "stress_acceleration_5d": 0.0,
        "stress_delta_5d": 0.0,
        "stress_persistence_days": 8,
        "stress_score": 0.41
      },
      "volatility_regime_status": {
        "percentile": 0.67,
        "status": "elevated",
        "ten_day_delta": 0.08
      }
    },
    "expectations": {
      "what_not_to_expect": [
        "automatic leverage targeting",
        "automatic policy orders",
        "exact turning-point prediction",
        "FAST_CASCADE as a solved execution regime"
      ],
      "what_to_expect": [
        "daily post-close stage probability distribution",
        "current dominant and secondary stage",
        "transition pressure and action relevance for discretionary review",
        "evidence behind the stage process"
      ]
    },
    "export_fields": {
      "boundary_flag": false,
      "breadth_status": "weak",
      "hazard_percentile": 0.6752,
      "hazard_score": 0.44,
      "late_cycle_transition_label": "RECOVERY",
      "rationale_summary": "RECOVERY leads LATE_CYCLE by 5.0%. Urgency is HIGH; action relevance is PREPARE_TO_ADJUST. Hazard=0.44, breadth=0.45, volatility percentile=0.67. This is a cycle-stage probability read, not an automatic beta instruction.",
      "relapse_pressure": "HIGH",
      "vol_status": "elevated"
    },
    "late_cycle_transition": {
      "badge_text": null,
      "confidence_style": "STANDARD",
      "direction": "NOT_APPLICABLE",
      "direction_text": null,
      "display_label": "RECOVERY",
      "is_transition_zone": false
    },
    "limits": [
      "Do not infer automatic leverage.",
      "Do not infer exact turning-point prediction.",
      "Boundary warnings are warnings, not fine-grained action advice.",
      "True out-of-sample evidence starts accumulating only from deployment forward."
    ],
    "probability_dynamics": {
      "EXPANSION": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.1120395164,
        "trend": "FLAT"
      },
      "FAST_CASCADE_BOUNDARY": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.0157667671,
        "trend": "FLAT"
      },
      "LATE_CYCLE": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.3139986737,
        "trend": "FLAT"
      },
      "RECOVERY": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.3639452064,
        "trend": "FLAT"
      },
      "STRESS": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.1942498363,
        "trend": "FLAT"
      }
    },
    "product_name": "Daily Post-Close Cycle Stage Probability Dashboard",
    "product_scope": {
      "auto_beta_control_restored": false,
      "auto_trading_engine": false,
      "turning_point_prediction_solved": false
    },
    "reading_guide": [
      "1. Read dominant and secondary stage.",
      "2. Read Transition Urgency.",
      "3. Read Relapse Pressure and Boundary Warning.",
      "4. Only then decide whether this is worth a fresh discretionary beta review."
    ],
    "recovery_caution": {
      "banner_text": "Recovery signal is present, but relapse pressure is high. Do not treat this as an all-clear.",
      "is_active": true,
      "style": "RECOVERY_HIGH"
    },
    "relapse_pressure": {
      "banner_text": "Recovery signal is present, but relapse pressure is high. Do not treat this as an all-clear.",
      "caution_active": true,
      "copy": "Current repair signal is fragile; renewed drawdown risk remains high.",
      "level": "HIGH",
      "score": 1.0,
      "visible": true
    },
    "stage_distribution": {
      "EXPANSION": 0.1120395164,
      "FAST_CASCADE_BOUNDARY": 0.0157667671,
      "LATE_CYCLE": 0.3139986737,
      "RECOVERY": 0.3639452064,
      "STRESS": 0.1942498363
    },
    "stage_stability": {
      "concentration_label": "DIFFUSE_OR_UNSTABLE",
      "human_readable": "Probability mass is dispersed; read the transition panel before acting.",
      "normalized_entropy": 0.845362,
      "top1_margin": 0.049947,
      "top1_probability": 0.363945
    },
    "summary": {
      "confidence_margin": 0.049947,
      "current_stage": "RECOVERY",
      "date": "2026-04-19",
      "display_badge": null,
      "display_stage": "RECOVERY",
      "secondary_stage": "LATE_CYCLE",
      "short_rationale": "RECOVERY leads LATE_CYCLE by 5.0%. Urgency is HIGH; action relevance is PREPARE_TO_ADJUST. Hazard=0.44, breadth=0.45, volatility percentile=0.67. This is a cycle-stage probability read, not an automatic beta instruction.",
      "stage_confidence": 0.363945,
      "stage_stability": "DIFFUSE_OR_UNSTABLE"
    },
    "transition_urgency": "HIGH",
    "versions": {
      "calibration_version": "recovery_compliance_guarded",
      "engine_version": "v14.0-ULTIMA",
      "product_version": "final-product-v1",
      "ui_version": "daily-probability-dashboard-v2"
    }
  },
  "summary": "RECOVERY no longer reads as a clean all-clear when relapse pressure is not LOW."
}
```
