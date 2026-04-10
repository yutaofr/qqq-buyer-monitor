# v14 Macro Cycle Worldview Audit

## Summary

- Audit Window: `2013-01-30` to `2026-03-31`
- Rows: `3312`
- Stable Regime vs Worldview Benchmark: `62.86%`
- Target Beta vs Worldview Benchmark MAE: `0.1469`
- Left-Tail Event Coverage: `66.27%`
- Transition-Window Regime Match: `48.35%`

## Probability Alignment

| regime | probability_mae | probability_correlation | delta_sign_alignment | model_mean_probability | benchmark_mean_probability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MID_CYCLE | 0.2285 | 0.5736 | 0.5725 | 0.3839 | 0.2332 |
| LATE_CYCLE | 0.1928 | 0.578 | 0.6211 | 0.334 | 0.3803 |
| BUST | 0.0813 | 0.9242 | 0.654 | 0.1693 | 0.1846 |
| RECOVERY | 0.1052 | 0.7755 | 0.6184 | 0.1128 | 0.2019 |

## Beta Alignment By Worldview Regime

| benchmark_regime | rows | mean_target_beta | mean_benchmark_beta | beta_mae |
| :--- | :--- | :--- | :--- | :--- |
| BUST | 456 | 0.5996 | 0.7017 | 0.1022 |
| LATE_CYCLE | 1435 | 0.7063 | 0.8441 | 0.1446 |
| MID_CYCLE | 1183 | 0.7666 | 0.905 | 0.1502 |
| RECOVERY | 238 | 0.692 | 0.9218 | 0.2298 |

## Crisis Windows

| window | rows | stable_vs_benchmark_regime | beta_mae | tractor_prob_mean | sidecar_prob_mean | left_tail_cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018Q4 | 63 | 0.5397 | 0.122 | 0.2324 | 0.1065 | 0.3889 |
| 2020COVID | 52 | 0.6731 | 0.1555 | 0.8 | 0.6846 | 0.9583 |
| 2022H1 | 124 | 0.7097 | 0.0835 | 0.1205 | 0.2113 | 0.6842 |

## Left-Tail Audit

- Event Rows: `166`
- Tractor Hit Share: `38.55%`
- Sidecar Hit Share: `62.05%`
- Combined Coverage: `66.27%`

## Interpretation

- This worldview benchmark is PIT-safe and evaluation-only: it uses trailing QQQ price/volume structure, not forward labels.
- The left-tail event definition is ex-post for audit only (`1d return <= -3%` or `forward 20d drawdown <= -12%`) and is not fed back into the runtime.