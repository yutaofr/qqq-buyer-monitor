# Phase Next Event-Slice Validation

## Summary
Validation is slice-first. Aggregate appears only after load-bearing event slices.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "aggregate_reported_last": true,
  "candidate_change_decisions": {
    "exit_repair": "REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING",
    "hazard_module": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
    "hybrid_release": "HYBRID_RELEASE_REDESIGN_HELPS_BUT_REMAINS_SECONDARY"
  },
  "pooled_score_optimization_used": false,
  "reporting_order": [
    "slower structural stress",
    "2018-style partially containable drawdowns",
    "2020-like fast cascades",
    "2015-style liquidity vacuum",
    "recovery-with-relapse",
    "rapid V-shape",
    "aggregate"
  ],
  "slice_results": [
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.3810037464440439,
      "event_slice": "slower structural stress",
      "false_exit_or_false_reentry": 0.0,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.47151885726725873,
      "policy_turnover": 4,
      "post_gap_damage": -0.18766111046503248,
      "pre_gap_exposure_reduction": 0.07546252371916509,
      "recovery_miss": 0.9430377145345175,
      "shift_signal_quality_change": 0.5
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.22607933972641048,
      "event_slice": "2018-style partially containable drawdowns",
      "false_exit_or_false_reentry": 0.0,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.15622048330362315,
      "policy_turnover": 1,
      "post_gap_damage": -0.043616212451805914,
      "pre_gap_exposure_reduction": 0.022131147540983605,
      "recovery_miss": 0.3124409666072463,
      "shift_signal_quality_change": 0.6666666666666666
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.2855936032087112,
      "event_slice": "2020-like fast cascades",
      "false_exit_or_false_reentry": 1.0,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.3132424817593382,
      "policy_turnover": 2,
      "post_gap_damage": -0.5676889407430674,
      "pre_gap_exposure_reduction": 0.17647058823529413,
      "recovery_miss": 0.6264849635186764,
      "shift_signal_quality_change": 0.0
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.1403546565802471,
      "event_slice": "2015-style liquidity vacuum",
      "false_exit_or_false_reentry": 0.5,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.11041438977742624,
      "policy_turnover": 3,
      "post_gap_damage": -0.12621420912090453,
      "pre_gap_exposure_reduction": 0.058561643835616434,
      "recovery_miss": 0.22082877955485247,
      "shift_signal_quality_change": 0.0
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.21573123640288405,
      "event_slice": "recovery-with-relapse",
      "false_exit_or_false_reentry": 0.0,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.05321676318259305,
      "policy_turnover": 1,
      "post_gap_damage": -0.05483641378977566,
      "pre_gap_exposure_reduction": 0.09204545454545456,
      "recovery_miss": 0.1064335263651861,
      "shift_signal_quality_change": 0.0
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.10092359519716942,
      "event_slice": "rapid V-shape",
      "false_exit_or_false_reentry": 0.0,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.0,
      "policy_turnover": 0,
      "post_gap_damage": 0.0,
      "pre_gap_exposure_reduction": 0.0,
      "recovery_miss": 0.0,
      "shift_signal_quality_change": 0.0
    },
    {
      "best_hybrid_policy_reference": "staged_cap_release",
      "drawdown_contribution": -0.23388057257296962,
      "event_slice": "aggregate",
      "false_exit_or_false_reentry": 0.25,
      "hazard_decision_reference": "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE",
      "non_gap_drag": 0.21081827779186557,
      "policy_turnover": 11,
      "post_gap_damage": -0.16173652576956538,
      "pre_gap_exposure_reduction": 0.06983694067891191,
      "recovery_miss": 0.42163655558373114,
      "shift_signal_quality_change": 0.20833333333333331
    }
  ],
  "summary": "Validation is slice-first. Aggregate appears only after load-bearing event slices."
}
```
