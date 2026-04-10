# v14 Macro Cycle Worldview Audit

## Summary

- Audit Window: `2013-01-30` to `2026-03-31`
- Rows: `3312`
- Stable Regime vs Worldview Benchmark: `59.54%`
- Target Beta vs Worldview Benchmark MAE: `0.1465`
- Left-Tail Event Coverage: `66.27%`
- Transition-Window Regime Match: `43.16%`

## Probability Alignment

| regime | probability_mae | probability_correlation | delta_sign_alignment | model_mean_probability | benchmark_mean_probability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MID_CYCLE | 0.2251 | 0.5768 | 0.5704 | 0.3803 | 0.2332 |
| LATE_CYCLE | 0.1917 | 0.5784 | 0.6208 | 0.3308 | 0.3803 |
| BUST | 0.0802 | 0.924 | 0.6543 | 0.1672 | 0.1846 |
| RECOVERY | 0.102 | 0.7949 | 0.6193 | 0.1218 | 0.2019 |

## Beta Alignment By Worldview Regime

| benchmark_regime | rows | mean_target_beta | mean_benchmark_beta | beta_mae |
| :--- | :--- | :--- | :--- | :--- |
| BUST | 456 | 0.601 | 0.7017 | 0.1007 |
| LATE_CYCLE | 1435 | 0.706 | 0.8441 | 0.1448 |
| MID_CYCLE | 1183 | 0.766 | 0.905 | 0.1507 |
| RECOVERY | 238 | 0.6974 | 0.9218 | 0.2244 |

## Crisis Windows

| window | rows | stable_vs_benchmark_regime | beta_mae | tractor_prob_mean | sidecar_prob_mean | left_tail_cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018Q4 | 63 | 0.5397 | 0.122 | 0.2324 | 0.1065 | 0.3889 |
| 2020COVID | 52 | 0.6538 | 0.1549 | 0.8 | 0.6846 | 0.9583 |
| 2022H1 | 124 | 0.7258 | 0.0832 | 0.1205 | 0.2113 | 0.6842 |

## Left-Tail Audit

- Event Rows: `166`
- Tractor Hit Share: `38.55%`
- Sidecar Hit Share: `62.05%`
- Combined Coverage: `66.27%`

## Interpretation

- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.
- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.