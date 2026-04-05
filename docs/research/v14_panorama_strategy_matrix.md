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
| standard | 2152.0 | 1.5898115483205508 | -0.2315165684381959 | 0.7312999150682237 | 0.0010381335983145057 | 0.6886575856558467 | 0.8753252788104089 | 0.1903104859933111 | 0.2337544762273369 | 0.05065055762081784 | 0.8571841686699272 | 0.11865406112788898 | 0.3150557620817844 | 0.7312999150682237 | 0.1903104859933111 | 0.05065055762081784 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2152.0 | 1.2569130392584702 | -0.218356628718553 | 0.6536843713907227 | 0.015252201822241346 | 0.6089133235100909 | 0.8753252788104089 | 0.25044114464602796 | 0.31736127497564703 | 0.11802973977695168 | 0.8571841686699272 | 0.11865406112788898 | 0.3150557620817844 | 0.7312999150682237 | 0.1903104859933111 | 0.05065055762081784 | True | PASS | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2152.0 | 1.387292167600172 | -0.231516568438196 | 0.6969065453364984 | 0.008545326754304151 | 0.6300842104714022 | 0.8753252788104089 | 0.21702596755571213 | 0.2749768320785891 | 0.07946096654275094 | 0.8571841686699272 | 0.11865406112788898 | 0.3150557620817844 | 0.7312999150682237 | 0.1903104859933111 | 0.05065055762081784 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2152.0 | 1.467961652607964 | -0.2575060572096296 | 0.6835540150495488 | 0.025136643454430018 | 0.6049990137460521 | 0.8753252788104089 | 0.28748445613563794 | 0.3560376899296064 | 0.10362453531598513 | 0.8571841686699272 | 0.11865406112788898 | 0.3150557620817844 | 0.7312999150682237 | 0.1903104859933111 | 0.05065055762081784 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `62.33%`
- Posterior Brier: `0.5160`
- Mean Entropy: `0.4907`
- Raw Beta vs Expectation MAE: `0.1297`
- Target Beta vs Expectation MAE: `0.2057`
- Deployment Exact Match: `53.03%`
- Deployment Rank Error: `0.6510`
- Deployment Pacing Abs Error: `0.3860`
- Deployment Pacing Signed Bias: `-0.1790`
- Raw Beta Min: `0.5000`
- Beta Expectation Min: `0.5000`
- Target Beta Min: `0.5000`
- Raw Beta Within 5pct Of Expected: `33.69%`
- Target Beta Within 5pct Of Expected: `14.81%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `3.39%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8571841686699272 | 0.7312999150682237 | 0.7312999150682237 | 0.8753252788104089 | 0.11865406112788898 | 0.1903104859933111 | 0.1903104859933111 |
| s4_sidecar | 0.8571841686699272 | 0.7312999150682237 | 0.6536843713907227 | 0.8753252788104089 | 0.11865406112788898 | 0.1903104859933111 | 0.25044114464602796 |
| s5_tractor | 0.8571841686699272 | 0.7312999150682237 | 0.6969065453364984 | 0.8753252788104089 | 0.11865406112788898 | 0.1903104859933111 | 0.21702596755571213 |
| s4s5_panorama | 0.8571841686699272 | 0.7312999150682237 | 0.6835540150495488 | 0.8753252788104089 | 0.11865406112788898 | 0.1903104859933111 | 0.28748445613563794 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `1.3708`
- Calibration Max Drawdown: `-0.1151`
- Calibration Left-Tail Beta: `0.6541`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2152.0 | 1.5898115483205508 | -0.2315165684381959 | 0.7312999150682237 | 0.0010381335983145057 | 0.6886575856558467 | 0.8753252788104089 | 0.1903104859933111 | 0.2337544762273369 | 0.05065055762081784 | 0.8571841686699272 | 0.11865406112788898 | 0.3150557620817844 | 0.7312999150682237 | 0.1903104859933111 | 0.05065055762081784 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5072`, mean `0.7313`, below-floor share `0.00%`).
