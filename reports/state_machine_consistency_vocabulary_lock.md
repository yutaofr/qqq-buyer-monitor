# State Machine Consistency Vocabulary Lock

## Summary
State/accounting vocabulary is locked; later reports use these terms without redefinition.

## Machine-Readable Snapshot
```json
{
  "hard_rule": "No later workstream may redefine or blur these terms.",
  "summary": "State/accounting vocabulary is locked; later reports use these terms without redefinition.",
  "terms": {
    "accounting_basis": "Metric provenance label identifying whether the computation used theoretical target leverage, actual executed leverage, or a mixture/ambiguous basis.",
    "actual_executed_leverage": "The leverage actually borne by the modeled portfolio return for that date/session. In current clean-room code this equals theoretical_target_leverage shifted by one session.",
    "designed_execution_delay": "A documented rule that intentionally causes actual leverage to lag theoretical target; the current clean-room rule is target.shift(1).fillna(2.0).",
    "execution_state": "Actionable state after timing, delay, batching, or translation rules. In the clean-room convergence script this is next-session executable leverage.",
    "policy_state": "Aggregated intended portfolio posture after combining hazard, exit repair, and hybrid cap rules, but before execution timing is applied.",
    "signal_state": "Raw logical state emitted by a model or policy module before execution translation; examples include hazard_active, repair_active, and hybrid_active booleans.",
    "state_translation_mismatch": "A mismatch between policy/theoretical and actual executed state caused by translation logic, timing rules, or implementation details.",
    "theoretical_target_leverage": "The leverage the portfolio would hold if policy_state were applied immediately and frictionlessly on the same session.",
    "unexplained_inconsistency": "Any theoretical-vs-actual divergence not explicitly documented as designed behavior."
  }
}
```
