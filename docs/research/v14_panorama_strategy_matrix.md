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
| standard | 2070.0 | 1.760681693197364 | -0.22754788970414452 | 0.7203853955553219 | 0.02054324540122544 | 0.6794561043336673 | 0.8747826086956522 | 0.20716913319848243 | 0.2368798052823294 | 0.07584541062801932 | 0.8579193488504894 | 0.14378228985472133 | 0.314975845410628 | 0.7203853955553219 | 0.20716913319848243 | 0.07584541062801932 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2070.0 | 1.160997241801049 | -0.2368758642764831 | 0.6525748433038727 | 0.026773920717628404 | 0.5867926356074192 | 0.8747826086956522 | 0.25684316821947994 | 0.3095276811892618 | 0.11835748792270531 | 0.8579193488504894 | 0.14378228985472133 | 0.314975845410628 | 0.7203853955553219 | 0.20716913319848243 | 0.07584541062801932 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2070.0 | 1.2888995271295247 | -0.2275478897041444 | 0.6712207937016769 | 0.024859149004320538 | 0.6038237565866846 | 0.8747826086956522 | 0.2417339969737853 | 0.2930909764144585 | 0.10628019323671498 | 0.8579193488504894 | 0.14378228985472133 | 0.314975845410628 | 0.7203853955553219 | 0.20716913319848243 | 0.07584541062801932 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2070.0 | 1.2679901402641374 | -0.32063469195492855 | 0.7552300426106132 | 0.04496748044567959 | 0.6349488427581806 | 0.8747826086956522 | 0.28592499703360524 | 0.33977926322387486 | 0.10048309178743961 | 0.8579193488504894 | 0.14378228985472133 | 0.314975845410628 | 0.7203853955553219 | 0.20716913319848243 | 0.07584541062801932 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `41.97%`
- Posterior Brier: `0.8589`
- Mean Entropy: `0.5090`
- Raw Beta vs Expectation MAE: `0.1625`
- Target Beta vs Expectation MAE: `0.2300`
- Deployment Exact Match: `43.12%`
- Deployment Rank Error: `0.7499`
- Deployment Pacing Abs Error: `0.4482`
- Deployment Pacing Signed Bias: `-0.1631`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `28.92%`
- Target Beta Within 5pct Of Expected: `6.26%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8579193488504894 | 0.7203853955553219 | 0.7203853955553219 | 0.8747826086956522 | 0.14378228985472133 | 0.20716913319848243 | 0.20716913319848243 |
| s4_sidecar | 0.8579193488504894 | 0.7203853955553219 | 0.6525748433038727 | 0.8747826086956522 | 0.14378228985472133 | 0.20716913319848243 | 0.25684316821947994 |
| s5_tractor | 0.8579193488504894 | 0.7203853955553219 | 0.6712207937016769 | 0.8747826086956522 | 0.14378228985472133 | 0.20716913319848243 | 0.2417339969737853 |
| s4s5_panorama | 0.8579193488504894 | 0.7203853955553219 | 0.7552300426106132 | 0.8747826086956522 | 0.14378228985472133 | 0.20716913319848243 | 0.28592499703360524 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.2262`
- Calibration Max Drawdown: `-0.1095`
- Calibration Left-Tail Beta: `0.6862`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2070.0 | 1.760681693197364 | -0.22754788970414452 | 0.7203853955553219 | 0.02054324540122544 | 0.6794561043336673 | 0.8747826086956522 | 0.20716913319848243 | 0.2368798052823294 | 0.07584541062801932 | 0.8579193488504894 | 0.14378228985472133 | 0.314975845410628 | 0.7203853955553219 | 0.20716913319848243 | 0.07584541062801932 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5034`, mean `0.7204`, below-floor share `0.00%`).
