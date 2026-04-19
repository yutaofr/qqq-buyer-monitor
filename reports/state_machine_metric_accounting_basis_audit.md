# State Machine Metric Accounting Basis Audit

## Summary
Several verdict-driving families are actual-executed internally, but budget and verdict layers remain mixed or ambiguous.

## Machine-Readable Snapshot
```json
{
  "mandatory_recomputation_required": true,
  "metric_families": [
    {
      "accounting_basis": "MIXED_OR_AMBIGUOUS",
      "basis_admissible": false,
      "metric_family": "structural non-defendability metrics",
      "recomputation_mandatory": true,
      "series_actually_used": "raw QQQ gap/intraday loss share; not a portfolio leverage accounting series",
      "where_computed": "scripts/convergence_research.py::build_structural_boundary"
    },
    {
      "accounting_basis": "MIXED_OR_AMBIGUOUS",
      "basis_admissible": false,
      "metric_family": "event-class loss contribution metrics",
      "recomputation_mandatory": true,
      "series_actually_used": "raw market loss plus integrated-stack benefit from actual executed leverage",
      "where_computed": "scripts/convergence_research.py::build_loss_contribution"
    },
    {
      "accounting_basis": "ACTUAL_EXECUTED_ONLY",
      "basis_admissible": true,
      "metric_family": "hazard timing/value metrics",
      "recomputation_mandatory": false,
      "series_actually_used": "executed = _executed_leverage(hazard_beta)",
      "where_computed": "scripts/convergence_research.py::_hazard_window_metrics"
    },
    {
      "accounting_basis": "ACTUAL_EXECUTED_ONLY",
      "basis_admissible": true,
      "metric_family": "hybrid decomposition metrics",
      "recomputation_mandatory": false,
      "series_actually_used": "policy_ret = executed * return",
      "where_computed": "scripts/convergence_research.py::_hybrid_metrics"
    },
    {
      "accounting_basis": "ACTUAL_EXECUTED_ONLY",
      "basis_admissible": true,
      "metric_family": "full-stack interaction contribution metrics",
      "recomputation_mandatory": false,
      "series_actually_used": "stack_ret = executed * return",
      "where_computed": "scripts/convergence_research.py::_stack_metrics_for_window"
    },
    {
      "accounting_basis": "MIXED_OR_AMBIGUOUS",
      "basis_admissible": false,
      "metric_family": "false re-entry / false exit metrics",
      "recomputation_mandatory": true,
      "series_actually_used": "state-count metrics mixed with executed-leverage damage metrics",
      "where_computed": "scripts/convergence_research.py::_variant_exit_metrics and _stack_metrics_for_window"
    },
    {
      "accounting_basis": "ACTUAL_EXECUTED_ONLY",
      "basis_admissible": true,
      "metric_family": "recovery miss metrics",
      "recomputation_mandatory": false,
      "series_actually_used": "computed from 2.0 - executed during positive-return recovery sessions",
      "where_computed": "scripts/convergence_research.py::_stack_metrics_for_window"
    },
    {
      "accounting_basis": "MIXED_OR_AMBIGUOUS",
      "basis_admissible": false,
      "metric_family": "budget allocation metrics",
      "recomputation_mandatory": true,
      "series_actually_used": "combines actual-executed benefits, raw losses, state counts, and complexity costs",
      "where_computed": "scripts/convergence_research.py::build_policy_competition/build_decision_framework"
    },
    {
      "accounting_basis": "MIXED_OR_AMBIGUOUS",
      "basis_admissible": false,
      "metric_family": "verdict-driving KPI",
      "recomputation_mandatory": true,
      "series_actually_used": "old checklist lacks a metric-accounting-basis gate",
      "where_computed": "scripts/convergence_research.py::build_final_verdict"
    }
  ],
  "summary": "Several verdict-driving families are actual-executed internally, but budget and verdict layers remain mixed or ambiguous.",
  "verdict_driving_non_actual_count": 3
}
```
