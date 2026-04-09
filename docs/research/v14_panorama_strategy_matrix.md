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
| standard | 2070.0 | 1.8749295915543946 | -0.23775114626618066 | 0.7608549842614944 | 0.02716843687258439 | 0.7137406516741485 | 0.8747826086956522 | 0.18262907025178093 | 0.21555942466665196 | 0.12705314009661836 | 0.8587627474994584 | 0.14400956069471677 | 0.3173913043478261 | 0.7608549842614944 | 0.18262907025178093 | 0.12705314009661836 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2070.0 | 1.1761653955305076 | -0.24718238458326702 | 0.6815355353705135 | 0.03339170750663724 | 0.6037783012256603 | 0.8747826086956522 | 0.23962335083584335 | 0.2988861665745754 | 0.15458937198067632 | 0.8587627474994584 | 0.14400956069471677 | 0.3173913043478261 | 0.7608549842614944 | 0.18262907025178093 | 0.12705314009661836 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2070.0 | 1.3003536622537988 | -0.23775114626618066 | 0.7033087663836376 | 0.03163832510792028 | 0.6236122422580791 | 0.8747826086956522 | 0.22243824944738366 | 0.28033769789251956 | 0.1468599033816425 | 0.8587627474994584 | 0.14400956069471677 | 0.3173913043478261 | 0.7608549842614944 | 0.18262907025178093 | 0.12705314009661836 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2070.0 | 1.298711870222251 | -0.32140686625706827 | 0.7743110349623699 | 0.04738490052347937 | 0.6426724255625001 | 0.8747826086956522 | 0.2754394088706444 | 0.3339161810025475 | 0.12222222222222222 | 0.8587627474994584 | 0.14400956069471677 | 0.3173913043478261 | 0.7608549842614944 | 0.18262907025178093 | 0.12705314009661836 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `42.13%`
- Posterior Brier: `0.8416`
- Mean Entropy: `0.3717`
- Raw Beta vs Expectation MAE: `0.1621`
- Target Beta vs Expectation MAE: `0.2092`
- Deployment Exact Match: `42.39%`
- Deployment Rank Error: `0.7627`
- Deployment Pacing Abs Error: `0.4668`
- Deployment Pacing Signed Bias: `-0.0938`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `28.95%`
- Target Beta Within 5pct Of Expected: `10.94%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8587627474994584 | 0.7608549842614944 | 0.7608549842614944 | 0.8747826086956522 | 0.14400956069471677 | 0.18262907025178093 | 0.18262907025178093 |
| s4_sidecar | 0.8587627474994584 | 0.7608549842614944 | 0.6815355353705135 | 0.8747826086956522 | 0.14400956069471677 | 0.18262907025178093 | 0.23962335083584335 |
| s5_tractor | 0.8587627474994584 | 0.7608549842614944 | 0.7033087663836376 | 0.8747826086956522 | 0.14400956069471677 | 0.18262907025178093 | 0.22243824944738366 |
| s4s5_panorama | 0.8587627474994584 | 0.7608549842614944 | 0.7743110349623699 | 0.8747826086956522 | 0.14400956069471677 | 0.18262907025178093 | 0.2754394088706444 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.2958`
- Calibration Max Drawdown: `-0.1142`
- Calibration Left-Tail Beta: `0.7115`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2070.0 | 1.8749295915543946 | -0.23775114626618066 | 0.7608549842614944 | 0.02716843687258439 | 0.7137406516741485 | 0.8747826086956522 | 0.18262907025178093 | 0.21555942466665196 | 0.12705314009661836 | 0.8587627474994584 | 0.14400956069471677 | 0.3173913043478261 | 0.7608549842614944 | 0.18262907025178093 | 0.12705314009661836 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5044`, mean `0.7609`, below-floor share `0.00%`).
