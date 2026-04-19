# Convergence Hazard System 2020-Like

## Summary
Hazard is bounded to pre-gap reduction and is timed against damage start and largest gap.

## Decision
`HAZARD_SYSTEM_IS_MATERIALLY_USEFUL_FOR_PRE_GAP_REDUCTION`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "architecture": {
    "additive_prior_like": true,
    "bounded": true,
    "exogenous": true,
    "implemented_as_top_level_hard_gate": false
  },
  "candidate_signals": [
    "FRA-OIS acceleration proxy",
    "repo/funding stress proxy",
    "treasury vol acceleration",
    "stress VIX acceleration"
  ],
  "decision": "HAZARD_SYSTEM_IS_MATERIALLY_USEFUL_FOR_PRE_GAP_REDUCTION",
  "first_material_damage_rule": {
    "price_only": true,
    "rule": "first close-to-prior-local-peak drawdown greater than 5 percent",
    "window_invariant": true
  },
  "non_gap_false_activation_audit": {
    "average_false_activation_rate": 0.014516129032258065
  },
  "structural_humility": {
    "claim_scope": "improvable pre-gap part only",
    "solves_2020_like_survivability": false
  },
  "summary": "Hazard is bounded to pre-gap reduction and is timed against damage start and largest gap.",
  "tested_windows": [
    {
      "actual_effective_leverage_reduction": 0.5684210526315789,
      "cumulative_drawdown_already_suffered_at_first_warning": -0.13224730468260903,
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "exposure_baseline_definition": "2.0 QLD-like target leverage before bounded hazard adjustment",
      "exposure_reduction_achieved_before_largest_gap_date": 0.28421052631578947,
      "first_hazard_warning_date": "2020-02-27",
      "first_material_damage_date": "2020-02-24",
      "largest_gap_date": "2020-03-16",
      "pre_gap_cumulative_loss_reduction_account_terms": 0.3634383664232945,
      "warning_lead_vs_first_material_damage_date": -3,
      "warning_lead_vs_largest_gap_date": 18
    },
    {
      "actual_effective_leverage_reduction": 0.0,
      "cumulative_drawdown_already_suffered_at_first_warning": null,
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "exposure_baseline_definition": "2.0 QLD-like target leverage before bounded hazard adjustment",
      "exposure_reduction_achieved_before_largest_gap_date": 0.0,
      "first_hazard_warning_date": null,
      "first_material_damage_date": "2015-08-21",
      "largest_gap_date": "2015-08-24",
      "pre_gap_cumulative_loss_reduction_account_terms": 0.0,
      "warning_lead_vs_first_material_damage_date": null,
      "warning_lead_vs_largest_gap_date": null
    }
  ]
}
```
