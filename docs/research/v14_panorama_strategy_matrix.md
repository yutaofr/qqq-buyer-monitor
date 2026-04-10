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

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | posterior_vs_benchmark_process | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | stable_vs_benchmark_regime | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9287606925374816 | -0.2280783934949524 | 0.7240597665696947 | 0.02904220242427177 | 0.6842816151700717 | 0.8749034749034749 | 0.20098093459998043 | 0.23077117598362631 | 0.0719111969111969 | 0.8664062475411152 | 0.1273269482498208 | 0.3918918918918919 | 0.7240597665696947 | 0.20098093459998043 | 0.0719111969111969 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.8105911151342551 | 0.6665823236175658 | 0.14245537106331185 | 0.9177245311669072 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2854897727439543 | -0.23996028587003093 | 0.6573424208214034 | 0.03356060395955644 | 0.5942777487972687 | 0.8749034749034749 | 0.24884053829525493 | 0.30324904053218077 | 0.11245173745173745 | 0.8664062475411152 | 0.1273269482498208 | 0.3918918918918919 | 0.7240597665696947 | 0.20098093459998043 | 0.0719111969111969 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.8105911151342551 | 0.6665823236175658 | 0.14245537106331185 | 0.9177245311669072 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.4107480827303873 | -0.22807839349495318 | 0.6783913206093278 | 0.03195501918706017 | 0.6124854221604803 | 0.8749034749034749 | 0.2325274665698627 | 0.28558700274676374 | 0.1027992277992278 | 0.8664062475411152 | 0.1273269482498208 | 0.3918918918918919 | 0.7240597665696947 | 0.20098093459998043 | 0.0719111969111969 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.8105911151342551 | 0.6665823236175658 | 0.14245537106331185 | 0.9177245311669072 | False | Process Distortion | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.3952751064198994 | -0.32631024081784277 | 0.7556634181917339 | 0.047802283252338734 | 0.639207283287152 | 0.8749034749034749 | 0.2817631473210413 | 0.33670300973905876 | 0.10183397683397684 | 0.8664062475411152 | 0.1273269482498208 | 0.3918918918918919 | 0.7240597665696947 | 0.20098093459998043 | 0.0719111969111969 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.8105911151342551 | 0.6665823236175658 | 0.14245537106331185 | 0.9177245311669072 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-03` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `50.85%`
- Posterior Brier: `0.7313`
- Mean Entropy: `0.5563`
- Posterior Process vs Benchmark: `81.81%`
- Execution-Stable vs Benchmark: `81.81%`
- Probability Within Band: `56.44%`
- Delta Within Band: `83.18%`
- Acceleration Within Band: `85.25%`
- Transition Probability Within Band: `94.07%`
- Entropy Within Band: `63.42%`
- Raw Beta vs Expectation MAE: `0.1425`
- Target Beta vs Expectation MAE: `0.2233`
- Deployment Exact Match: `51.69%`
- Deployment Rank Error: `0.6479`
- Deployment Pacing Abs Error: `0.4091`
- Deployment Pacing Signed Bias: `-0.0827`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `34.54%`
- Target Beta Within 5pct Of Expected: `5.98%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8664062475411152 | 0.7240597665696947 | 0.7240597665696947 | 0.8749034749034749 | 0.1273269482498208 | 0.20098093459998043 | 0.20098093459998043 |
| s4_sidecar | 0.8664062475411152 | 0.7240597665696947 | 0.6573424208214034 | 0.8749034749034749 | 0.1273269482498208 | 0.20098093459998043 | 0.24884053829525493 |
| s5_tractor | 0.8664062475411152 | 0.7240597665696947 | 0.6783913206093278 | 0.8749034749034749 | 0.1273269482498208 | 0.20098093459998043 | 0.2325274665698627 |
| s4s5_panorama | 0.8664062475411152 | 0.7240597665696947 | 0.7556634181917339 | 0.8749034749034749 | 0.1273269482498208 | 0.20098093459998043 | 0.2817631473210413 |

## Conditional Process Gate Lens

| scenario | acceptance_pass | acceptance_reason | posterior_vs_benchmark_process | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | transition_entropy_within_band_share |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | True | PASS | 0.8105911151342551 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.6665823236175658 | 0.9177245311669072 |
| s4_sidecar | False | Drawdown Regression | 0.8105911151342551 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.6665823236175658 | 0.9177245311669072 |
| s5_tractor | False | Process Distortion | 0.8105911151342551 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.6665823236175658 | 0.9177245311669072 |
| s4s5_panorama | False | Drawdown Regression | 0.8105911151342551 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.6665823236175658 | 0.9177245311669072 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `0.8893`
- Calibration Max Drawdown: `-0.1067`
- Calibration Left-Tail Beta: `0.7081`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | posterior_vs_benchmark_process | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | stable_vs_benchmark_regime | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9287606925374816 | -0.2280783934949524 | 0.7240597665696947 | 0.02904220242427177 | 0.6842816151700717 | 0.8749034749034749 | 0.20098093459998043 | 0.23077117598362631 | 0.0719111969111969 | 0.8664062475411152 | 0.1273269482498208 | 0.3918918918918919 | 0.7240597665696947 | 0.20098093459998043 | 0.0719111969111969 | 0.8105911151342551 | 0.5599973759632428 | 0.8662854393288574 | 0.9437438886334071 | 0.9305587077891208 | 0.8105911151342551 | 0.6665823236175658 | 0.14245537106331185 | 0.9177245311669072 | True | PASS | 0.2 | 0.15 | 0.05 | False |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5026`, mean `0.7241`, below-floor share `0.00%`).
