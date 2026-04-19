# Post-Patch Research-Line Admissibility Gate

## Summary
Every candidate line is gated before receiving bounded budget.

## Accounting Basis
All ranking metrics are recomputed from actual-executed portfolio returns. `residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.

## Machine-Readable Snapshot
```json
{
  "line_rows": [
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "PRIMARY_ADMISSIBLE",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "PRIMARY_OR_ELEVATED",
      "research_line": "slower structural subtype-specific work: 2008 financial crisis stress",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "BOUNDED_SECONDARY_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "slower structural subtype-specific work: 2022 H1 structural stress",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "BOUNDED_SECONDARY_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "slower structural stress exit refinement",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "CO_PRIMARY_ADMISSIBLE",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "PRIMARY_OR_ELEVATED",
      "research_line": "recovery-with-relapse refinement",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "BOUNDED_SECONDARY_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "hazard as slow-stress timing assistant",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE",
      "admissibility": "BOUNDED_SECONDARY_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "repair target",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "2018-style drawdown refinement",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "NOT_A_REPAIR_SCORE",
      "admissibility": "BOUNDARY_DISCLOSURE_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "boundary object",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "2020-like bounded observation only",
      "structural_boundary_status": "BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "NOT_A_REPAIR_SCORE",
      "admissibility": "BOUNDARY_DISCLOSURE_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "boundary object",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "2015-style bounded observation only",
      "structural_boundary_status": "BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "NOT_A_REPAIR_SCORE",
      "admissibility": "MONITORING_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "monitoring object",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "false re-entry monitoring",
      "structural_boundary_status": "NON_BOUNDARY"
    },
    {
      "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
      "actual_executed_contribution_sign": "NOT_A_REPAIR_SCORE",
      "admissibility": "MONITORING_ONLY",
      "interaction_stability": "PASSED_REQUIRED_TEST",
      "line_type": "monitoring object",
      "policy_improvable_share_level": "LOW_OR_NOT_SCORING",
      "research_line": "execution gate placeholder",
      "structural_boundary_status": "NON_BOUNDARY"
    }
  ],
  "summary": "Every candidate line is gated before receiving bounded budget."
}
```
