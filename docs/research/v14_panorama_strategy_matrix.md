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
| standard | 2072.0 | 1.9384226070941115 | -0.2285351893583023 | 0.7242016932454085 | 0.029116665229612627 | 0.6838737672487044 | 0.8749034749034749 | 0.20057247539148418 | 0.23098413174939594 | 0.07577220077220077 | 0.8636935792160966 | 0.1283077724766775 | 0.38996138996138996 | 0.7242016932454085 | 0.20057247539148418 | 0.07577220077220077 | 0.8050060164965225 | 0.5565878378378378 | 0.8766891891891893 | 0.9438947876447876 | 0.8515801354401806 | 0.45125482625482627 | 0.14174290071101167 | 0.7223476297968398 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2846334833659254 | -0.24097675169578447 | 0.6576789822534226 | 0.03366261398905802 | 0.5947967088966101 | 0.8749034749034749 | 0.24831822630025743 | 0.3032783780554428 | 0.11824324324324324 | 0.8636935792160966 | 0.1283077724766775 | 0.38996138996138996 | 0.7242016932454085 | 0.20057247539148418 | 0.07577220077220077 | 0.8050060164965225 | 0.5565878378378378 | 0.8766891891891893 | 0.9438947876447876 | 0.8515801354401806 | 0.45125482625482627 | 0.14174290071101167 | 0.7223476297968398 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.4081595845756136 | -0.2285351893583023 | 0.6785282625049395 | 0.03202369925788583 | 0.6122024664983245 | 0.8749034749034749 | 0.23212011386138107 | 0.2856952824467815 | 0.10666023166023166 | 0.8636935792160966 | 0.1283077724766775 | 0.38996138996138996 | 0.7242016932454085 | 0.20057247539148418 | 0.07577220077220077 | 0.8050060164965225 | 0.5565878378378378 | 0.8766891891891893 | 0.9438947876447876 | 0.8515801354401806 | 0.45125482625482627 | 0.14174290071101167 | 0.7223476297968398 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3928053875116229 | -0.32660970748378626 | 0.7556626147537044 | 0.04779185788588134 | 0.6394299450065852 | 0.8749034749034749 | 0.2816805642599486 | 0.336904984763941 | 0.10424710424710425 | 0.8636935792160966 | 0.1283077724766775 | 0.38996138996138996 | 0.7242016932454085 | 0.20057247539148418 | 0.07577220077220077 | 0.8050060164965225 | 0.5565878378378378 | 0.8766891891891893 | 0.9438947876447876 | 0.8515801354401806 | 0.45125482625482627 | 0.14174290071101167 | 0.7223476297968398 | False | Worldview Process Failure (entropy_within_band_share) | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-03` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `51.69%`
- Posterior Brier: `0.7275`
- Mean Entropy: `0.5498`
- Stable vs Benchmark Regime: `80.10%`
- Probability Within Band: `55.84%`
- Delta Within Band: `84.31%`
- Acceleration Within Band: `85.11%`
- Transition Probability Within Band: `87.10%`
- Entropy Within Band: `42.93%`
- Raw Beta vs Expectation MAE: `0.1423`
- Target Beta vs Expectation MAE: `0.2226`
- Deployment Exact Match: `52.23%`
- Deployment Rank Error: `0.6338`
- Deployment Pacing Abs Error: `0.3975`
- Deployment Pacing Signed Bias: `-0.0919`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `34.75%`
- Target Beta Within 5pct Of Expected: `6.25%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8636935792160966 | 0.7242016932454085 | 0.7242016932454085 | 0.8749034749034749 | 0.1283077724766775 | 0.20057247539148418 | 0.20057247539148418 |
| s4_sidecar | 0.8636935792160966 | 0.7242016932454085 | 0.6576789822534226 | 0.8749034749034749 | 0.1283077724766775 | 0.20057247539148418 | 0.24831822630025743 |
| s5_tractor | 0.8636935792160966 | 0.7242016932454085 | 0.6785282625049395 | 0.8749034749034749 | 0.1283077724766775 | 0.20057247539148418 | 0.23212011386138107 |
| s4s5_panorama | 0.8636935792160966 | 0.7242016932454085 | 0.7556626147537044 | 0.8749034749034749 | 0.1283077724766775 | 0.20057247539148418 | 0.2816805642599486 |

## Calibration Winner

- No scenario cleared the acceptance contract in calibration.
- Report is fail-closed; `standard` is shown below only as the baseline reference.

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9384226070941115 | -0.2285351893583023 | 0.7242016932454085 | 0.029116665229612627 | 0.6838737672487044 | 0.8749034749034749 | 0.20057247539148418 | 0.23098413174939594 | 0.07577220077220077 | 0.8636935792160966 | 0.1283077724766775 | 0.38996138996138996 | 0.7242016932454085 | 0.20057247539148418 | 0.07577220077220077 | 0.8050060164965225 | 0.5565878378378378 | 0.8766891891891893 | 0.9438947876447876 | 0.8515801354401806 | 0.45125482625482627 | 0.14174290071101167 | 0.7223476297968398 | False | Worldview Process Failure (entropy_within_band_share) | 0.2 | 0.15 | 0.05 | True |

## Production Recommendation

- Fail closed: no scenario, including `standard`, cleared the regime-process acceptance gate.
- Keep all panorama variants in diagnostic mode until the mainline process metrics themselves are repaired.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5026`, mean `0.7242`, below-floor share `0.00%`).
