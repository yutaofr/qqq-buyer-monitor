# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `ALFRED+PIT_FALLBACK`
- Calibration Window: `2011-01-01` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: no worse max drawdown, no worse left-tail beta, bounded turnover drift

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2070.0 | 1.6534025161653325 | -0.24393635727651475 | 0.727236862771121 | 0.0017627123625177273 | 0.7090909087342893 | 0.8747826086956522 | 0.18124679116972664 | 0.21918084548021294 | 0.08115942028985507 | 0.8519875205523874 | 0.11875265910063643 | 0.2536231884057971 | 0.727236862771121 | 0.18124679116972664 | 0.08115942028985507 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2070.0 | 1.2589668852291935 | -0.24348720973678295 | 0.6349492327791759 | 0.011184550684740426 | 0.565897616930423 | 0.8747826086956522 | 0.2565320896739363 | 0.3164736408729725 | 0.13381642512077294 | 0.8519875205523874 | 0.11875265910063643 | 0.2536231884057971 | 0.727236862771121 | 0.18124679116972664 | 0.08115942028985507 | True | PASS | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2070.0 | 1.3531311616707584 | -0.2439363572765153 | 0.6852242076331987 | 0.009086730977835049 | 0.6364088526836358 | 0.8747826086956522 | 0.21760730080645596 | 0.275702281272101 | 0.10966183574879228 | 0.8519875205523874 | 0.11875265910063643 | 0.2536231884057971 | 0.727236862771121 | 0.18124679116972664 | 0.08115942028985507 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2070.0 | 1.3748462155555412 | -0.2631144790321205 | 0.7061440764727666 | 0.02753946369110616 | 0.6035679604132744 | 0.8747826086956522 | 0.30519118389701344 | 0.36290962393953197 | 0.10096618357487923 | 0.8519875205523874 | 0.11875265910063643 | 0.2536231884057971 | 0.727236862771121 | 0.18124679116972664 | 0.08115942028985507 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `67.40%`
- Posterior Brier: `0.4526`
- Mean Entropy: `0.4818`
- Raw Beta vs Expectation MAE: `0.1255`
- Target Beta vs Expectation MAE: `0.2034`
- Deployment Exact Match: `58.42%`
- Deployment Rank Error: `0.6262`
- Deployment Pacing Abs Error: `0.3605`
- Deployment Pacing Signed Bias: `-0.1242`
- Raw Beta Min: `0.5000`
- Beta Expectation Min: `0.5000`
- Target Beta Min: `0.5000`
- Raw Beta Within 5pct Of Expected: `31.17%`
- Target Beta Within 5pct Of Expected: `15.71%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `10.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8519875205523874 | 0.727236862771121 | 0.727236862771121 | 0.8747826086956522 | 0.11875265910063643 | 0.18124679116972664 | 0.18124679116972664 |
| s4_sidecar | 0.8519875205523874 | 0.727236862771121 | 0.6349492327791759 | 0.8747826086956522 | 0.11875265910063643 | 0.18124679116972664 | 0.2565320896739363 |
| s5_tractor | 0.8519875205523874 | 0.727236862771121 | 0.6852242076331987 | 0.8747826086956522 | 0.11875265910063643 | 0.18124679116972664 | 0.21760730080645596 |
| s4s5_panorama | 0.8519875205523874 | 0.727236862771121 | 0.7061440764727666 | 0.8747826086956522 | 0.11875265910063643 | 0.18124679116972664 | 0.30519118389701344 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.3377`
- Calibration Max Drawdown: `-0.1095`
- Calibration Left-Tail Beta: `0.6416`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2070.0 | 1.6534025161653325 | -0.24393635727651475 | 0.727236862771121 | 0.0017627123625177273 | 0.7090909087342893 | 0.8747826086956522 | 0.18124679116972664 | 0.21918084548021294 | 0.08115942028985507 | 0.8519875205523874 | 0.11875265910063643 | 0.2536231884057971 | 0.727236862771121 | 0.18124679116972664 | 0.08115942028985507 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5000`, mean `0.7272`, below-floor share `0.00%`).
