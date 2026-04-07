# v14 Macro Cycle Worldview Audit

## Summary

- Audit Window: `2011-01-03` to `2026-03-27`
- Rows: `3831`
- Stable Regime vs Worldview Benchmark: `69.30%`
- Target Beta vs Worldview Benchmark MAE: `0.1244`
- Left-Tail Event Coverage: `52.41%`
- Transition-Window Regime Match: `51.63%`

## Probability Alignment

| regime | probability_mae | probability_correlation | delta_sign_alignment | model_mean_probability | benchmark_mean_probability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MID_CYCLE | 0.2351 | 0.6536 | 0.5944 | 0.3673 | 0.2251 |
| LATE_CYCLE | 0.204 | 0.6645 | 0.65 | 0.3673 | 0.3701 |
| BUST | 0.1063 | 0.9028 | 0.6434 | 0.1868 | 0.1969 |
| RECOVERY | 0.163 | 0.2766 | 0.5904 | 0.0786 | 0.2078 |

## Beta Alignment By Worldview Regime

| benchmark_regime | rows | mean_target_beta | mean_benchmark_beta | beta_mae |
| :--- | :--- | :--- | :--- | :--- |
| BUST | 609 | 0.6025 | 0.6941 | 0.1024 |
| LATE_CYCLE | 1563 | 0.694 | 0.8143 | 0.1266 |
| MID_CYCLE | 1344 | 0.7926 | 0.8966 | 0.1218 |
| RECOVERY | 315 | 0.7119 | 0.8671 | 0.1672 |

## Crisis Windows

| window | rows | stable_vs_benchmark_regime | beta_mae | tractor_prob_mean | sidecar_prob_mean | left_tail_cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018Q4 | 63 | 0.7937 | 0.106 | 0.2219 | 0.0952 | 0.3333 |
| 2020COVID | 52 | 0.7308 | 0.1405 | 0.7486 | 0.6936 | 1.0 |
| 2022H1 | 124 | 0.9355 | 0.0814 | 0.1232 | 0.1159 | 0.0 |

## Left-Tail Audit

- Event Rows: `187`
- Tractor Hit Share: `41.71%`
- Sidecar Hit Share: `48.66%`
- Combined Coverage: `52.41%`

## Interpretation

- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.
- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.