# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `ALFRED+PIT_FALLBACK`
- Calibration Window: `2011-01-01` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: process gate first, then no worse max drawdown, no worse left-tail beta, bounded turnover drift

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9849961685228 | -0.25455538793809096 | 0.7876637672855258 | 0.026956297528468193 | 0.730860137545232 | 0.8749034749034749 | 0.15311095697213964 | 0.19051968348055734 | 0.21621621621621623 | 0.8708715247917878 | 0.1216532007288263 | 0.46187258687258687 | 0.7876637672855258 | 0.15311095697213964 | 0.21621621621621623 | 0.6722972972972973 | 0.4576496138996139 | 0.7087355212355212 | 0.5430743243243243 | 0.6411992263056093 | 0.07625482625482626 | 0.48571812436713274 | 0.15473887814313347 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2817969516928325 | -0.2680056618685801 | 0.7035142779992392 | 0.034373634273940495 | 0.6202098796888963 | 0.8749034749034749 | 0.21505190606044985 | 0.28425688262074045 | 0.22876447876447875 | 0.8708715247917878 | 0.1216532007288263 | 0.46187258687258687 | 0.7876637672855258 | 0.15311095697213964 | 0.21621621621621623 | 0.6722972972972973 | 0.4576496138996139 | 0.7087355212355212 | 0.5430743243243243 | 0.6411992263056093 | 0.07625482625482626 | 0.48571812436713274 | 0.15473887814313347 | False | Worldview Process Failure (probability_within_band_share) | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.412353700313275 | -0.25455538793809207 | 0.7266049901113435 | 0.03201797635769184 | 0.6396206963681496 | 0.8749034749034749 | 0.197142960194249 | 0.26429892666259547 | 0.2195945945945946 | 0.8708715247917878 | 0.1216532007288263 | 0.46187258687258687 | 0.7876637672855258 | 0.15311095697213964 | 0.21621621621621623 | 0.6722972972972973 | 0.4576496138996139 | 0.7087355212355212 | 0.5430743243243243 | 0.6411992263056093 | 0.07625482625482626 | 0.48571812436713274 | 0.15473887814313347 | False | Worldview Process Failure (probability_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3356562303474036 | -0.33609714522333634 | 0.7827180351128715 | 0.04756628846937209 | 0.6556197042174167 | 0.8749034749034749 | 0.26492752180619233 | 0.32869019456185156 | 0.1583011583011583 | 0.8708715247917878 | 0.1216532007288263 | 0.46187258687258687 | 0.7876637672855258 | 0.15311095697213964 | 0.21621621621621623 | 0.6722972972972973 | 0.4576496138996139 | 0.7087355212355212 | 0.5430743243243243 | 0.6411992263056093 | 0.07625482625482626 | 0.48571812436713274 | 0.15473887814313347 | False | Worldview Process Failure (probability_within_band_share) | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `52.26%`
- Posterior Brier: `0.7135`
- Mean Entropy: `0.3137`
- Stable vs Benchmark Regime: `66.15%`
- Probability Within Band: `45.27%`
- Delta Within Band: `72.83%`
- Acceleration Within Band: `56.70%`
- Transition Probability Within Band: `61.89%`
- Entropy Within Band: `8.06%`
- Raw Beta vs Expectation MAE: `0.1340`
- Target Beta vs Expectation MAE: `0.1760`
- Deployment Exact Match: `53.41%`
- Deployment Rank Error: `0.6253`
- Deployment Pacing Abs Error: `0.3918`
- Deployment Pacing Signed Bias: `-0.0865`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `44.26%`
- Target Beta Within 5pct Of Expected: `19.93%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8708715247917878 | 0.7876637672855258 | 0.7876637672855258 | 0.8749034749034749 | 0.1216532007288263 | 0.15311095697213964 | 0.15311095697213964 |
| s4_sidecar | 0.8708715247917878 | 0.7876637672855258 | 0.7035142779992392 | 0.8749034749034749 | 0.1216532007288263 | 0.15311095697213964 | 0.21505190606044985 |
| s5_tractor | 0.8708715247917878 | 0.7876637672855258 | 0.7266049901113435 | 0.8749034749034749 | 0.1216532007288263 | 0.15311095697213964 | 0.197142960194249 |
| s4s5_panorama | 0.8708715247917878 | 0.7876637672855258 | 0.7827180351128715 | 0.8749034749034749 | 0.1216532007288263 | 0.15311095697213964 | 0.26492752180619233 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.0912`
- Calibration Max Drawdown: `-0.1106`
- Calibration Left-Tail Beta: `0.7761`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9849961685228 | -0.25455538793809096 | 0.7876637672855258 | 0.026956297528468193 | 0.730860137545232 | 0.8749034749034749 | 0.15311095697213964 | 0.19051968348055734 | 0.21621621621621623 | 0.8708715247917878 | 0.1216532007288263 | 0.46187258687258687 | 0.7876637672855258 | 0.15311095697213964 | 0.21621621621621623 | 0.6722972972972973 | 0.4576496138996139 | 0.7087355212355212 | 0.5430743243243243 | 0.6411992263056093 | 0.07625482625482626 | 0.48571812436713274 | 0.15473887814313347 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5049`, mean `0.7877`, below-floor share `0.00%`).
