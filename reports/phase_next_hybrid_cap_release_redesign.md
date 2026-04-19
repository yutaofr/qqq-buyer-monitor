# Phase Next Hybrid Cap Release Redesign

## Decision
`HYBRID_RELEASE_REDESIGN_HELPS_BUT_REMAINS_SECONDARY`

## Summary
Hybrid is evaluated as a two-speed cap system. Release is not symmetric with cap entry and is judged net of recovery miss.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "best_redesigned_policy": "staged_cap_release",
  "decision": "HYBRID_RELEASE_REDESIGN_HELPS_BUT_REMAINS_SECONDARY",
  "design": {
    "enter_cap_logic": "stress_posterior_or_stress_regime_evidence",
    "leverage_note": "Under 2x leverage, recovery miss is explicitly charged against gap protection benefit.",
    "release_cap_logic": "faster_recovery_sensitive_repair_confirmation"
  },
  "policies_compared": [
    "symmetric_cap_release",
    "faster_recovery_sensitive_cap_release",
    "staged_cap_release"
  ],
  "policy_metrics": [
    {
      "gap_day_loss_reduction": 1.2279119626253208,
      "judged_by_aggregate_gain_only": false,
      "net_contribution_after_recovery_miss": -0.30699571383611823,
      "non_gap_drag": 4.0089346651710756,
      "policy": "symmetric_cap_release",
      "post_gap_recovery_miss_cost": 0.6161131286821757,
      "slice_rows": [
        {
          "cumulative_policy_contribution": 0.13794329254392257,
          "event_name": "2022 H1 structural stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.16560322564905322,
          "net_contribution_after_recovery_miss": 0.02581159436134825,
          "non_gap_drag": 0.9470164427945913,
          "post_gap_recovery_miss_cost": 0.11213169818257432
        },
        {
          "cumulative_policy_contribution": -0.13157618171850188,
          "event_name": "Q4 2018 drawdown",
          "event_slice": "2018-style partially containable drawdowns",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": -0.1715073058680361,
          "non_gap_drag": 0.31491320523320193,
          "post_gap_recovery_miss_cost": 0.039931124149534196
        },
        {
          "cumulative_policy_contribution": -0.03736596471857406,
          "event_name": "COVID fast cascade",
          "event_slice": "2020-like fast cascades",
          "gap_day_loss_reduction": 0.6227672533898518,
          "net_contribution_after_recovery_miss": -0.2089609232341752,
          "non_gap_drag": 0.8735085469850821,
          "post_gap_recovery_miss_cost": 0.17159495851560114
        },
        {
          "cumulative_policy_contribution": -0.0956515666794941,
          "event_name": "August 2015 liquidity vacuum",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.04062881131504118,
          "net_contribution_after_recovery_miss": -0.0956515666794941,
          "non_gap_drag": 0.19304139981369525,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.13612648732247373,
          "event_name": "2022 bear rally relapse",
          "event_slice": "recovery-with-relapse",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.13612648732247373,
          "non_gap_drag": 0.10787555166824384,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.0,
          "event_name": "2023 Q3/Q4 V-shape",
          "event_slice": "rapid V-shape",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.0,
          "non_gap_drag": 0.0,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.37384609525157714,
          "event_name": "2008 financial crisis stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.281905393143035,
          "net_contribution_after_recovery_miss": 0.14985860937002435,
          "non_gap_drag": 1.241026992436809,
          "post_gap_recovery_miss_cost": 0.2239874858815528
        },
        {
          "cumulative_policy_contribution": -0.07420474715534596,
          "event_name": "2011 downgrade liquidity shock",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.1170072791283395,
          "net_contribution_after_recovery_miss": -0.14267260910825919,
          "non_gap_drag": 0.331552526239452,
          "post_gap_recovery_miss_cost": 0.06846786195291324
        }
      ],
      "slower_structural_stress_contribution": 0.5117893877954998,
      "style_2018_contribution": -0.13157618171850188
    },
    {
      "gap_day_loss_reduction": 1.251174342683352,
      "judged_by_aggregate_gain_only": false,
      "net_contribution_after_recovery_miss": -0.20518635991127238,
      "non_gap_drag": 4.045984343455892,
      "policy": "faster_recovery_sensitive_cap_release",
      "post_gap_recovery_miss_cost": 0.6161131286821757,
      "slice_rows": [
        {
          "cumulative_policy_contribution": 0.049106835102405655,
          "event_name": "2022 H1 structural stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.16560322564905322,
          "net_contribution_after_recovery_miss": -0.06302486308016866,
          "non_gap_drag": 1.0738025766962531,
          "post_gap_recovery_miss_cost": 0.11213169818257432
        },
        {
          "cumulative_policy_contribution": 0.08913067677350209,
          "event_name": "Q4 2018 drawdown",
          "event_slice": "2018-style partially containable drawdowns",
          "gap_day_loss_reduction": 0.02326238005803132,
          "net_contribution_after_recovery_miss": 0.04919955262396789,
          "non_gap_drag": 0.30508694141018755,
          "post_gap_recovery_miss_cost": 0.039931124149534196
        },
        {
          "cumulative_policy_contribution": -0.023190441864562095,
          "event_name": "COVID fast cascade",
          "event_slice": "2020-like fast cascades",
          "gap_day_loss_reduction": 0.6227672533898518,
          "net_contribution_after_recovery_miss": -0.19478540038016323,
          "non_gap_drag": 0.7782824942374391,
          "post_gap_recovery_miss_cost": 0.17159495851560114
        },
        {
          "cumulative_policy_contribution": -0.11096742763330611,
          "event_name": "August 2015 liquidity vacuum",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.04062881131504118,
          "net_contribution_after_recovery_miss": -0.11096742763330611,
          "non_gap_drag": 0.20835726076750727,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.13612648732247373,
          "event_name": "2022 bear rally relapse",
          "event_slice": "recovery-with-relapse",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.13612648732247373,
          "non_gap_drag": 0.10787555166824384,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.0,
          "event_name": "2023 Q3/Q4 V-shape",
          "event_slice": "rapid V-shape",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.0,
          "non_gap_drag": 0.0,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.37384609525157714,
          "event_name": "2008 financial crisis stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.281905393143035,
          "net_contribution_after_recovery_miss": 0.14985860937002435,
          "non_gap_drag": 1.241026992436809,
          "post_gap_recovery_miss_cost": 0.2239874858815528
        },
        {
          "cumulative_policy_contribution": -0.10312545618118711,
          "event_name": "2011 downgrade liquidity shock",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.1170072791283395,
          "net_contribution_after_recovery_miss": -0.17159331813410034,
          "non_gap_drag": 0.331552526239452,
          "post_gap_recovery_miss_cost": 0.06846786195291324
        }
      ],
      "slower_structural_stress_contribution": 0.4229529303539828,
      "style_2018_contribution": 0.08913067677350209
    },
    {
      "gap_day_loss_reduction": 1.251174342683352,
      "judged_by_aggregate_gain_only": false,
      "net_contribution_after_recovery_miss": -0.20024862284820033,
      "non_gap_drag": 4.11990656202002,
      "policy": "staged_cap_release",
      "post_gap_recovery_miss_cost": 0.6244244693775357,
      "slice_rows": [
        {
          "cumulative_policy_contribution": 0.09903090270120785,
          "event_name": "2022 H1 structural stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.16560322564905322,
          "net_contribution_after_recovery_miss": -0.013100795481366473,
          "non_gap_drag": 1.0870151476746743,
          "post_gap_recovery_miss_cost": 0.11213169818257432
        },
        {
          "cumulative_policy_contribution": 0.06561447615163868,
          "event_name": "Q4 2018 drawdown",
          "event_slice": "2018-style partially containable drawdowns",
          "gap_day_loss_reduction": 0.02326238005803132,
          "net_contribution_after_recovery_miss": 0.025683352002104483,
          "non_gap_drag": 0.33072198956878807,
          "post_gap_recovery_miss_cost": 0.039931124149534196
        },
        {
          "cumulative_policy_contribution": -0.03380896533730254,
          "event_name": "COVID fast cascade",
          "event_slice": "2020-like fast cascades",
          "gap_day_loss_reduction": 0.6227672533898518,
          "net_contribution_after_recovery_miss": -0.20540392385290368,
          "non_gap_drag": 0.7963564734058592,
          "post_gap_recovery_miss_cost": 0.17159495851560114
        },
        {
          "cumulative_policy_contribution": -0.11096742763330611,
          "event_name": "August 2015 liquidity vacuum",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.04062881131504118,
          "net_contribution_after_recovery_miss": -0.11096742763330611,
          "non_gap_drag": 0.20835726076750727,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.13612648732247373,
          "event_name": "2022 bear rally relapse",
          "event_slice": "recovery-with-relapse",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.13612648732247373,
          "non_gap_drag": 0.10787555166824384,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.0,
          "event_name": "2023 Q3/Q4 V-shape",
          "event_slice": "rapid V-shape",
          "gap_day_loss_reduction": 0.0,
          "net_contribution_after_recovery_miss": 0.0,
          "non_gap_drag": 0.0,
          "post_gap_recovery_miss_cost": 0.0
        },
        {
          "cumulative_policy_contribution": 0.37384609525157714,
          "event_name": "2008 financial crisis stress",
          "event_slice": "slower structural stress",
          "gap_day_loss_reduction": 0.281905393143035,
          "net_contribution_after_recovery_miss": 0.14985860937002435,
          "non_gap_drag": 1.241026992436809,
          "post_gap_recovery_miss_cost": 0.2239874858815528
        },
        {
          "cumulative_policy_contribution": -0.10566572192695335,
          "event_name": "2011 downgrade liquidity shock",
          "event_slice": "2015-style liquidity vacuum",
          "gap_day_loss_reduction": 0.1170072791283395,
          "net_contribution_after_recovery_miss": -0.18244492457522662,
          "non_gap_drag": 0.3485531464981388,
          "post_gap_recovery_miss_cost": 0.07677920264827327
        }
      ],
      "slower_structural_stress_contribution": 0.472876997952785,
      "style_2018_contribution": 0.06561447615163868
    }
  ],
  "repair_dependency": "REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING",
  "summary": "Hybrid is evaluated as a two-speed cap system. Release is not symmetric with cap entry a
```
