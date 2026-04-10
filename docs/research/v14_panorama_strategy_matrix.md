# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `CACHED_ARTIFACT`
- Calibration Window: `2011-01-03` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: conditional expected-process gate first, then no worse max drawdown, no worse left-tail beta, bounded turnover drift
- Conditional expected-process gate: probability, delta, acceleration, and entropy are judged against context-aware benchmark bands driven by trend strength, transition intensity, uncertainty, and conflict score.

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.93018437402579 | -0.22771560496591337 | 0.723356984664543 | 0.02914409821659712 | 0.6831405945938134 | 0.8749034749034749 | 0.2012532490324716 | 0.23168410170625245 | 0.07432432432432433 | 0.8636896944875583 | 0.12835096787779005 | 0.38513513513513514 | 0.723356984664543 | 0.2012532490324716 | 0.07432432432432433 | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.14473341649956167 | 0.9157543789553155 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2824358394745268 | -0.24018207604480513 | 0.6570162123076713 | 0.03370124658756388 | 0.5941413303627114 | 0.8749034749034749 | 0.2488693022908552 | 0.30369133439857626 | 0.11631274131274132 | 0.8636896944875583 | 0.12835096787779005 | 0.38513513513513514 | 0.723356984664543 | 0.2012532490324716 | 0.07432432432432433 | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.14473341649956167 | 0.9157543789553155 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.4088079818453605 | -0.22771560496591303 | 0.6778282825299182 | 0.03206365666949039 | 0.6115777726275095 | 0.8749034749034749 | 0.23267022986430103 | 0.2861421143439264 | 0.10521235521235521 | 0.8636896944875583 | 0.12835096787779005 | 0.38513513513513514 | 0.723356984664543 | 0.2012532490324716 | 0.07432432432432433 | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.14473341649956167 | 0.9157543789553155 | False | Process Distortion | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3919841760085934 | -0.32656384879970535 | 0.7552886594011087 | 0.047804716480627445 | 0.6390678500695428 | 0.8749034749034749 | 0.2819514339513604 | 0.3370818301073894 | 0.10231660231660232 | 0.8636896944875583 | 0.12835096787779005 | 0.38513513513513514 | 0.723356984664543 | 0.2012532490324716 | 0.07432432432432433 | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.14473341649956167 | 0.9157543789553155 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-03` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `51.72%`
- Posterior Brier: `0.7293`
- Mean Entropy: `0.5534`
- Stable vs Benchmark Regime: `80.09%`
- Probability Within Band: `56.05%`
- Delta Within Band: `83.26%`
- Acceleration Within Band: `85.38%`
- Transition Probability Within Band: `94.05%`
- Entropy Within Band: `62.24%`
- Raw Beta vs Expectation MAE: `0.1426`
- Target Beta vs Expectation MAE: `0.2232`
- Deployment Exact Match: `52.11%`
- Deployment Rank Error: `0.6344`
- Deployment Pacing Abs Error: `0.3979`
- Deployment Pacing Signed Bias: `-0.0933`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `34.33%`
- Target Beta Within 5pct Of Expected: `6.16%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8636896944875583 | 0.723356984664543 | 0.723356984664543 | 0.8749034749034749 | 0.12835096787779005 | 0.2012532490324716 | 0.2012532490324716 |
| s4_sidecar | 0.8636896944875583 | 0.723356984664543 | 0.6570162123076713 | 0.8749034749034749 | 0.12835096787779005 | 0.2012532490324716 | 0.2488693022908552 |
| s5_tractor | 0.8636896944875583 | 0.723356984664543 | 0.6778282825299182 | 0.8749034749034749 | 0.12835096787779005 | 0.2012532490324716 | 0.23267022986430103 |
| s4s5_panorama | 0.8636896944875583 | 0.723356984664543 | 0.7552886594011087 | 0.8749034749034749 | 0.12835096787779005 | 0.2012532490324716 | 0.2819514339513604 |

## Conditional Process Gate Lens

| scenario | acceptance_pass | acceptance_reason | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | transition_entropy_within_band_share |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | True | PASS | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.9157543789553155 |
| s4_sidecar | False | Drawdown Regression | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.9157543789553155 |
| s5_tractor | False | Process Distortion | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.9157543789553155 |
| s4s5_panorama | False | Drawdown Regression | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.9157543789553155 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `0.8926`
- Calibration Max Drawdown: `-0.1067`
- Calibration Left-Tail Beta: `0.7094`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.93018437402579 | -0.22771560496591337 | 0.723356984664543 | 0.02914409821659712 | 0.6831405945938134 | 0.8749034749034749 | 0.2012532490324716 | 0.23168410170625245 | 0.07432432432432433 | 0.8636896944875583 | 0.12835096787779005 | 0.38513513513513514 | 0.723356984664543 | 0.2012532490324716 | 0.07432432432432433 | 0.8042330447287078 | 0.5536673261420157 | 0.8646269333359966 | 0.9436279119509319 | 0.9266221832990494 | 0.6614259729213197 | 0.14473341649956167 | 0.9157543789553155 | True | PASS | 0.2 | 0.15 | 0.05 | False |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5026`, mean `0.7234`, below-floor share `0.00%`).
