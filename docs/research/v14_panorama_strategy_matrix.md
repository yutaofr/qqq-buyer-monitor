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
| standard | 2072.0 | 1.9216029891580906 | -0.237751146266181 | 0.7607147997269852 | 0.027149864516844237 | 0.7137406511298323 | 0.8749034749034749 | 0.182823808439211 | 0.2157862045111324 | 0.12693050193050193 | 0.8585940647761227 | 0.14417556768544773 | 0.3170849420849421 | 0.7607147997269852 | 0.182823808439211 | 0.12693050193050193 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2114943761654735 | -0.2471823845832669 | 0.6814719145643282 | 0.03336712952357131 | 0.6037783024643555 | 0.8749034749034749 | 0.2397630744889675 | 0.2989805735153176 | 0.15444015444015444 | 0.8585940647761227 | 0.14417556768544773 | 0.3170849420849421 | 0.7607147997269852 | 0.182823808439211 | 0.12693050193050193 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.3303512604184178 | -0.23775114626618077 | 0.7031125264335849 | 0.031607786201138945 | 0.6236122407041695 | 0.8749034749034749 | 0.22270616375783853 | 0.28063263933693006 | 0.14671814671814673 | 0.8585940647761227 | 0.14417556768544773 | 0.3170849420849421 | 0.7607147997269852 | 0.182823808439211 | 0.12693050193050193 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3286877855128871 | -0.32140686625706827 | 0.7740462605065129 | 0.0473391639437738 | 0.6426724238739221 | 0.8749034749034749 | 0.27565616279518196 | 0.3341162996129688 | 0.12210424710424711 | 0.8585940647761227 | 0.14417556768544773 | 0.3170849420849421 | 0.7607147997269852 | 0.182823808439211 | 0.12693050193050193 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `42.11%`
- Posterior Brier: `0.8418`
- Mean Entropy: `0.3718`
- Raw Beta vs Expectation MAE: `0.1622`
- Target Beta vs Expectation MAE: `0.2093`
- Deployment Exact Match: `42.37%`
- Deployment Rank Error: `0.7628`
- Deployment Pacing Abs Error: `0.4669`
- Deployment Pacing Signed Bias: `-0.0941`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `28.93%`
- Target Beta Within 5pct Of Expected: `10.93%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8585940647761227 | 0.7607147997269852 | 0.7607147997269852 | 0.8749034749034749 | 0.14417556768544773 | 0.182823808439211 | 0.182823808439211 |
| s4_sidecar | 0.8585940647761227 | 0.7607147997269852 | 0.6814719145643282 | 0.8749034749034749 | 0.14417556768544773 | 0.182823808439211 | 0.2397630744889675 |
| s5_tractor | 0.8585940647761227 | 0.7607147997269852 | 0.7031125264335849 | 0.8749034749034749 | 0.14417556768544773 | 0.182823808439211 | 0.22270616375783853 |
| s4s5_panorama | 0.8585940647761227 | 0.7607147997269852 | 0.7740462605065129 | 0.8749034749034749 | 0.14417556768544773 | 0.182823808439211 | 0.27565616279518196 |

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
| standard | 2072.0 | 1.9216029891580906 | -0.237751146266181 | 0.7607147997269852 | 0.027149864516844237 | 0.7137406511298323 | 0.8749034749034749 | 0.182823808439211 | 0.2157862045111324 | 0.12693050193050193 | 0.8585940647761227 | 0.14417556768544773 | 0.3170849420849421 | 0.7607147997269852 | 0.182823808439211 | 0.12693050193050193 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5044`, mean `0.7607`, below-floor share `0.00%`).
