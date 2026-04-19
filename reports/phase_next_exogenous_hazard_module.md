# Phase Next Exogenous Hazard Module

## Decision
`EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE`

## Summary
A bounded exogenous hazard function is rebuilt from traceable macro/liquidity proxies. It targets only pre-gap exposure reduction.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "architecture": {
    "implemented_as_top_level_orchestrator_gate": false,
    "integration_mode": "bounded_additive_or_prior_like_policy_input",
    "module_type": "bounded_exogenous_hazard_function"
  },
  "candidate_signals": {
    "FRA_OIS_acceleration_proxy": "credit_spread_bps five-day acceleration z-score",
    "related_liquidity_funding_signals": [
      "stress_vix_acceleration",
      "treasury_vol_21d_acceleration"
    ],
    "repo_or_funding_stress_proxy": "net_liquidity drawdown, liquidity_roc deterioration, funding_stress_flag"
  },
  "decision": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
  "structural_humility": {
    "claim_scope": "reduces only the improvable pre-gap portion if validated further",
    "solves_2020_like_survivability": false
  },
  "summary": "A bounded exogenous hazard function is rebuilt from traceable macro/liquidity proxies. It targets only pre-gap exposure reduction.",
  "summary_metrics": {
    "conflict_rate_with_slower_structural_stress_handling": 0.026195868316394165,
    "days_of_earlier_warning": 18,
    "exposure_reduction_achieved_before_largest_gap_date": 0.45,
    "false_hazard_activation_frequency": 0.022847100175746926,
    "first_warning_date": "2020-02-27",
    "impact_on_recovery_miss": 0.8945854641008336,
    "largest_gap_date": "2020-03-16",
    "pre_gap_cumulative_loss_reduction": 0.2556294399673167
  }
}
```
