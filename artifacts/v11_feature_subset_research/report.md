# v11 QQQ Cycle Feature Research

## Protocol

- Selection Window: `2016-01-01` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Selection objective: higher posterior truth probability, higher accuracy, lower entropy, lower Brier
- Candidate families: baseline, leave-one-out, first-principles core plus optional enhancers

## Selection Winner

- Name: `drop_erp_absolute`
- Family: `leave_one_out`
- Features (11): `real_yield_structural_z,move_21d,breakeven_accel,core_capex_momentum,copper_gold_roc_126d,usdjpy_roc_126d,spread_21d,liquidity_252d,spread_absolute,pmi_momentum,labor_slack`
- Selection accuracy / Brier / entropy: `0.4607 / 0.6665 / 0.8100`
- Selection true-regime prob / rank / L1: `0.3501 / 1.7869 / 1.2997`
- Holdout accuracy / Brier / entropy: `0.6738 / 0.4454 / 0.6686`
- Holdout true-regime prob / rank / L1: `0.5180 / 1.4721 / 0.9639`

## Production Recommendation

- Rule: holdout accuracy no worse than baseline, holdout Brier no worse than baseline, holdout entropy no worse than baseline, holdout true-regime probability no worse than baseline; among eligible candidates choose the smallest feature set.
- Name: `drop_pmi_momentum__labor_slack`
- Family: `pair_prune`
- Features (10): `real_yield_structural_z,move_21d,breakeven_accel,core_capex_momentum,copper_gold_roc_126d,usdjpy_roc_126d,spread_21d,liquidity_252d,erp_absolute,spread_absolute`
- Selection composite rank: `22.5556`
- Holdout accuracy / Brier / entropy: `0.6831 / 0.4582 / 0.5892`
- Holdout true-regime prob / rank / L1: `0.5436 / 1.4452 / 0.9128`

## Top 10

| name | family | feature_count | selection_composite_rank | selection_top1_accuracy | selection_mean_brier | selection_mean_entropy | selection_mean_true_regime_probability | holdout_top1_accuracy | holdout_mean_brier | holdout_mean_entropy | holdout_mean_true_regime_probability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| drop_erp_absolute | leave_one_out | 11 | 9 | 0.460653 | 0.666472 | 0.810044 | 0.350134 | 0.673792 | 0.445363 | 0.668599 | 0.518033 |
| drop_real_yield_structural_z | leave_one_out | 11 | 12.888889 | 0.190019 | 0.856244 | 0.750999 | 0.271164 | 0.658457 | 0.456814 | 0.691596 | 0.505464 |
| qqq_core_9__move_21d__copper_gold_roc_126d__usdjpy_roc_126d | core_plus_optional | 9 | 16.555556 | 0.205374 | 0.939695 | 0.686533 | 0.249825 | 0.642193 | 0.47264 | 0.587986 | 0.534943 |
| qqq_core_10__move_21d__copper_gold_roc_126d__usdjpy_roc_126d__labor_slack | core_plus_optional | 10 | 16.555556 | 0.205374 | 0.939695 | 0.686533 | 0.249825 | 0.642193 | 0.47264 | 0.587986 | 0.534943 |
| drop_spread_21d | leave_one_out | 11 | 18.111111 | 0.203455 | 0.941232 | 0.685229 | 0.249596 | 0.643587 | 0.470808 | 0.587899 | 0.535808 |
| qqq_core_10__move_21d__breakeven_accel__copper_gold_roc_126d__usdjpy_roc_126d | core_plus_optional | 10 | 18.111111 | 0.203455 | 0.941232 | 0.685229 | 0.249596 | 0.643587 | 0.470808 | 0.587899 | 0.535808 |
| drop_breakeven_accel | leave_one_out | 11 | 21.111111 | 0.166987 | 0.941001 | 0.708902 | 0.245447 | 0.684015 | 0.459751 | 0.589819 | 0.542709 |
| qqq_core_10__move_21d__copper_gold_roc_126d__usdjpy_roc_126d__spread_21d | core_plus_optional | 10 | 21.111111 | 0.166987 | 0.941001 | 0.708902 | 0.245447 | 0.684015 | 0.459751 | 0.589819 | 0.542709 |
| qqq_core_9__move_21d__breakeven_accel__copper_gold_roc_126d | core_plus_optional | 9 | 21.333333 | 0.207294 | 0.938962 | 0.689584 | 0.248262 | 0.626859 | 0.484254 | 0.594864 | 0.526427 |
| qqq_core_10__move_21d__breakeven_accel__copper_gold_roc_126d__labor_slack | core_plus_optional | 10 | 21.333333 | 0.207294 | 0.938962 | 0.689584 | 0.248262 | 0.626859 | 0.484254 | 0.594864 | 0.526427 |

## Leave-One-Out Lens

Positive `selection_mean_true_regime_probability_delta` or `selection_top1_accuracy_delta` means the system improved after dropping that feature.

| name | selection_top1_accuracy_delta | selection_mean_brier_delta | selection_mean_entropy_delta | selection_mean_true_regime_probability_delta | holdout_top1_accuracy_delta | holdout_mean_brier_delta | holdout_mean_entropy_delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| drop_erp_absolute | 0.295585 | -0.275762 | 0.10226 | 0.104915 | -0.009294 | -0.012826 | 0.079377 |
| drop_real_yield_structural_z | 0.024952 | -0.085989 | 0.043215 | 0.025945 | -0.024628 | -0.001375 | 0.102374 |
| drop_spread_21d | 0.038388 | -0.001002 | -0.022555 | 0.004377 | -0.039498 | 0.012619 | -0.001324 |
| drop_breakeven_accel | 0.001919 | -0.001233 | 0.001118 | 0.000228 | 0.000929 | 0.001561 | 0.000597 |
| drop_pmi_momentum | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drop_labor_slack | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drop_move_21d | 0.005758 | 0.001531 | -0.001534 | -0.000392 | -0.003717 | -0.004348 | 0.006146 |
| drop_usdjpy_roc_126d | 0.001919 | -0.002526 | 0.005915 | -0.00149 | -0.046004 | 0.024241 | 0.006815 |
| drop_spread_absolute | 0.034549 | 0.002049 | 0.011479 | -0.001784 | -0.055762 | 0.037077 | 0.018072 |
| drop_core_capex_momentum | -0.003839 | 0.013684 | -0.00516 | -0.004489 | 0.005112 | 0.000487 | 0.002064 |
| drop_liquidity_252d | 0.001919 | 0.016183 | 0.017718 | -0.015471 | -0.034851 | 0.031515 | 0.028264 |
| drop_copper_gold_roc_126d | -0.024952 | 0.049149 | -0.009317 | -0.019425 | -0.020446 | 0.044543 | 0.017618 |
