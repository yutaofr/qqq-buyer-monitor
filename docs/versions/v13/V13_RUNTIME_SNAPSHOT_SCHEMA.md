# v13 Runtime Snapshot Schema

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Purpose

This document defines the runtime snapshot contract for v13 overlay-enabled execution.

The goal is replayability. A reviewer must be able to reconstruct the full execution path from one snapshot file.

---

## 2. Versioning Rule

If overlay diagnostics are exported, the snapshot version must bump from the inherited v12 schema.

Required version string:

```text
v13_runtime_snapshot.v1
```

---

## 3. File Location

Reference path:

```text
artifacts/runtime_snapshots/snapshot_<observation_date>.json
```

The exact directory may follow existing repository conventions, but the schema version must remain explicit.

---

## 4. Top-Level Required Fields

The snapshot must contain:

```text
snapshot_version
captured_at_utc
observation_date
macro_data_path
regime_data_path
audit_path
overlay_audit_path
feature_contract
runtime_priors
prior_details
quality_audit
feature_weights
raw_t0_data
feature_vector
gaussian_nb
execution_overlay
final_execution
```

---

## 5. `execution_overlay` Block

The `execution_overlay` object must contain:

```text
enabled
mode
raw_inputs
input_quality
derived_features
negative_score
positive_score
beta_overlay_multiplier
deployment_overlay_multiplier
signal_contributions
admission_decisions
neutral_fallback_triggered
```

Requirements:

- `raw_inputs` stores only raw overlay evidence
- `derived_features` stores monotone transformed features
- `signal_contributions` makes the final multiplier traceable
- `admission_decisions` states why a source was admitted, downgraded, or rejected

---

## 6. `final_execution` Block

The `final_execution` object must contain:

```text
protected_beta_pre_overlay
overlay_beta
raw_target_beta
deployment_state_pre_overlay
deployment_state_post_overlay
behavioral_guard_input_beta
behavioral_guard_output_bucket
final_target_beta
```

This block exists to prove that v13 conditions action without mutating belief.

---

## 7. Compatibility Rule

v13 may preserve inherited v12 snapshot fields, but it may not silently overwrite their meaning.

In particular:

- `raw_target_beta` must retain its v12.1 meaning
- posterior probabilities must retain their v12.1 meaning
- new overlay fields must live in a clearly separate namespace

---

## 8. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-10` | runtime snapshot exports overlay diagnostics |
| `AC-15` | snapshot schema version bumps and carries full overlay decision trace |
| `tests/unit/engine/v11/test_conductor_overlay_integration.py` | snapshot wiring and field presence |
| `tests/integration/engine/v13/test_v13_shadow_mode.py` | end-to-end replayability |
