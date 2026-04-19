# Convergence Policy Architecture Competition

## Summary
Architecture competition is judged under spot-only daily regular-session constraints.

## Decision
`POLICY_ARCHITECTURE_HAS_TWO_BOUNDED_CONTENDERS`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "architectures": [
    {
      "account_feasibility_realism": "spot_only_feasible",
      "architecture": "repaired exit system without hybrid",
      "budgeted_complexity_cost": 1,
      "drawdown_contribution": -0.1803867778118216,
      "false_reentry": 2,
      "non_gap_drag": 0.13148800622129542,
      "post_gap_damage": -1.2627074446827513,
      "pre_gap_exposure_reduction": 0.2929928772034036,
      "recovery_miss": 1.281329553574195,
      "stack_reference": "exit repair only",
      "total_contribution": 0.49776804319333273,
      "turnover": 2
    },
    {
      "account_feasibility_realism": "spot_only_feasible",
      "architecture": "repaired exit system + redesigned hybrid",
      "budgeted_complexity_cost": 3,
      "drawdown_contribution": -0.16792340348704124,
      "false_reentry": 2,
      "non_gap_drag": 0.14180784233651603,
      "post_gap_damage": -1.1754638244092888,
      "pre_gap_exposure_reduction": 0.31962859331280374,
      "recovery_miss": 1.3950334462648193,
      "stack_reference": "exit repair + hybrid",
      "total_contribution": 0.5373105220358012,
      "turnover": 2
    },
    {
      "account_feasibility_realism": "spot_only_feasible",
      "architecture": "repaired exit system + hazard",
      "budgeted_complexity_cost": 2,
      "drawdown_contribution": -0.1803867778118216,
      "false_reentry": 2,
      "non_gap_drag": 0.17863135409949912,
      "post_gap_damage": -1.2627074446827513,
      "pre_gap_exposure_reduction": 0.337800843064001,
      "recovery_miss": 1.281329553574195,
      "stack_reference": "exit repair + hazard",
      "total_contribution": 0.4925294987429918,
      "turnover": 2
    },
    {
      "account_feasibility_realism": "spot_only_feasible",
      "architecture": "repaired exit system + hazard + redesigned hybrid",
      "budgeted_complexity_cost": 3,
      "drawdown_contribution": -0.16792340348704124,
      "false_reentry": 2,
      "non_gap_drag": 0.18895119021471973,
      "post_gap_damage": -1.1754638244092888,
      "pre_gap_exposure_reduction": 0.36443655917340134,
      "recovery_miss": 1.3950334462648193,
      "stack_reference": "full stack: exit repair + hazard + hybrid",
      "total_contribution": 0.5320719775854601,
      "turnover": 2
    },
    {
      "account_feasibility_realism": "bounded_secondary_only",
      "architecture": "bounded gearbox",
      "budgeted_complexity_cost": 3,
      "drawdown_contribution": -0.1803867778118216,
      "false_reentry": 2,
      "non_gap_drag": 0.13148800622129542,
      "post_gap_damage": -1.2627074446827513,
      "pre_gap_exposure_reduction": 0.2929928772034036,
      "recovery_miss": 1.281329553574195,
      "stack_reference": "exit repair only",
      "total_contribution": 0.49776804319333273,
      "turnover": 2
    }
  ],
  "best_architecture": {
    "account_feasibility_realism": "spot_only_feasible",
    "architecture": "repaired exit system + redesigned hybrid",
    "budgeted_complexity_cost": 3,
    "drawdown_contribution": -0.16792340348704124,
    "false_reentry": 2,
    "non_gap_drag": 0.14180784233651603,
    "post_gap_damage": -1.1754638244092888,
    "pre_gap_exposure_reduction": 0.31962859331280374,
    "recovery_miss": 1.3950334462648193,
    "stack_reference": "exit repair + hybrid",
    "total_contribution": 0.5373105220358012,
    "turnover": 2
  },
  "constraints": {
    "daily_signals": true,
    "no_derivatives": true,
    "no_shorting": true,
    "regular_session_execution": true,
    "spot_only": true
  },
  "decision": "POLICY_ARCHITECTURE_HAS_TWO_BOUNDED_CONTENDERS",
  "summary": "Architecture competition is judged under spot-only daily regular-session constraints."
}
```
