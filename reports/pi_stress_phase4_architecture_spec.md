# pi_stress Phase 4 Architecture Spec

## Locked Roles

- Mainline: `two_stage_anomaly_severity`
- Challenger: `hierarchical_stress_posterior`
- Reference baseline: `C9_baseline_reference`

## Stage Semantics

Stage 1 estimates regime geometry, ambiguity, transition intensity, and healing tendency. Stage 2 estimates severity conditioned on Stage 1 and state evidence.

## Conductor Rule

`abstract_stage_outputs_only`

## Constraint Policy

{
  "full_six_class_independent_modeling": "ALLOWED_WITH_MONITORING",
  "taxonomy_policy": "six-class reporting allowed",
  "training_policy": "low-complexity interpretable deterministic/additive model only"
}
