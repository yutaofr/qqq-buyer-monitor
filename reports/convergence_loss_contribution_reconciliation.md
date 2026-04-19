# Convergence Loss Contribution Reconciliation

## Summary
Budget ranking reconciles raw loss with integrated-stack benefit.

## Decision
`SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "decision": "SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET",
  "event_class_rows": [
    {
      "cumulative_loss_contribution": 0.8067543893263802,
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "improvable_loss_contribution": 0.33993516905129556,
      "integrated_stack_benefit": -0.08651971855320648,
      "residual_unrepaired_loss": 0.8067543893263802,
      "tail_loss_contribution": 0.7241958076991433
    },
    {
      "cumulative_loss_contribution": 0.20024995817523472,
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "improvable_loss_contribution": 0.09411559740405082,
      "integrated_stack_benefit": -0.10243147166151326,
      "residual_unrepaired_loss": 0.20024995817523472,
      "tail_loss_contribution": 0.14112968913182544
    },
    {
      "cumulative_loss_contribution": 0.5831704431023952,
      "event_class": "2018-style partially containable drawdown",
      "improvable_loss_contribution": 0.4031771669330796,
      "integrated_stack_benefit": 0.07883526773439475,
      "residual_unrepaired_loss": 0.5043351753680004,
      "tail_loss_contribution": 0.43989465993717947
    },
    {
      "cumulative_loss_contribution": 2.661026819678842,
      "event_class": "slower structural stress",
      "improvable_loss_contribution": 1.7295058966509467,
      "integrated_stack_benefit": 0.5165326809988862,
      "residual_unrepaired_loss": 2.1444941386799554,
      "tail_loss_contribution": 2.168688433382016
    },
    {
      "cumulative_loss_contribution": 0.43213939632525744,
      "event_class": "recovery-with-relapse",
      "improvable_loss_contribution": 0.2525061755285419,
      "integrated_stack_benefit": 0.12565521906689892,
      "residual_unrepaired_loss": 0.3064841772583585,
      "tail_loss_contribution": 0.23863733081812166
    },
    {
      "cumulative_loss_contribution": 0.3392817486781218,
      "event_class": "rapid V-shape ordinary correction",
      "improvable_loss_contribution": 0.22398866746557944,
      "integrated_stack_benefit": 0.0,
      "residual_unrepaired_loss": 0.3392817486781218,
      "tail_loss_contribution": 0.10518753556670046
    }
  ],
  "event_rows": [
    {
      "cumulative_loss_contribution": 0.8067543893263802,
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "improvable_loss_contribution": 0.33993516905129556,
      "integrated_stack_benefit": -0.08651971855320648,
      "residual_unrepaired_loss": 0.8067543893263802,
      "tail_loss_contribution": 0.7241958076991433
    },
    {
      "cumulative_loss_contribution": 0.20024995817523472,
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "improvable_loss_contribution": 0.09411559740405082,
      "integrated_stack_benefit": -0.10243147166151326,
      "residual_unrepaired_loss": 0.20024995817523472,
      "tail_loss_contribution": 0.14112968913182544
    },
    {
      "cumulative_loss_contribution": 0.5831704431023952,
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "improvable_loss_contribution": 0.4031771669330796,
      "integrated_stack_benefit": 0.07883526773439475,
      "residual_unrepaired_loss": 0.5043351753680004,
      "tail_loss_contribution": 0.43989465993717947
    },
    {
      "cumulative_loss_contribution": 1.2734256505236257,
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "improvable_loss_contribution": 0.8143944375890436,
      "integrated_stack_benefit": 0.17144397768973801,
      "residual_unrepaired_loss": 1.1019816728338876,
      "tail_loss_contribution": 0.9735686994271071
    },
    {
      "cumulative_loss_contribution": 1.387601169155216,
      "event_class": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "improvable_loss_contribution": 0.915111459061903,
      "integrated_stack_benefit": 0.3450887033091482,
      "residual_unrepaired_loss": 1.0425124658460678,
      "tail_loss_contribution": 1.1951197339549087
    },
    {
      "cumulative_loss_contribution": 0.43213939632525744,
      "event_class": "recovery-with-relapse",
      "event_name": "2022 bear rally relapse",
      "improvable_loss_contribution": 0.2525061755285419,
      "integrated_stack_benefit": 0.12565521906689892,
      "residual_unrepaired_loss": 0.3064841772583585,
      "tail_loss_contribution": 0.23863733081812166
    },
    {
      "cumulative_loss_contribution": 0.3392817486781218,
      "event_class": "rapid V-shape ordinary correction",
      "event_name": "2023 Q3/Q4 V-shape",
      "improvable_loss_contribution": 0.22398866746557944,
      "integrated_stack_benefit": 0.0,
      "residual_unrepaired_loss": 0.3392817486781218,
      "tail_loss_contribution": 0.10518753556670046
    }
  ],
  "next_unit_research_budget_highest_expected_value": "slower structural stress",
  "summary": "Budget ranking reconciles raw loss with integrated-stack benefit."
}
```
