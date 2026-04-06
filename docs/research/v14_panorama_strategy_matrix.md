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
| standard | 2070.0 | 1.7716381587188135 | -0.22706301841611254 | 0.7256981274091809 | 0.0198994317425383 | 0.686841388577646 | 0.8747826086956522 | 0.20305357680706831 | 0.23392485335994445 | 0.07536231884057971 | 0.8437383126803595 | 0.15380127106828637 | 0.30241545893719807 | 0.7256981274091809 | 0.20305357680706831 | 0.07536231884057971 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2070.0 | 1.156835208659667 | -0.23637626768090403 | 0.6552873879166269 | 0.026729392600817477 | 0.5883001655285125 | 0.8747826086956522 | 0.2555560312521411 | 0.3089784825245746 | 0.11352657004830918 | 0.8437383126803595 | 0.15380127106828637 | 0.30241545893719807 | 0.7256981274091809 | 0.20305357680706831 | 0.07536231884057971 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2070.0 | 1.2937352381746554 | -0.22706301841611254 | 0.6740715429605468 | 0.024569580122559734 | 0.60526485256848 | 0.8747826086956522 | 0.23996155439192574 | 0.29251628211934194 | 0.10338164251207729 | 0.8437383126803595 | 0.15380127106828637 | 0.30241545893719807 | 0.7256981274091809 | 0.20305357680706831 | 0.07536231884057971 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2070.0 | 1.2653823366315269 | -0.31978771704511266 | 0.7568376721250658 | 0.04485766537288744 | 0.6361913041715161 | 0.8747826086956522 | 0.2849519120473531 | 0.3397473673240003 | 0.10096618357487923 | 0.8437383126803595 | 0.15380127106828637 | 0.30241545893719807 | 0.7256981274091809 | 0.20305357680706831 | 0.07536231884057971 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `40.85%`
- Posterior Brier: `0.8944`
- Mean Entropy: `0.4884`
- Raw Beta vs Expectation MAE: `0.1699`
- Target Beta vs Expectation MAE: `0.2291`
- Deployment Exact Match: `41.53%`
- Deployment Rank Error: `0.7805`
- Deployment Pacing Abs Error: `0.4682`
- Deployment Pacing Signed Bias: `-0.1698`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5002`
- Raw Beta Within 5pct Of Expected: `27.59%`
- Target Beta Within 5pct Of Expected: `5.87%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8437383126803595 | 0.7256981274091809 | 0.7256981274091809 | 0.8747826086956522 | 0.15380127106828637 | 0.20305357680706831 | 0.20305357680706831 |
| s4_sidecar | 0.8437383126803595 | 0.7256981274091809 | 0.6552873879166269 | 0.8747826086956522 | 0.15380127106828637 | 0.20305357680706831 | 0.2555560312521411 |
| s5_tractor | 0.8437383126803595 | 0.7256981274091809 | 0.6740715429605468 | 0.8747826086956522 | 0.15380127106828637 | 0.20305357680706831 | 0.23996155439192574 |
| s4s5_panorama | 0.8437383126803595 | 0.7256981274091809 | 0.7568376721250658 | 0.8747826086956522 | 0.15380127106828637 | 0.20305357680706831 | 0.2849519120473531 |

## Calibration Winner

- Scenario: `s4s5_panorama`
- Tractor Threshold: `0.25`
- Sidecar Threshold: `0.25`
- Calm Threshold: `0.15`
- Calibration Return: `1.2199`
- Calibration Max Drawdown: `-0.0864`
- Calibration Left-Tail Beta: `0.6021`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| s4s5_panorama | 2070.0 | 1.127885483895362 | -0.38716680731262243 | 0.8790194189554513 | 0.04496253263976517 | 0.7390551481359569 | 0.8747826086956522 | 0.3028920149307135 | 0.3549213081435002 | 0.07439613526570048 | 0.8437383126803595 | 0.15380127106828637 | 0.30241545893719807 | 0.7256981274091809 | 0.20305357680706831 | 0.07536231884057971 | False | Defensive Violation | 0.25 | 0.25 | 0.15 |

## Production Recommendation

- Keep `standard` as the production champion.
- Keep `s4_sidecar`, `s5_tractor`, and `s4s5_panorama` in shadow/diagnostic mode only.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5061`, mean `0.7257`, below-floor share `0.00%`).
