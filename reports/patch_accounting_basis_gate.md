# Patch Accounting Basis Gate

## Summary
Accounting-basis gate executes before verdict construction and blocks mixed-input paths.

## Decision
`ACCOUNTING_BASIS_GATE_IS_OPERATIONAL`

## Machine-Readable Snapshot
```json
{
  "admissible_classes": {
    "ACTUAL_EXECUTED_ONLY": {
      "may_enter_budget_scoring": true,
      "may_enter_verdict_aggregation": true
    },
    "MARKET_STRUCTURE_ATTRIBUTION": {
      "allowed_role": "boundary constraint / override / disclosure context",
      "may_enter_budget_scoring": false,
      "may_enter_verdict_aggregation": false
    },
    "MIXED_OR_AMBIGUOUS": {
      "blocked": true,
      "may_enter_budget_scoring": false,
      "may_enter_verdict_aggregation": false
    }
  },
  "blocked_metric_entered_aggregation": false,
  "decision": "ACCOUNTING_BASIS_GATE_IS_OPERATIONAL",
  "execution_order": "PRE_VERDICT",
  "family_gate_rows": [
    {
      "allowed_role": "verdict aggregation and budget scoring",
      "basis_classification": "ACTUAL_EXECUTED_ONLY",
      "blocked": false,
      "metric_family": "event-class loss contribution metrics",
      "prior_use_invalid": true
    },
    {
      "allowed_role": "boundary constraint / override / disclosure context only",
      "basis_classification": "MARKET_STRUCTURE_ATTRIBUTION",
      "blocked": false,
      "blocked_from_scoring": true,
      "metric_family": "structural non-defendability metrics",
      "prior_use_invalid": true
    },
    {
      "allowed_role": "diagnostic reporting only",
      "basis_classification": "DIAGNOSTIC_ONLY",
      "blocked": true,
      "metric_family": "false re-entry / exit count metrics",
      "prior_use_invalid": true
    },
    {
      "allowed_role": "verdict aggregation and budget scoring",
      "basis_classification": "ACTUAL_EXECUTED_ONLY",
      "blocked": false,
      "metric_family": "false re-entry / exit damage metrics",
      "prior_use_invalid": false
    },
    {
      "allowed_role": "budget scoring after pre-gate",
      "basis_classification": "ACTUAL_EXECUTED_ONLY_WITH_SEPARATE_MARKET_STRUCTURE_CONSTRAINTS",
      "blocked": false,
      "metric_family": "budget allocation metrics",
      "prior_use_invalid": true
    },
    {
      "allowed_role": "none",
      "basis_classification": "MIXED_OR_AMBIGUOUS",
      "blocked": true,
      "metric_family": "old mixed-input verdict path",
      "prior_use_invalid": true
    }
  ],
  "summary": "Accounting-basis gate executes before verdict construction and blocks mixed-input paths."
}
```
