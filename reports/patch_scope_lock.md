# Patch Scope Lock

## Summary
Patch scope is locked to accounting, metric role separation, and verdict gates.

## Machine-Readable Snapshot
```json
{
  "hard_rule": "No patch workstream introduces policy architecture logic unless strictly required for accounting reconstruction.",
  "known_mixed_or_ambiguous_families": [
    {
      "metric_family": "event-class loss contribution metrics",
      "object_layer": "data-layer object",
      "old_basis": "MIXED_OR_AMBIGUOUS",
      "patch_action": "rebuild in unified actual-executed portfolio return space"
    },
    {
      "metric_family": "structural non-defendability metrics",
      "object_layer": "boundary-layer object",
      "old_basis": "MIXED_OR_AMBIGUOUS",
      "patch_action": "reclassify as MARKET_STRUCTURE_ATTRIBUTION and remove from scoring"
    },
    {
      "metric_family": "false re-entry / false exit metrics",
      "object_layer": "diagnostic object",
      "old_basis": "MIXED_OR_AMBIGUOUS",
      "patch_action": "split count diagnostics from actual-executed damage accounting"
    },
    {
      "metric_family": "budget allocation metrics",
      "object_layer": "verdict-layer object",
      "old_basis": "MIXED_OR_AMBIGUOUS",
      "patch_action": "rebuild from policy value vector plus separate structural constraint vector"
    },
    {
      "metric_family": "verdict-driving KPI",
      "object_layer": "verdict-layer object",
      "old_basis": "MIXED_OR_AMBIGUOUS",
      "patch_action": "bind to accounting-basis pre-gate"
    }
  ],
  "required_statements": {
    "does_not_optimize_model_modules": true,
    "does_not_reopen_gearbox_as_primary": true,
    "does_not_reopen_hybrid_as_primary": true,
    "does_not_reopen_residual_protection_operationalization": true,
    "repairs_only_accounting_role_separation_and_gates": true
  },
  "summary": "Patch scope is locked to accounting, metric role separation, and verdict gates."
}
```
