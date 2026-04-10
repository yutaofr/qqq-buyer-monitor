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
| standard | 2072.0 | 1.9248421708117927 | -0.24497955435638652 | 0.7491981294765795 | 0.025122891178093507 | 0.695781942240525 | 0.8749034749034749 | 0.179593605253692 | 0.21143617340521703 | 0.10231660231660232 | 0.8698279733489 | 0.12271241694730109 | 0.4555984555984556 | 0.7491981294765795 | 0.179593605253692 | 0.10231660231660232 | 0.8121713606815911 | 0.48081563706563707 | 0.705719111969112 | 0.5343870656370656 | 0.7108317214700194 | 0.152992277992278 | 0.3313375295967826 | 0.2940038684719536 | False | Worldview Process Failure (acceleration_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2844109884533634 | -0.2569888663242176 | 0.6773895673740606 | 0.03117185568562776 | 0.6032364638532889 | 0.8749034749034749 | 0.23241014167705795 | 0.29289785879574043 | 0.1414092664092664 | 0.8698279733489 | 0.12271241694730109 | 0.4555984555984556 | 0.7491981294765795 | 0.179593605253692 | 0.10231660231660232 | 0.8121713606815911 | 0.48081563706563707 | 0.705719111969112 | 0.5343870656370656 | 0.7108317214700194 | 0.152992277992278 | 0.3313375295967826 | 0.2940038684719536 | False | Worldview Process Failure (acceleration_within_band_share) | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.408219520207028 | -0.2449795543563863 | 0.6980016812208537 | 0.02934854835236429 | 0.6202054753214598 | 0.8749034749034749 | 0.21643160145411647 | 0.27484023619293446 | 0.12982625482625482 | 0.8698279733489 | 0.12271241694730109 | 0.4555984555984556 | 0.7491981294765795 | 0.179593605253692 | 0.10231660231660232 | 0.8121713606815911 | 0.48081563706563707 | 0.705719111969112 | 0.5343870656370656 | 0.7108317214700194 | 0.152992277992278 | 0.3313375295967826 | 0.2940038684719536 | False | Worldview Process Failure (acceleration_within_band_share) | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.349294405274604 | -0.3318254748692633 | 0.7655012428487191 | 0.04644160539208373 | 0.6446785327283244 | 0.8749034749034749 | 0.2751980568723452 | 0.3333324459489588 | 0.11534749034749035 | 0.8698279733489 | 0.12271241694730109 | 0.4555984555984556 | 0.7491981294765795 | 0.179593605253692 | 0.10231660231660232 | 0.8121713606815911 | 0.48081563706563707 | 0.705719111969112 | 0.5343870656370656 | 0.7108317214700194 | 0.152992277992278 | 0.3313375295967826 | 0.2940038684719536 | False | Worldview Process Failure (acceleration_within_band_share) | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `52.32%`
- Posterior Brier: `0.7094`
- Mean Entropy: `0.4770`
- Stable vs Benchmark Regime: `81.02%`
- Probability Within Band: `48.34%`
- Delta Within Band: `72.16%`
- Acceleration Within Band: `55.31%`
- Transition Probability Within Band: `71.21%`
- Entropy Within Band: `14.40%`
- Raw Beta vs Expectation MAE: `0.1353`
- Target Beta vs Expectation MAE: `0.2008`
- Deployment Exact Match: `53.26%`
- Deployment Rank Error: `0.6232`
- Deployment Pacing Abs Error: `0.3899`
- Deployment Pacing Signed Bias: `-0.0925`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `43.36%`
- Target Beta Within 5pct Of Expected: `8.97%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8698279733489 | 0.7491981294765795 | 0.7491981294765795 | 0.8749034749034749 | 0.12271241694730109 | 0.179593605253692 | 0.179593605253692 |
| s4_sidecar | 0.8698279733489 | 0.7491981294765795 | 0.6773895673740606 | 0.8749034749034749 | 0.12271241694730109 | 0.179593605253692 | 0.23241014167705795 |
| s5_tractor | 0.8698279733489 | 0.7491981294765795 | 0.6980016812208537 | 0.8749034749034749 | 0.12271241694730109 | 0.179593605253692 | 0.21643160145411647 |
| s4s5_panorama | 0.8698279733489 | 0.7491981294765795 | 0.7655012428487191 | 0.8749034749034749 | 0.12271241694730109 | 0.179593605253692 | 0.2751980568723452 |

## Calibration Winner

- No scenario cleared the acceptance contract in calibration.
- Report is fail-closed; `standard` is shown below only as the baseline reference.

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9248421708117927 | -0.24497955435638652 | 0.7491981294765795 | 0.025122891178093507 | 0.695781942240525 | 0.8749034749034749 | 0.179593605253692 | 0.21143617340521703 | 0.10231660231660232 | 0.8698279733489 | 0.12271241694730109 | 0.4555984555984556 | 0.7491981294765795 | 0.179593605253692 | 0.10231660231660232 | 0.8121713606815911 | 0.48081563706563707 | 0.705719111969112 | 0.5343870656370656 | 0.7108317214700194 | 0.152992277992278 | 0.3313375295967826 | 0.2940038684719536 | False | Worldview Process Failure (acceleration_within_band_share) | 0.2 | 0.15 | 0.05 | True |

## Production Recommendation

- Fail closed: no scenario, including `standard`, cleared the regime-process acceptance gate.
- Keep all panorama variants in diagnostic mode until the mainline process metrics themselves are repaired.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5027`, mean `0.7492`, below-floor share `0.00%`).
