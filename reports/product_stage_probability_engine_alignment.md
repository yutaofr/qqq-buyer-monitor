# Stage Probability Engine Alignment

## Decision
`STAGE_PROBABILITY_ENGINE_IS_ALIGNED`

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "STAGE_PROBABILITY_ENGINE_IS_ALIGNED",
  "hard_rule_result": "No hard label is emitted without exposing the full stage distribution.",
  "latest_daily_output": {
    "action_relevance_band": "NO_ACTION_ZONE",
    "boundary_warning": {
      "evidence_shown": {
        "boundary_pressure": 0.002602,
        "hazard_delta_5d": 0.001291,
        "relapse_flag": false,
        "volatility_percentile": 0.900794
      },
      "is_active": false,
      "not_to_infer": null,
      "visual_treatment": "hidden",
      "warning_text": null
    },
    "change_vs_yesterday": {
      "EXPANSION": -0.008873,
      "FAST_CASCADE_BOUNDARY": -0.007877,
      "LATE_CYCLE": 0.049688,
      "RECOVERY": -0.016238,
      "STRESS": -0.016699
    },
    "date": "2026-04-16",
    "distribution_change_20d": {
      "EXPANSION": -0.236599,
      "FAST_CASCADE_BOUNDARY": 0.001466,
      "LATE_CYCLE": 0.34875,
      "RECOVERY": -0.206751,
      "STRESS": 0.093135
    },
    "distribution_change_5d": {
      "EXPANSION": 0.05714,
      "FAST_CASCADE_BOUNDARY": -0.027071,
      "LATE_CYCLE": -0.027225,
      "RECOVERY": -0.001411,
      "STRESS": -0.001434
    },
    "dominant_stage": "LATE_CYCLE",
    "evidence_panel": {
      "boundary_pressure_gap_stress": {
        "boundary_pressure": 0.002602,
        "is_gap_stress_relevant": false
      },
      "breadth_health_status": {
        "status": "impaired",
        "ten_day_delta": -0.038237,
        "value": 0.383476
      },
      "hazard_percentile_context": {
        "five_day_delta": 0.001291,
        "percentile": 0.920635,
        "status": "extreme"
      },
      "hazard_score": 0.336331,
      "repair_relapse_status": {
        "relapse_flag": false,
        "repair_confirmation": false,
        "repair_persistence_days": 0
      },
      "structural_stress_status": {
        "is_active": false,
        "stress_acceleration_5d": 0.061156,
        "stress_delta_5d": -0.080858,
        "stress_persistence_days": 0,
        "stress_score": 0.068228
      },
      "volatility_regime_status": {
        "percentile": 0.900794,
        "status": "extreme",
        "ten_day_delta": 0.027778
      }
    },
    "expectation_section": {
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
    "probability_dynamics": {
      "EXPANSION": {
        "acceleration_1d": -0.0036234691,
        "delta_1d": -0.0088730944,
        "probability": 0.1784737672,
        "trend": "FALLING"
      },
      "FAST_CASCADE_BOUNDARY": {
        "acceleration_1d": 0.0031493446,
        "delta_1d": -0.0078773295,
        "probability": 0.0402011811,
        "trend": "FALLING"
      },
      "LATE_CYCLE": {
        "acceleration_1d": -0.0084680143,
        "delta_1d": 0.0496876128,
        "probability": 0.5679025521,
        "trend": "RISING"
      },
      "RECOVERY": {
        "acceleration_1d": 0.0079131363,
        "delta_1d": -0.0162383352,
        "probability": 0.0565539236,
        "trend": "FALLING"
      },
      "STRESS": {
        "acceleration_1d": 0.0010290025,
        "delta_1d": -0.0166988538,
        "probability": 0.156868576,
        "trend": "FALLING"
      }
    },
    "product": "Daily Post-Close Cycle Stage Probability Dashboard",
    "secondary_stage": "EXPANSION",
    "short_rationale": "LATE_CYCLE leads EXPANSION by 38.9%. Urgency is LOW; action relevance is NO_ACTION_ZONE. Hazard=0.34, breadth=0.38, volatility percentile=0.90. This is a cycle-stage probability read, not an automatic beta instruction.",
    "stage_probabilities": {
      "EXPANSION": 0.1784737672,
      "FAST_CASCADE_BOUNDARY": 0.0402011811,
      "LATE_CYCLE": 0.5679025521,
      "RECOVERY": 0.0565539236,
      "STRESS": 0.156868576
    },
    "stage_stability": {
      "concentration_label": "MODERATELY_CONCENTRATED",
      "human_readable": "The leading stage is clear, but the secondary stage matters.",
      "normalized_entropy": 0.752511,
      "top1_margin": 0.389429,
      "top1_probability": 0.567903
    },
    "transition_urgency": "LOW"
  },
  "required_checks": {
    "fast_cascade_non_ordinary": true,
    "interpretable_across_historical_windows": true,
    "label_ordering_consistent": true,
    "no_hidden_stage_omitted": true,
    "probabilities_sum_to_1": true
  },
  "required_outputs": {
    "confidence_stability_proxy": {
      "concentration_label": "MODERATELY_CONCENTRATED",
      "human_readable": "The leading stage is clear, but the secondary stage matters.",
      "normalized_entropy": 0.752511,
      "top1_margin": 0.389429,
      "top1_probability": 0.567903
    },
    "daily_process_history": "process frame includes daily probabilities, deltas, acceleration, urgency, and action band",
    "dominant_stage": "LATE_CYCLE",
    "probability_for_each_allowed_stage": true,
    "secondary_stage": "EXPANSION",
    "uncertainty_handling_when_diffuse": "DIFFUSE_OR_UNSTABLE concentration state and secondary-stage display"
  }
}
```
