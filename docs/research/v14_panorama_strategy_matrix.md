# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `CACHED_ARTIFACT`
- Calibration Window: `2011-01-03` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: process gate first, then no worse max drawdown, no worse left-tail beta, bounded turnover drift

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.921663747564598 | -0.2285351893583023 | 0.7206516443977371 | 0.030953286095846466 | 0.6831532696789261 | 0.8749034749034749 | 0.20412252423915553 | 0.23433512099745726 | 0.07094594594594594 | 0.8632335904180902 | 0.12858303323000603 | 0.38706563706563707 | 0.7206516443977371 | 0.20412252423915553 | 0.07094594594594594 | 0.8120936705950402 | 0.5616554054054054 | 0.8778957528957528 | 0.9438947876447876 | 0.8628668171557562 | 0.4473938223938224 | 0.14330674426014192 | 0.7020316027088036 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2526094915425698 | -0.24097675169578447 | 0.6547905959889 | 0.034914803777440925 | 0.594100011006806 | 0.8749034749034749 | 0.25120661256477994 | 0.3054589451477585 | 0.11341698841698841 | 0.8632335904180902 | 0.12858303323000603 | 0.38706563706563707 | 0.7206516443977371 | 0.20412252423915553 | 0.07094594594594594 | 0.8120936705950402 | 0.5616554054054054 | 0.8778957528957528 | 0.9438947876447876 | 0.8628668171557562 | 0.4473938223938224 | 0.14330674426014192 | 0.7020316027088036 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.384455989236109 | -0.2285351893583023 | 0.675544181399936 | 0.03357655686797704 | 0.6113830921332591 | 0.8749034749034749 | 0.23510419496638454 | 0.2879431030586263 | 0.10183397683397684 | 0.8632335904180902 | 0.12858303323000603 | 0.38706563706563707 | 0.7206516443977371 | 0.20412252423915553 | 0.07094594594594594 | 0.8120936705950402 | 0.5616554054054054 | 0.8778957528957528 | 0.9438947876447876 | 0.8628668171557562 | 0.4473938223938224 | 0.14330674426014192 | 0.7020316027088036 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3775587491283154 | -0.32660970748378626 | 0.7545925687464448 | 0.04866049905703848 | 0.6387134612244925 | 0.8749034749034749 | 0.2827506102672082 | 0.33756630144916305 | 0.10183397683397684 | 0.8632335904180902 | 0.12858303323000603 | 0.38706563706563707 | 0.7206516443977371 | 0.20412252423915553 | 0.07094594594594594 | 0.8120936705950402 | 0.5616554054054054 | 0.8778957528957528 | 0.9438947876447876 | 0.8628668171557562 | 0.4473938223938224 | 0.14330674426014192 | 0.7020316027088036 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-03` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `51.24%`
- Posterior Brier: `0.7287`
- Mean Entropy: `0.5519`
- Stable vs Benchmark Regime: `80.54%`
- Probability Within Band: `56.25%`
- Delta Within Band: `84.18%`
- Acceleration Within Band: `84.74%`
- Transition Probability Within Band: `87.81%`
- Entropy Within Band: `42.78%`
- Raw Beta vs Expectation MAE: `0.1424`
- Target Beta vs Expectation MAE: `0.2248`
- Deployment Exact Match: `51.51%`
- Deployment Rank Error: `0.6395`
- Deployment Pacing Abs Error: `0.4005`
- Deployment Pacing Signed Bias: `-0.0944`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `34.57%`
- Target Beta Within 5pct Of Expected: `5.95%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8632335904180902 | 0.7206516443977371 | 0.7206516443977371 | 0.8749034749034749 | 0.12858303323000603 | 0.20412252423915553 | 0.20412252423915553 |
| s4_sidecar | 0.8632335904180902 | 0.7206516443977371 | 0.6547905959889 | 0.8749034749034749 | 0.12858303323000603 | 0.20412252423915553 | 0.25120661256477994 |
| s5_tractor | 0.8632335904180902 | 0.7206516443977371 | 0.675544181399936 | 0.8749034749034749 | 0.12858303323000603 | 0.20412252423915553 | 0.23510419496638454 |
| s4s5_panorama | 0.8632335904180902 | 0.7206516443977371 | 0.7545925687464448 | 0.8749034749034749 | 0.12858303323000603 | 0.20412252423915553 | 0.2827506102672082 |

## Calibration Winner

- No scenario cleared the acceptance contract in calibration.
- Report is fail-closed; `standard` is shown below only as the baseline reference.

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.921663747564598 | -0.2285351893583023 | 0.7206516443977371 | 0.030953286095846466 | 0.6831532696789261 | 0.8749034749034749 | 0.20412252423915553 | 0.23433512099745726 | 0.07094594594594594 | 0.8632335904180902 | 0.12858303323000603 | 0.38706563706563707 | 0.7206516443977371 | 0.20412252423915553 | 0.07094594594594594 | 0.8120936705950402 | 0.5616554054054054 | 0.8778957528957528 | 0.9438947876447876 | 0.8628668171557562 | 0.4473938223938224 | 0.14330674426014192 | 0.7020316027088036 | False | Worldview Process Failure (entropy_within_band_share) | 0.2 | 0.15 | 0.05 | True |

## Production Recommendation

- Fail closed: no scenario, including `standard`, cleared the regime-process acceptance gate.
- Keep all panorama variants in diagnostic mode until the mainline process metrics themselves are repaired.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5026`, mean `0.7207`, below-floor share `0.00%`).
