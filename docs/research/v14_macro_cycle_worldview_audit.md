# v14 Macro Cycle Worldview Audit

## Summary

- Audit Window: `2011-01-03` to `2026-03-27`
- Rows: `3831`
- Stable Regime vs Worldview Benchmark: `72.36%`
- Target Beta vs Worldview Benchmark MAE: `0.1076`
- Left-Tail Event Coverage: `72.19%`
- Transition-Window Regime Match: `58.75%`

## Probability Alignment

| regime | probability_mae | probability_correlation | delta_sign_alignment | model_mean_probability | benchmark_mean_probability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MID_CYCLE | 0.2224 | 0.6535 | 0.5748 | 0.3494 | 0.2171 |
| LATE_CYCLE | 0.1828 | 0.694 | 0.64 | 0.3324 | 0.376 |
| BUST | 0.1017 | 0.8988 | 0.6356 | 0.1903 | 0.1989 |
| RECOVERY | 0.1347 | 0.6052 | 0.597 | 0.1279 | 0.208 |

## Beta Alignment By Worldview Regime

| benchmark_regime | rows | mean_target_beta | mean_benchmark_beta | beta_mae |
| :--- | :--- | :--- | :--- | :--- |
| BUST | 629 | 0.6221 | 0.6972 | 0.0987 |
| LATE_CYCLE | 1657 | 0.7279 | 0.8156 | 0.1096 |
| MID_CYCLE | 1230 | 0.835 | 0.895 | 0.1045 |
| RECOVERY | 315 | 0.7688 | 0.8663 | 0.127 |

## Crisis Windows

| window | rows | stable_vs_benchmark_regime | beta_mae | tractor_prob_mean | sidecar_prob_mean | left_tail_cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018Q4 | 63 | 0.8254 | 0.0842 | 0.1884 | 0.1317 | 0.0556 |
| 2020COVID | 52 | 0.8077 | 0.0987 | 0.8375 | 0.6822 | 1.0 |
| 2022H1 | 124 | 0.9355 | 0.0709 | 0.1152 | 0.282 | 0.7632 |

## Left-Tail Audit

- Event Rows: `187`
- Tractor Hit Share: `32.09%`
- Sidecar Hit Share: `72.19%`
- Combined Coverage: `72.19%`

## Interpretation

- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.
- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.