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
| standard | 2070.0 | 1.7264840483581891 | -0.2266156434076102 | 0.7217219907430583 | 0.01932676453114833 | 0.6793202762187001 | 0.8747826086956522 | 0.20393837665050754 | 0.23668346747941657 | 0.09371980676328502 | 0.8422122214870955 | 0.15367677526068743 | 0.3120772946859903 | 0.7217219907430583 | 0.20393837665050754 | 0.09371980676328502 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2070.0 | 1.1560648623519598 | -0.23311380372205648 | 0.6530538479887716 | 0.0261772732018847 | 0.5859201808110949 | 0.8747826086956522 | 0.25618633824932685 | 0.31021496759146666 | 0.12173913043478261 | 0.8422122214870955 | 0.15367677526068743 | 0.3120772946859903 | 0.7217219907430583 | 0.20393837665050754 | 0.09371980676328502 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2070.0 | 1.3462689222837612 | -0.22661564340760976 | 0.6760857237471516 | 0.023939203236023245 | 0.6034298383061443 | 0.8747826086956522 | 0.23848270169901048 | 0.2911754857706669 | 0.11545893719806763 | 0.8422122214870955 | 0.15367677526068743 | 0.3120772946859903 | 0.7217219907430583 | 0.20393837665050754 | 0.09371980676328502 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2070.0 | 1.250188662363767 | -0.31713844318289175 | 0.7739517989112428 | 0.04278962704323321 | 0.6637539934810461 | 0.8747826086956522 | 0.2984024522769289 | 0.3531984197706963 | 0.09371980676328502 | 0.8422122214870955 | 0.15367677526068743 | 0.3120772946859903 | 0.7217219907430583 | 0.20393837665050754 | 0.09371980676328502 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `40.46%`
- Posterior Brier: `0.8973`
- Mean Entropy: `0.4819`
- Raw Beta vs Expectation MAE: `0.1698`
- Target Beta vs Expectation MAE: `0.2294`
- Deployment Exact Match: `41.16%`
- Deployment Rank Error: `0.7849`
- Deployment Pacing Abs Error: `0.4708`
- Deployment Pacing Signed Bias: `-0.1695`
- Raw Beta Min: `0.5083`
- Beta Expectation Min: `0.5083`
- Target Beta Min: `0.5002`
- Raw Beta Within 5pct Of Expected: `28.74%`
- Target Beta Within 5pct Of Expected: `7.00%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8422122214870955 | 0.7217219907430583 | 0.7217219907430583 | 0.8747826086956522 | 0.15367677526068743 | 0.20393837665050754 | 0.20393837665050754 |
| s4_sidecar | 0.8422122214870955 | 0.7217219907430583 | 0.6530538479887716 | 0.8747826086956522 | 0.15367677526068743 | 0.20393837665050754 | 0.25618633824932685 |
| s5_tractor | 0.8422122214870955 | 0.7217219907430583 | 0.6760857237471516 | 0.8747826086956522 | 0.15367677526068743 | 0.20393837665050754 | 0.23848270169901048 |
| s4s5_panorama | 0.8422122214870955 | 0.7217219907430583 | 0.7739517989112428 | 0.8747826086956522 | 0.15367677526068743 | 0.20393837665050754 | 0.2984024522769289 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.2103`
- Calibration Max Drawdown: `-0.1071`
- Calibration Left-Tail Beta: `0.6808`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2070.0 | 1.7264840483581891 | -0.2266156434076102 | 0.7217219907430583 | 0.01932676453114833 | 0.6793202762187001 | 0.8747826086956522 | 0.20393837665050754 | 0.23668346747941657 | 0.09371980676328502 | 0.8422122214870955 | 0.15367677526068743 | 0.3120772946859903 | 0.7217219907430583 | 0.20393837665050754 | 0.09371980676328502 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5065`, mean `0.7217`, below-floor share `0.00%`).
