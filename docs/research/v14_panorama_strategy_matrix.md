# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `PIT_FALLBACK`
- Calibration Window: `2011-01-01` to `2017-12-29`
- Holdout Window: `2018-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: no worse max drawdown, no worse left-tail beta, bounded turnover drift

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2069.0 | 2.1711166917970006 | -0.29865637113121113 | 0.8182868469341912 | 0.00778722464253059 | 0.8148150103157037 | 0.8747220879652006 | 0.14554209832149217 | 0.17855429808003626 | 0.18559690671822135 | 0.9543089262001663 | 0.13663597529862784 | 0.3639439342677622 | 0.8182868469341912 | 0.14554209832149217 | 0.18559690671822135 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2069.0 | 1.3723286725716544 | -0.28898207163977396 | 0.6881329610988903 | 0.01718366908542122 | 0.5937918474168811 | 0.8747220879652006 | 0.23456599410731327 | 0.30073956874669483 | 0.18124697921701305 | 0.9543089262001663 | 0.13663597529862784 | 0.3639439342677622 | 0.8182868469341912 | 0.14554209832149217 | 0.18559690671822135 | True | PASS | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2069.0 | 1.5002151412643951 | -0.29865637113121146 | 0.7552848027197439 | 0.01718016426932904 | 0.6834668557316225 | 0.8747220879652006 | 0.1919158503726631 | 0.25703340642135103 | 0.19623006283228614 | 0.9543089262001663 | 0.13663597529862784 | 0.3639439342677622 | 0.8182868469341912 | 0.14554209832149217 | 0.18559690671822135 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2069.0 | 1.4332430534757066 | -0.3035448374360865 | 0.7483445240421019 | 0.03250241915384618 | 0.6244023930576759 | 0.8747220879652006 | 0.2826837160879981 | 0.3505546153272209 | 0.15514741420976316 | 0.9543089262001663 | 0.13663597529862784 | 0.3639439342677622 | 0.8182868469341912 | 0.14554209832149217 | 0.18559690671822135 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `44.49%`
- Posterior Brier: `0.8314`
- Mean Entropy: `0.5106`
- Raw Beta vs Expectation MAE: `0.1646`
- Target Beta vs Expectation MAE: `0.2008`
- Deployment Exact Match: `42.06%`
- Deployment Rank Error: `0.8467`
- Deployment Pacing Abs Error: `0.5098`
- Deployment Pacing Signed Bias: `0.0396`
- Raw Beta Min: `0.5003`
- Beta Expectation Min: `0.5003`
- Target Beta Min: `0.5005`
- Raw Beta Within 5pct Of Expected: `27.31%`
- Target Beta Within 5pct Of Expected: `13.47%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.9543089262001663 | 0.8182868469341912 | 0.8182868469341912 | 0.8747220879652006 | 0.13663597529862784 | 0.14554209832149217 | 0.14554209832149217 |
| s4_sidecar | 0.9543089262001663 | 0.8182868469341912 | 0.6881329610988903 | 0.8747220879652006 | 0.13663597529862784 | 0.14554209832149217 | 0.23456599410731327 |
| s5_tractor | 0.9543089262001663 | 0.8182868469341912 | 0.7552848027197439 | 0.8747220879652006 | 0.13663597529862784 | 0.14554209832149217 | 0.1919158503726631 |
| s4s5_panorama | 0.9543089262001663 | 0.8182868469341912 | 0.7483445240421019 | 0.8747220879652006 | 0.13663597529862784 | 0.14554209832149217 | 0.2826837160879981 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.4710`
- Calibration Max Drawdown: `-0.1365`
- Calibration Left-Tail Beta: `0.7145`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2069.0 | 2.1711166917970006 | -0.29865637113121113 | 0.8182868469341912 | 0.00778722464253059 | 0.8148150103157037 | 0.8747220879652006 | 0.14554209832149217 | 0.17855429808003626 | 0.18559690671822135 | 0.9543089262001663 | 0.13663597529862784 | 0.3639439342677622 | 0.8182868469341912 | 0.14554209832149217 | 0.18559690671822135 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5016`, mean `0.8183`, below-floor share `0.00%`).
