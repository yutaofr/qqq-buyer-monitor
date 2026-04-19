# Patch Event-Class Loss Contribution

## Summary
Event-class loss contribution is rebuilt in one portfolio-return accounting space.

## Decision
`LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN`

## Machine-Readable Snapshot
```json
{
  "accounting_basis": "ACTUAL_EXECUTED_ONLY",
  "decision": "LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN",
  "definitions": {
    "baseline_return": "return of baseline portfolio under baseline leverage and actual execution convention",
    "policy_contribution": "policy_return - baseline_return",
    "policy_return": "return of patched full-stack portfolio under actual executed leverage"
  },
  "event_class_rows": [
    {
      "baseline_cumulative_return_contribution": -0.063301,
      "baseline_tail_loss_contribution": 0.226871,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_count": 1.0,
      "policy_contribution": -0.102431,
      "policy_cumulative_return_contribution": -0.165732,
      "policy_improvable_share": 0.0,
      "policy_tail_loss_contribution": 0.189367,
      "residual_unrepaired_share": 0.775535
    },
    {
      "baseline_cumulative_return_contribution": -0.338712,
      "baseline_tail_loss_contribution": 0.509697,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "2018-style partially containable drawdown",
      "event_count": 1.0,
      "policy_contribution": 0.078835,
      "policy_cumulative_return_contribution": -0.259877,
      "policy_improvable_share": 0.067592,
      "policy_tail_loss_contribution": 0.318711,
      "residual_unrepaired_share": 0.617617
    },
    {
      "baseline_cumulative_return_contribution": -0.048398,
      "baseline_tail_loss_contribution": 0.834123,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_count": 1.0,
      "policy_contribution": -0.08652,
      "policy_cumulative_return_contribution": -0.134918,
      "policy_improvable_share": 0.0,
      "policy_tail_loss_contribution": 0.393738,
      "residual_unrepaired_share": 0.560198
    },
    {
      "baseline_cumulative_return_contribution": 0.022427,
      "baseline_tail_loss_contribution": 0.309752,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "rapid V-shape ordinary correction",
      "event_count": 1.0,
      "policy_contribution": 0.0,
      "policy_cumulative_return_contribution": 0.022427,
      "policy_improvable_share": 0.0,
      "policy_tail_loss_contribution": 0.309752,
      "residual_unrepaired_share": 1.0
    },
    {
      "baseline_cumulative_return_contribution": -0.45428,
      "baseline_tail_loss_contribution": 0.385626,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "recovery-with-relapse",
      "event_count": 1.0,
      "policy_contribution": 0.125655,
      "policy_cumulative_return_contribution": -0.328625,
      "policy_improvable_share": 0.145387,
      "policy_tail_loss_contribution": 0.26924,
      "residual_unrepaired_share": 0.706836
    },
    {
      "baseline_cumulative_return_contribution": -1.390193,
      "baseline_tail_loss_contribution": 2.155862,
      "basis_proof": {
        "baseline_return": "baseline_actual_executed_return",
        "policy_contribution": "policy_return - baseline_return",
        "policy_return": "policy_actual_executed_return"
      },
      "event_class": "slower structural stress",
      "event_count": 2.0,
      "policy_contribution": 0.516533,
      "policy_cumulative_return_contribution": -0.87366,
      "policy_improvable_share": 0.097055,
      "policy_tail_loss_contribution": 0.948031,
      "residual_unrepaired_share": 0.47412
    }
  ],
  "summary": "Event-class loss contribution is rebuilt in one portfolio-return accounting space."
}
```
