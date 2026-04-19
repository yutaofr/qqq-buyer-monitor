# State Machine Translation Path Reconstruction

## Summary
The translation path has a deliberate next-session execution lag, but accounting-basis documentation is incomplete.

## Machine-Readable Snapshot
```json
{
  "chain": [
    {
      "code_reference": "scripts/convergence_research.py::_hazard_active",
      "delay_rule": "none",
      "documented_in_reports": true,
      "explicit_in_code": true,
      "input_variable": "hazard_score",
      "leverage_change_timing": "later, after policy aggregation and execution translation",
      "stage": "hazard output",
      "transformation_rule": "hazard_active = hazard_score >= 0.38"
    },
    {
      "code_reference": "scripts/convergence_research.py::_repair_conditions",
      "delay_rule": "persistence delays stress release",
      "documented_in_reports": true,
      "explicit_in_code": true,
      "input_variable": "stress_score, breadth_proxy, vol_21, close, persistence",
      "leverage_change_timing": "later, through target cap assignment",
      "stage": "exit/repair output",
      "transformation_rule": "repair_active remains true until breadth, vol, price, and persistence release conditions pass"
    },
    {
      "code_reference": "scripts/convergence_research.py::_hybrid_active and _target_leverage",
      "delay_rule": "three-session staged cap after release",
      "documented_in_reports": true,
      "explicit_in_code": true,
      "input_variable": "hybrid_active and staged release state",
      "leverage_change_timing": "immediate target cap, later executed after one-session lag",
      "stage": "hybrid/cap output",
      "transformation_rule": "active hybrid caps target at 0.8; staged release caps target at 1.35 for three sessions"
    },
    {
      "code_reference": "scripts/convergence_research.py::_target_leverage",
      "delay_rule": "none inside aggregation",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "exit repair active, hazard active, hybrid active",
      "leverage_change_timing": "theoretical target changes immediately",
      "stage": "policy aggregation rule",
      "transformation_rule": "start at 2.0; apply min caps of 0.9, 1.1, and 0.8/1.35"
    },
    {
      "code_reference": "scripts/convergence_research.py::_target_leverage",
      "delay_rule": "none",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "policy_state",
      "leverage_change_timing": "same-session theoretical posture",
      "stage": "theoretical target leverage assignment",
      "transformation_rule": "policy cap result is assigned to theoretical_target_leverage"
    },
    {
      "code_reference": "scripts/convergence_research.py::_executed_leverage",
      "delay_rule": "one-session next-session executable leverage delay",
      "documented_in_reports": true,
      "explicit_in_code": true,
      "input_variable": "theoretical_target_leverage",
      "leverage_change_timing": "next-session executable leverage",
      "stage": "execution translation rule",
      "transformation_rule": "actual_executed_leverage = theoretical_target_leverage.shift(1).fillna(2.0)"
    },
    {
      "code_reference": "scripts/convergence_research.py::_stack_metrics_for_window",
      "delay_rule": "inherits one-session delay",
      "documented_in_reports": true,
      "explicit_in_code": true,
      "input_variable": "execution_state",
      "leverage_change_timing": "current modeled accounting session",
      "stage": "actual executed leverage assignment",
      "transformation_rule": "portfolio return uses actual_executed_leverage * QQQ close-to-close return"
    },
    {
      "code_reference": "scripts/convergence_research.py::build_*",
      "delay_rule": "metric-dependent",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "actual_executed_leverage, theoretical_target_leverage, raw price losses",
      "leverage_change_timing": "not a state change; accounting basis classification required",
      "stage": "metric accounting layer",
      "transformation_rule": "stack metrics generally use actual executed leverage; some budget/verdict families mix raw losses with actual benefits"
    }
  ],
  "governance_defects": [
    {
      "code_reference": "scripts/convergence_research.py::_target_leverage",
      "delay_rule": "none inside aggregation",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "exit repair active, hazard active, hybrid active",
      "leverage_change_timing": "theoretical target changes immediately",
      "stage": "policy aggregation rule",
      "transformation_rule": "start at 2.0; apply min caps of 0.9, 1.1, and 0.8/1.35"
    },
    {
      "code_reference": "scripts/convergence_research.py::_target_leverage",
      "delay_rule": "none",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "policy_state",
      "leverage_change_timing": "same-session theoretical posture",
      "stage": "theoretical target leverage assignment",
      "transformation_rule": "policy cap result is assigned to theoretical_target_leverage"
    },
    {
      "code_reference": "scripts/convergence_research.py::build_*",
      "delay_rule": "metric-dependent",
      "documented_in_reports": false,
      "explicit_in_code": true,
      "input_variable": "actual_executed_leverage, theoretical_target_leverage, raw price losses",
      "leverage_change_timing": "not a state change; accounting basis classification required",
      "stage": "metric accounting layer",
      "transformation_rule": "stack metrics generally use actual executed leverage; some budget/verdict families mix raw losses with actual benefits"
    }
  ],
  "summary": "The translation path has a deliberate next-session execution lag, but accounting-basis documentation is incomplete."
}
```
