# State Machine Actual Leverage Recalculation

## Summary
Actual-executed recalculation uses shifted next-session leverage as the primary accounting basis.

## Machine-Readable Snapshot
```json
{
  "comparison_rows": [
    {
      "absolute_delta": 0.044457,
      "claim": "full-stack contribution",
      "event_name": "COVID fast cascade",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": -0.042063,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": -0.08652,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.063158,
      "claim": "pre-gap exposure reduction",
      "event_name": "COVID fast cascade",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.789474,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.726316,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.045066,
      "claim": "post-gap damage",
      "event_name": "COVID fast cascade",
      "metric": "post_gap_damage",
      "previous_value": -0.515449,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": -0.560516,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.014872,
      "claim": "recovery miss",
      "event_name": "COVID fast cascade",
      "metric": "recovery_miss",
      "previous_value": 0.517075,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.531947,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.004509,
      "claim": "full-stack contribution",
      "event_name": "August 2015 liquidity vacuum",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": -0.097922,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": -0.102431,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "pre-gap exposure reduction",
      "event_name": "August 2015 liquidity vacuum",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "post-gap damage",
      "event_name": "August 2015 liquidity vacuum",
      "metric": "post_gap_damage",
      "previous_value": -0.101956,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": -0.101956,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "recovery miss",
      "event_name": "August 2015 liquidity vacuum",
      "metric": "recovery_miss",
      "previous_value": 0.19233,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.19233,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.030873,
      "claim": "full-stack contribution",
      "event_name": "Q4 2018 drawdown",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": 0.109708,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.078835,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.066667,
      "claim": "pre-gap exposure reduction",
      "event_name": "Q4 2018 drawdown",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.066667,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.030866,
      "claim": "post-gap damage",
      "event_name": "Q4 2018 drawdown",
      "metric": "post_gap_damage",
      "previous_value": -0.034893,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": -0.065759,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "recovery miss",
      "event_name": "Q4 2018 drawdown",
      "metric": "recovery_miss",
      "previous_value": 0.08969,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.08969,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.085142,
      "claim": "full-stack contribution",
      "event_name": "2022 H1 structural stress",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": 0.256586,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.171444,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.032432,
      "claim": "pre-gap exposure reduction",
      "event_name": "2022 H1 structural stress",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.964865,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.932432,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "post-gap damage",
      "event_name": "2022 H1 structural stress",
      "metric": "post_gap_damage",
      "previous_value": -0.10191,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": -0.10191,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "recovery miss",
      "event_name": "2022 H1 structural stress",
      "metric": "recovery_miss",
      "previous_value": 0.104954,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.104954,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.03815,
      "claim": "full-stack contribution",
      "event_name": "2008 financial crisis stress",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": 0.383238,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.345089,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.030769,
      "claim": "pre-gap exposure reduction",
      "event_name": "2008 financial crisis stress",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.923077,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": 0.892308,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.037302,
      "claim": "post-gap damage",
      "event_name": "2008 financial crisis stress",
      "metric": "post_gap_damage",
      "previous_value": -0.198348,
      "prior_interpretation_survives": false,
      "recalculated_actual_executed_leverage_value": -0.23565,
      "sign_change": false,
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.000848,
      "claim": "recovery miss",
      "event_name": "2008 financial crisis stress",
      "metric": "recovery_miss",
      "previous_value": 0.475264,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.476112,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.019984,
      "claim": "full-stack contribution",
      "event_name": "2022 bear rally relapse",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": 0.145639,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.125655,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "pre-gap exposure reduction",
      "event_name": "2022 bear rally relapse",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "post-gap damage",
      "event_name": "2022 bear rally relapse",
      "metric": "post_gap_damage",
      "previous_value": -0.109673,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": -0.109673,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "recovery miss",
      "event_name": "2022 bear rally relapse",
      "metric": "recovery_miss",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "full-stack contribution",
      "event_name": "2023 Q3/Q4 V-shape",
      "metric": "full_stack_contribution_vs_baseline",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "pre-gap exposure reduction",
      "event_name": "2023 Q3/Q4 V-shape",
      "metric": "pre_gap_exposure_reduction",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "post-gap damage",
      "event_name": "2023 Q3/Q4 V-shape",
      "metric": "post_gap_damage",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "absolute_delta": 0.0,
      "claim": "recovery miss",
      "event_name": "2023 Q3/Q4 V-shape",
      "metric": "recovery_miss",
      "previous_value": 0.0,
      "prior_interpretation_survives": true,
      "recalculated_actual_executed_leverage_value": 0.0,
      "sign_change": false,
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    }
  ],
  "load_bearing_recalculation_basis": "ACTUAL_EXECUTED_ONLY",
  "published_claim_survival": [
    {
      "claim": "2020-like full-stack repair is not solved by current stack",
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    },
    {
      "claim": "structural-stress exit plus hazard remains the bounded budget line",
      "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "claim": "old convergence-positive checklist reading",
      "survival_label": "FAILS_UNDER_ACTUAL_ACCOUNTING"
    },
    {
      "claim": "budget priority is not maturity or freezeability",
      "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
    }
  ],
  "required_windows_covered": true,
  "summary": "Actual-executed recalculation uses shifted next-session leverage as the primary accounting basis."
}
```
