# Final Product Late-Cycle UI Redesign

Diffuse `LATE_CYCLE` cases now render as a transition zone. The UI keeps the raw distribution, but the primary read becomes directional drift and mixed evidence rather than false certainty.

## Machine-Readable Snapshot
```json
{
  "decision": "LATE_CYCLE_IS_RENDERED_AS_A_TRANSITION_ZONE_WHEN_DIFFUSE",
  "structured_mock_evidence": {
    "action_band": "NO_ACTION_ZONE",
    "boundary_warning": {
      "evidence_shown": {
        "boundary_pressure": 0.0,
        "hazard_delta_5d": 0.06,
        "relapse_flag": false,
        "volatility_percentile": 0.64
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
        "status": "impaired",
        "ten_day_delta": -0.04,
        "value": 0.43
      },
      "hazard_percentile_context": {
        "five_day_delta": 0.06,
        "percentile": 0.6462,
        "status": "normal"
      },
      "hazard_score": 0.39,
      "repair_relapse_status": {
        "relapse_flag": false,
        "repair_confirmation": false,
        "repair_persistence_days": 1
      },
      "structural_stress_status": {
        "is_active": false,
        "stress_acceleration_5d": 0.0,
        "stress_delta_5d": 0.0,
        "stress_persistence_days": 7,
        "stress_score": 0.37
      },
      "volatility_regime_status": {
        "percentile": 0.64,
        "status": "contained",
        "ten_day_delta": 0.05
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
      "breadth_status": "impaired",
      "hazard_percentile": 0.6462,
      "hazard_score": 0.39,
      "late_cycle_transition_label": "Transition Zone",
      "rationale_summary": "LATE_CYCLE leads EXPANSION by 20.6%. Urgency is LOW; action relevance is NO_ACTION_ZONE. Hazard=0.39, breadth=0.43, volatility percentile=0.64. This is a cycle-stage probability read, not an automatic beta instruction.",
      "relapse_pressure": "LOW",
      "vol_status": "contained"
    },
    "late_cycle_transition": {
      "badge_text": "Transition zone / mixed evidence",
      "confidence_style": "SOFTENED",
      "direction": "UNRESOLVED_MIXED",
      "direction_text": "Unresolved / mixed transition",
      "display_label": "Transition Zone",
      "is_transition_zone": true,
      "raw_stage": "LATE_CYCLE"
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
        "probability": 0.2445768714,
        "trend": "FLAT"
      },
      "FAST_CASCADE_BOUNDARY": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.0107222989,
        "trend": "FLAT"
      },
      "LATE_CYCLE": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.4507546274,
        "trend": "FLAT"
      },
      "RECOVERY": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.0841220223,
        "trend": "FLAT"
      },
      "STRESS": {
        "acceleration_1d": 0.0,
        "delta_1d": 0.0,
        "probability": 0.2098241801,
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
      "banner_text": null,
      "is_active": false,
      "style": "HIDDEN"
    },
    "relapse_pressure": {
      "banner_text": null,
      "caution_active": false,
      "copy": "Repair looks comparatively clean; no major relapse pressure is currently dominant.",
      "level": "LOW",
      "score": 0.25,
      "visible": false
    },
    "stage_distribution": {
      "EXPANSION": 0.2445768714,
      "FAST_CASCADE_BOUNDARY": 0.0107222989,
      "LATE_CYCLE": 0.4507546274,
      "RECOVERY": 0.0841220223,
      "STRESS": 0.2098241801
    },
    "stage_stability": {
      "concentration_label": "MIXED",
      "human_readable": "The process is interpretable but not highly concentrated.",
      "normalized_entropy": 0.800345,
      "top1_margin": 0.206178,
      "top1_probability": 0.450755
    },
    "summary": {
      "confidence_margin": 0.206178,
      "current_stage": "LATE_CYCLE",
      "date": "2026-04-19",
      "display_badge": "Transition zone / mixed evidence",
      "display_stage": "Transition Zone",
      "secondary_stage": "EXPANSION",
      "short_rationale": "LATE_CYCLE leads EXPANSION by 20.6%. Urgency is LOW; action relevance is NO_ACTION_ZONE. Hazard=0.39, breadth=0.43, volatility percentile=0.64. This is a cycle-stage probability read, not an automatic beta instruction.",
      "stage_confidence": 0.450755,
      "stage_stability": "MIXED"
    },
    "transition_urgency": "LOW",
    "versions": {
      "calibration_version": "recovery_compliance_guarded",
      "engine_version": "v14.0-ULTIMA",
      "product_version": "final-product-v1",
      "ui_version": "daily-probability-dashboard-v2"
    }
  },
  "summary": "Diffuse late-cycle cases now foreground directional drift and ambiguity instead of false confidence."
}
```
