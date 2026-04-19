# Convergence Hybrid System Re-Derivation

## Summary
Hybrid is judged after recovery miss and interaction charges, not from local cap entry wins.

## Decision
`HYBRID_IS_NOT_WORTH_CONTINUED_PRIORITY`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "best_policy": {
    "entry_contribution": 1.04692344328155,
    "event_rows": [
      {
        "entry_contribution": 0.5748620800521708,
        "event_class": "2020-like fast-cascade / dominant overnight gap",
        "event_name": "COVID fast cascade",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.5237669447898842,
        "recovery_miss_cost": 0.50136038306875,
        "release_contribution": -0.021406561721134254
      },
      {
        "entry_contribution": 0.03750351813696109,
        "event_class": "2015-style liquidity vacuum / flash impairment",
        "event_name": "August 2015 liquidity vacuum",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.29576125083151994,
        "recovery_miss_cost": 0.19232977917000668,
        "release_contribution": -0.10243147166151326
      },
      {
        "entry_contribution": 0.021472966207413523,
        "event_class": "2018-style partially containable drawdown",
        "event_name": "Q4 2018 drawdown",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.008415824267468008,
        "recovery_miss_cost": 0.08969029513531623,
        "release_contribution": 0.08227447086784823
      },
      {
        "entry_contribution": 0.15286451598374146,
        "event_class": "slower structural stress",
        "event_name": "2022 H1 structural stress",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.060625012396443356,
        "recovery_miss_cost": 0.10495439864481781,
        "release_contribution": 0.04532938624837446
      },
      {
        "entry_contribution": 0.26022036290126305,
        "event_class": "slower structural stress",
        "event_name": "2008 financial crisis stress",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.1320231529594541,
        "recovery_miss_cost": 0.4761118562686023,
        "release_contribution": 0.3450887033091482
      },
      {
        "entry_contribution": 0.0,
        "event_class": "recovery-with-relapse",
        "event_name": "2022 bear rally relapse",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": 0.12465521906689891,
        "recovery_miss_cost": 0.0,
        "release_contribution": 0.12565521906689892
      },
      {
        "entry_contribution": 0.0,
        "event_class": "rapid V-shape ordinary correction",
        "event_name": "2023 Q3/Q4 V-shape",
        "interaction_cost_with_hazard_and_exit": 0.001,
        "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.001,
        "recovery_miss_cost": 0.0,
        "release_contribution": 0.0
      }
    ],
    "interaction_cost_with_hazard_and_exit": 0.007,
    "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.8969369661778707,
    "policy": "faster_recovery_sensitive_cap_release",
    "recovery_miss_cost": 1.364446712287493,
    "release_contribution": 0.47450974610962227
  },
  "class_contribution_questions": {
    "2015-style liquidity vacuum / flash impairment": {
      "net_contribution": -0.29576125083151994,
      "positive_after_costs": false
    },
    "2018-style partially containable drawdown": {
      "net_contribution": -0.008415824267468008,
      "positive_after_costs": false
    },
    "2020-like fast-cascade / dominant overnight gap": {
      "net_contribution": -0.5237669447898842,
      "positive_after_costs": false
    },
    "rapid V-shape ordinary correction": {
      "net_contribution": -0.001,
      "positive_after_costs": false
    },
    "recovery-with-relapse": {
      "net_contribution": 0.12465521906689891,
      "positive_after_costs": true
    },
    "slower structural stress": {
      "net_contribution": -0.1320231529594541,
      "positive_after_costs": false
    }
  },
  "decision": "HYBRID_IS_NOT_WORTH_CONTINUED_PRIORITY",
  "policy_families": [
    "symmetric_cap_release",
    "faster_recovery_sensitive_cap_release",
    "staged_cap_release"
  ],
  "policy_metrics": [
    {
      "entry_contribution": 1.0254504770741364,
      "event_rows": [
        {
          "entry_contribution": 0.5748620800521708,
          "event_class": "2020-like fast-cascade / dominant overnight gap",
          "event_name": "COVID fast cascade",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.6242530145760269,
          "recovery_miss_cost": 0.5892613548358048,
          "release_contribution": -0.03449165974022217
        },
        {
          "entry_contribution": 0.03750351813696109,
          "event_class": "2015-style liquidity vacuum / flash impairment",
          "event_name": "August 2015 liquidity vacuum",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.2669858152244824,
          "recovery_miss_cost": 0.1781920613664879,
          "release_contribution": -0.08829375385799448
        },
        {
          "entry_contribution": 0.0,
          "event_class": "2018-style partially containable drawdown",
          "event_name": "Q4 2018 drawdown",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.21164523210624098,
          "recovery_miss_cost": 0.08969029513531623,
          "release_contribution": -0.12145493697092474
        },
        {
          "entry_contribution": 0.15286451598374146,
          "event_class": "slower structural stress",
          "event_name": "2022 H1 structural stress",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": 0.021877871395726,
          "recovery_miss_cost": 0.10495439864481781,
          "release_contribution": 0.12733227004054382
        },
        {
          "entry_contribution": 0.26022036290126305,
          "event_class": "slower structural stress",
          "event_name": "2008 financial crisis stress",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.1315231529594541,
          "recovery_miss_cost": 0.4761118562686023,
          "release_contribution": 0.3450887033091482
        },
        {
          "entry_contribution": 0.0,
          "event_class": "recovery-with-relapse",
          "event_name": "2022 bear rally relapse",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": 0.12515521906689892,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.12565521906689892
        },
        {
          "entry_contribution": 0.0,
          "event_class": "rapid V-shape ordinary correction",
          "event_name": "2023 Q3/Q4 V-shape",
          "interaction_cost_with_hazard_and_exit": 0.0005,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.0005,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.0
        }
      ],
      "interaction_cost_with_hazard_and_exit": 0.0035,
      "net_system_contribution_after_recovery_miss_and_interaction_effects": -1.0878741244035794,
      "policy": "symmetric_cap_release",
      "recovery_miss_cost": 1.438209966251029,
      "release_contribution": 0.35383584184744954
    },
    {
      "entry_contribution": 1.04692344328155,
      "event_rows": [
        {
          "entry_contribution": 0.5748620800521708,
          "event_class": "2020-like fast-cascade / dominant overnight gap",
          "event_name": "COVID fast cascade",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.5237669447898842,
          "recovery_miss_cost": 0.50136038306875,
          "release_contribution": -0.021406561721134254
        },
        {
          "entry_contribution": 0.03750351813696109,
          "event_class": "2015-style liquidity vacuum / flash impairment",
          "event_name": "August 2015 liquidity vacuum",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.29576125083151994,
          "recovery_miss_cost": 0.19232977917000668,
          "release_contribution": -0.10243147166151326
        },
        {
          "entry_contribution": 0.021472966207413523,
          "event_class": "2018-style partially containable drawdown",
          "event_name": "Q4 2018 drawdown",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.008415824267468008,
          "recovery_miss_cost": 0.08969029513531623,
          "release_contribution": 0.08227447086784823
        },
        {
          "entry_contribution": 0.15286451598374146,
          "event_class": "slower structural stress",
          "event_name": "2022 H1 structural stress",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.060625012396443356,
          "recovery_miss_cost": 0.10495439864481781,
          "release_contribution": 0.04532938624837446
        },
        {
          "entry_contribution": 0.26022036290126305,
          "event_class": "slower structural stress",
          "event_name": "2008 financial crisis stress",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.1320231529594541,
          "recovery_miss_cost": 0.4761118562686023,
          "release_contribution": 0.3450887033091482
        },
        {
          "entry_contribution": 0.0,
          "event_class": "recovery-with-relapse",
          "event_name": "2022 bear rally relapse",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": 0.12465521906689891,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.12565521906689892
        },
        {
          "entry_contribution": 0.0,
          "event_class": "rapid V-shape ordinary correction",
          "event_name": "2023 Q3/Q4 V-shape",
          "interaction_cost_with_hazard_and_exit": 0.001,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.001,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.0
        }
      ],
      "interaction_cost_with_hazard_and_exit": 0.007,
      "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.8969369661778707,
      "policy": "faster_recovery_sensitive_cap_release",
      "recovery_miss_cost": 1.364446712287493,
      "release_contribution": 0.47450974610962227
    },
    {
      "entry_contribution": 1.04692344328155,
      "event_rows": [
        {
          "entry_contribution": 0.5748620800521708,
          "event_class": "2020-like fast-cascade / dominant overnight gap",
          "event_name": "COVID fast cascade",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.5529594474310446,
          "recovery_miss_cost": 0.51943436223717,
          "release_contribution": -0.0320250851938747
        },
        {
          "entry_contribution": 0.03750351813696109,
          "event_class": "2015-style liquidity vacuum / flash impairment",
          "event_name": "August 2015 liquidity vacuum",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.29626125083151994,
          "recovery_miss_cost": 0.19232977917000668,
          "release_contribution": -0.10243147166151326
        },
        {
          "entry_contribution": 0.021472966207413523,
          "event_class": "2018-style partially containable drawdown",
          "event_name": "Q4 2018 drawdown",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.032432024889331446,
          "recovery_miss_cost": 0.08969029513531623,
          "release_contribution": 0.05875827024598479
        },
        {
          "entry_contribution": 0.15286451598374146,
          "event_class": "slower structural stress",
          "event_name": "2022 H1 structural stress",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.011200944797641164,
          "recovery_miss_cost": 0.10495439864481781,
          "release_contribution": 0.09525345384717665
        },
        {
          "entry_contribution": 0.26022036290126305,
          "event_class": "slower structural stress",
          "event_name": "2008 financial crisis stress",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.1325231529594541,
          "recovery_miss_cost": 0.4761118562686023,
          "release_contribution": 0.3450887033091482
        },
        {
          "entry_contribution": 0.0,
          "event_class": "recovery-with-relapse",
          "event_name": "2022 bear rally relapse",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": 0.12415521906689891,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.12565521906689892
        },
        {
          "entry_contribution": 0.0,
          "event_class": "rapid V-shape ordinary correction",
          "event_name": "2023 Q3/Q4 V-shape",
          "interaction_cost_with_hazard_and_exit": 0.0015,
          "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.0015,
          "recovery_miss_cost": 0.0,
          "release_contribution": 0.0
        }
      ],
      "interaction_cost_with_hazard_and_exit": 0.0105,
      "net_system_contribution_after_recovery_miss_and_interaction_effects": -0.9027216018420924,
      "policy": "staged_cap_release",
      "recovery_miss_cost": 1.382520691455913,
      "release_contribution": 0.4902990896138206
    }
  ],
  "summary": "Hybrid is judged after recovery miss and interaction charges, not from local cap entry wins."
}
```
