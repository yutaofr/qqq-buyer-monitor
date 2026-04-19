# Frontier Blind-ish Event-Family Cross-Validation

## Summary
Blind-ish validation supports weak directional use only; it does not validate a hard budget rank.

## Decision
`BLINDISH_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_USE`

## Anti-Overclaiming Statement
This artifact does not restore candidate maturity, freezeability, deployment readiness, or robust OOS survival. Historical rankings are separated from transfer-aware budget use.

## Machine-Readable Snapshot
```json
{
  "candidate_line_rows": [
    {
      "blindish_performance_summary": {
        "held_out_policy_improvable_share": 0.033796,
        "validation_windows": [
          "Q4 2018 drawdown",
          "2023 Q3/Q4 V-shape"
        ]
      },
      "in_sample_performance_summary": {
        "policy_improvable_share": 0.145387,
        "source_windows": [
          "2022 bear rally relapse"
        ]
      },
      "neighboring_path_degradation": -0.111591,
      "rank_stability": "COLLAPSED",
      "research_line": "recovery-with-relapse refinement",
      "sign_stability": "SIGN_STABLE",
      "transfer_classification": "LOCAL_OR_WEAKLY_TRANSFERABLE"
    },
    {
      "blindish_performance_summary": {
        "held_out_policy_improvable_share": 0.067454,
        "validation_windows": [
          "2022 H1 structural stress",
          "Q4 2018 drawdown"
        ]
      },
      "in_sample_performance_summary": {
        "policy_improvable_share": 0.124347,
        "source_windows": [
          "2008 financial crisis stress"
        ]
      },
      "neighboring_path_degradation": -0.056893,
      "rank_stability": "STABLE",
      "research_line": "2008 subtype-specific structural repair",
      "sign_stability": "SIGN_STABLE",
      "transfer_classification": "TRANSFERABLE"
    },
    {
      "blindish_performance_summary": {
        "held_out_policy_improvable_share": 0.09597,
        "validation_windows": [
          "2008 financial crisis stress",
          "Q4 2018 drawdown"
        ]
      },
      "in_sample_performance_summary": {
        "policy_improvable_share": 0.067316,
        "source_windows": [
          "2022 H1 structural stress"
        ]
      },
      "neighboring_path_degradation": 0.028654,
      "rank_stability": "MATERIAL_CHANGE",
      "research_line": "2022 H1 subtype-specific structural repair",
      "sign_stability": "SIGN_STABLE",
      "transfer_classification": "LOCAL_OR_WEAKLY_TRANSFERABLE"
    },
    {
      "blindish_performance_summary": {
        "held_out_policy_improvable_share": 0.0,
        "validation_windows": [
          "2008 financial crisis stress",
          "Q4 2018 drawdown",
          "2022 bear rally relapse"
        ]
      },
      "in_sample_performance_summary": {
        "policy_improvable_share": 0.016454,
        "source_windows": [
          "2022 H1 structural stress"
        ]
      },
      "neighboring_path_degradation": -0.016454,
      "rank_stability": "COLLAPSED",
      "research_line": "hazard as slow-stress timing assistant",
      "sign_stability": "SIGN_UNSTABLE",
      "transfer_classification": "UNSTABLE"
    },
    {
      "blindish_performance_summary": {
        "held_out_policy_improvable_share": 0.033658,
        "validation_windows": [
          "August 2015 liquidity vacuum",
          "2022 H1 structural stress"
        ]
      },
      "in_sample_performance_summary": {
        "policy_improvable_share": 0.067592,
        "source_windows": [
          "Q4 2018 drawdown"
        ]
      },
      "neighboring_path_degradation": -0.033934,
      "rank_stability": "COLLAPSED",
      "research_line": "2018-style refinement",
      "sign_stability": "SIGN_STABLE",
      "transfer_classification": "LOCAL_OR_WEAKLY_TRANSFERABLE"
    }
  ],
  "decision": "BLINDISH_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_USE",
  "summary": "Blind-ish validation supports weak directional use only; it does not validate a hard budget rank.",
  "validation_designs": [
    "leave_one_major_window_out_validation",
    "cross_event_analog_validation",
    "year_separated_validation_where_feasible",
    "held_out_recombination_or_adversarial_block_validation"
  ]
}
```
