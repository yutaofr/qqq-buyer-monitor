# Convergence Integrated Interaction Validation

## Summary
Stacks are compared jointly; the full-stack result is judged for temporal collisions.

## Decision
`FULL_STACK_INTERACTION_HAS_ONE_OR_MORE_CRITICAL_COLLISIONS`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "critical_path_studies": {
    "2008 monotonic structural stress path": {
      "event_class": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.23564988565263115,
      "pre_gap_reduction_gained": 0.8923076923076925,
      "recovery_miss_accumulated": 0.4761118562686023,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": 0.3450887033091482
    },
    "2015-style liquidity vacuum path": {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10195617372444973,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.19232977917000668,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.10243147166151326
    },
    "2020-like fast cascade path": {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.560515801433964,
      "pre_gap_reduction_gained": 0.726315789473684,
      "recovery_miss_accumulated": 0.5319471170460762,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.08651971855320648
    },
    "2022 H1 multi-wave structural stress path": {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.10190967732249429,
      "pre_gap_reduction_gained": 0.9324324324324327,
      "recovery_miss_accumulated": 0.10495439864481781,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": 0.17144397768973801
    }
  },
  "decision": "FULL_STACK_INTERACTION_HAS_ONE_OR_MORE_CRITICAL_COLLISIONS",
  "diagnostic_answers": {
    "false_reentry_cause": "no dominant false reentry in audited rows",
    "hazard_derisk_contaminated_later_repair_confirmation": false,
    "hybrid_release_speed_mismatched_repair_confirmation": false
  },
  "stack_event_metrics": [
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -1.1353778814861348,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.0,
      "stack": "baseline stack",
      "total_system_contribution_vs_baseline": 0.0
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.6084209747716449,
      "pre_gap_reduction_gained": 0.5789473684210527,
      "recovery_miss_accumulated": 0.49016708512368057,
      "stack": "exit repair only",
      "total_system_contribution_vs_baseline": -0.0375924905315749
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.7734253621914686,
      "pre_gap_reduction_gained": 0.5684210526315789,
      "recovery_miss_accumulated": 0.19139791471763512,
      "stack": "hazard only",
      "total_system_contribution_vs_baseline": 0.03140421127444831
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.560515801433964,
      "pre_gap_reduction_gained": 0.6315789473684209,
      "recovery_miss_accumulated": 0.51943436223717,
      "stack": "hybrid redesign only",
      "total_system_contribution_vs_baseline": -0.0320250851938747
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.6084209747716449,
      "pre_gap_reduction_gained": 0.6736842105263158,
      "recovery_miss_accumulated": 0.49016708512368057,
      "stack": "exit repair + hazard",
      "total_system_contribution_vs_baseline": -0.08473583840977861
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.560515801433964,
      "pre_gap_reduction_gained": 0.6315789473684209,
      "recovery_miss_accumulated": 0.5319471170460762,
      "stack": "exit repair + hybrid",
      "total_system_contribution_vs_baseline": -0.03937637067500277
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.560515801433964,
      "pre_gap_reduction_gained": 0.726315789473684,
      "recovery_miss_accumulated": 0.51943436223717,
      "stack": "hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.07916843307207844
    },
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.560515801433964,
      "pre_gap_reduction_gained": 0.726315789473684,
      "recovery_miss_accumulated": 0.5319471170460762,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.08651971855320648
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.13945969186141083,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.0,
      "stack": "baseline stack",
      "total_system_contribution_vs_baseline": 0.0
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10508146690252983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.17630229757250618,
      "stack": "exit repair only",
      "total_system_contribution_vs_baseline": -0.09389551568972052
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.13945969186141083,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.0,
      "stack": "hazard only",
      "total_system_contribution_vs_baseline": 0.0
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10195617372444973,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.19232977917000668,
      "stack": "hybrid redesign only",
      "total_system_contribution_vs_baseline": -0.10243147166151326
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10508146690252983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.17630229757250618,
      "stack": "exit repair + hazard",
      "total_system_contribution_vs_baseline": -0.09389551568972052
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10195617372444973,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.19232977917000668,
      "stack": "exit repair + hybrid",
      "total_system_contribution_vs_baseline": -0.10243147166151326
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10195617372444973,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.19232977917000668,
      "stack": "hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.10243147166151326
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.10195617372444973,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.19232977917000668,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": -0.10243147166151326
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.08723242490361183,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.0,
      "stack": "baseline stack",
      "total_system_contribution_vs_baseline": 0.0
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0675488725468161,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08221610387403988,
      "stack": "exit repair only",
      "total_system_contribution_vs_baseline": 0.07197906182874075
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.07112770024805168,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.007589791573222326,
      "stack": "hazard only",
      "total_system_contribution_vs_baseline": 0.0016730967032898003
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0657594586961983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08969029513531623,
      "stack": "hybrid redesign only",
      "total_system_contribution_vs_baseline": 0.05875827024598479
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0675488725468161,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08221610387403988,
      "stack": "exit repair + hazard",
      "total_system_contribution_vs_baseline": 0.07197906182874075
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0657594586961983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08969029513531623,
      "stack": "exit repair + hybrid",
      "total_system_contribution_vs_baseline": 0.07883526773439475
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0657594586961983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08969029513531623,
      "stack": "hazard + hybrid",
      "total_system_contribution_vs_baseline": 0.05875827024598479
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "false_exit_or_false_reentry_count": 0,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": false,
      "post_gap_damage_suffered": -0.0657594586961983,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.08969029513531623,
      "stack": "full stack: exit repair + hazard + hybrid",
      "total_system_contribution_vs_baseline": 0.07883526773439475
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.25477419330623574,
      "pre_gap_reduction_gained": 0.0,
      "recovery_miss_accumulated": 0.0,
      "stack": "baseline stack",
      "total_system_contribution_vs_baseline": 0.0
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.1146483869878061,
      "pre_gap_reduction_gained": 0.6540540540540544,
      "recovery_miss_accumulated": 0.09620819875774966,
      "stack": "exit repair only",
      "total_system_contribution_vs_baseline": 0.12576172540784425
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.181972763732268,
      "pre_gap_reduction_gained": 0.4621621621621621,
      "recovery_miss_accumulated": 0.07789074994437488,
      "stack": "hazard only",
      "total_system_contribution_vs_baseline": -0.015996317223898382
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": true,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.10190967732249429,
      "pre_gap_reduction_gained": 0.7135135135135133,
      "recovery_miss_accumulated": 0.10495439864481781,
      "stack": "hybrid redesign only",
      "total_system_contribution_vs_baseline": 0.09525345384717665
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry_count": 1,
      "hazard_derisk_undone_too_early": false,
      "hybrid_release_before_resolution": true,
      "post_gap_damage_suffered": -0.1146483869878061,
      "pre_gap_reduction_gained": 0.872972972972973,
      "recovery_miss_accumulated": 0.09620819875774966,
      "stack": "exit repair + hazard",
      "total_system_contribution_vs_baseline": 0.16766652883570698
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "false_exit_or_false_reentry
```
