# v14 Macro Cycle Worldview Audit

## Summary

- Audit Window: `2011-01-03` to `2026-03-26`
- Rows: `3830`
- Stable Regime vs Worldview Benchmark: `37.44%`
- Target Beta vs Worldview Benchmark MAE: `0.1060`
- Left-Tail Event Coverage: `72.19%`
- Transition-Window Regime Match: `42.49%`

## Probability Alignment

| regime | probability_mae | probability_correlation | delta_sign_alignment | model_mean_probability | benchmark_mean_probability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MID_CYCLE | 0.4773 | 0.2409 | 0.5084 | 0.6775 | 0.2251 |
| LATE_CYCLE | 0.2689 | 0.0886 | 0.5042 | 0.128 | 0.3701 |
| BUST | 0.1511 | 0.3288 | 0.5389 | 0.1249 | 0.1969 |
| RECOVERY | 0.1625 | 0.1252 | 0.518 | 0.0696 | 0.2079 |

## Beta Alignment By Worldview Regime

| benchmark_regime | rows | mean_target_beta | mean_benchmark_beta | beta_mae |
| :--- | :--- | :--- | :--- | :--- |
| BUST | 608 | 0.7628 | 0.694 | 0.1246 |
| LATE_CYCLE | 1563 | 0.7651 | 0.8143 | 0.0973 |
| MID_CYCLE | 1344 | 0.8113 | 0.8966 | 0.101 |
| RECOVERY | 315 | 0.7494 | 0.8671 | 0.1347 |

## Crisis Windows

| window | rows | stable_vs_benchmark_regime | beta_mae | tractor_prob_mean | sidecar_prob_mean | left_tail_cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018Q4 | 63 | 0.3492 | 0.1354 | 0.1884 | 0.1317 | 0.0556 |
| 2020COVID | 52 | 0.2885 | 0.1626 | 0.8375 | 0.6822 | 1.0 |
| 2022H1 | 124 | 0.1048 | 0.121 | 0.1152 | 0.282 | 0.7632 |

## Left-Tail Audit

- Event Rows: `187`
- Tractor Hit Share: `32.09%`
- Sidecar Hit Share: `72.19%`
- Combined Coverage: `72.19%`

## Interpretation

- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.
- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.