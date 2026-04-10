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

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9260873084445418 | -0.22807849114242829 | 0.7237605291077005 | 0.02898240500820251 | 0.6836114563046886 | 0.8749034749034749 | 0.20110481649316458 | 0.23085740484621262 | 0.07046332046332046 | 0.8665596809275 | 0.1275424942136147 | 0.38658301158301156 | 0.7237605291077005 | 0.20110481649316458 | 0.07046332046332046 | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.14357943741908796 | 0.9135297004392505 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 2072.0 | 1.2835573922197936 | -0.23996049807870545 | 0.657138617737586 | 0.03349197240839376 | 0.5941622506718397 | 0.8749034749034749 | 0.24888810480327891 | 0.3032913084453388 | 0.11245173745173745 | 0.8665596809275 | 0.1275424942136147 | 0.38658301158301156 | 0.7237605291077005 | 0.20110481649316458 | 0.07046332046332046 | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.14357943741908796 | 0.9135297004392505 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 2072.0 | 1.4093408839073627 | -0.22807849114242806 | 0.6780794671119393 | 0.03186514979280877 | 0.6116858447670178 | 0.8749034749034749 | 0.23267171124822505 | 0.28565631917266116 | 0.10135135135135136 | 0.8665596809275 | 0.1275424942136147 | 0.38658301158301156 | 0.7237605291077005 | 0.20110481649316458 | 0.07046332046332046 | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.14357943741908796 | 0.9135297004392505 | False | Process Distortion | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 2072.0 | 1.397031128370212 | -0.32631041113575565 | 0.7555673612311027 | 0.04777794006138875 | 0.6390911467459277 | 0.8749034749034749 | 0.28170314739991975 | 0.3366775682423573 | 0.10183397683397684 | 0.8665596809275 | 0.1275424942136147 | 0.38658301158301156 | 0.7237605291077005 | 0.20110481649316458 | 0.07046332046332046 | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.14357943741908796 | 0.9135297004392505 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-03` onward
- Effective Evaluation Start: `2013-01-30`
- Posterior Top-1 Accuracy: `50.97%`
- Posterior Brier: `0.7312`
- Mean Entropy: `0.5575`
- Stable vs Benchmark Regime: `82.06%`
- Probability Within Band: `56.81%`
- Delta Within Band: `83.42%`
- Acceleration Within Band: `85.51%`
- Transition Probability Within Band: `94.16%`
- Entropy Within Band: `63.06%`
- Raw Beta vs Expectation MAE: `0.1417`
- Target Beta vs Expectation MAE: `0.2231`
- Deployment Exact Match: `52.11%`
- Deployment Rank Error: `0.6395`
- Deployment Pacing Abs Error: `0.4031`
- Deployment Pacing Signed Bias: `-0.0839`
- Raw Beta Min: `0.5149`
- Beta Expectation Min: `0.5149`
- Target Beta Min: `0.5001`
- Raw Beta Within 5pct Of Expected: `34.33%`
- Target Beta Within 5pct Of Expected: `5.89%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `0.00%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8665596809275 | 0.7237605291077005 | 0.7237605291077005 | 0.8749034749034749 | 0.1275424942136147 | 0.20110481649316458 | 0.20110481649316458 |
| s4_sidecar | 0.8665596809275 | 0.7237605291077005 | 0.657138617737586 | 0.8749034749034749 | 0.1275424942136147 | 0.20110481649316458 | 0.24888810480327891 |
| s5_tractor | 0.8665596809275 | 0.7237605291077005 | 0.6780794671119393 | 0.8749034749034749 | 0.1275424942136147 | 0.20110481649316458 | 0.23267171124822505 |
| s4s5_panorama | 0.8665596809275 | 0.7237605291077005 | 0.7555673612311027 | 0.8749034749034749 | 0.1275424942136147 | 0.20110481649316458 | 0.28170314739991975 |

## Conditional Process Gate Lens

| scenario | acceptance_pass | acceptance_reason | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | transition_entropy_within_band_share |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | True | PASS | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.9135297004392505 |
| s4_sidecar | False | Drawdown Regression | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.9135297004392505 |
| s5_tractor | False | Process Distortion | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.9135297004392505 |
| s4s5_panorama | False | Drawdown Regression | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.9135297004392505 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `0.8909`
- Calibration Max Drawdown: `-0.1067`
- Calibration Left-Tail Beta: `0.7089`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | stable_vs_benchmark_regime | probability_within_band_share | delta_within_band_share | acceleration_within_band_share | transition_probability_within_band_share | entropy_within_band_share | entropy_mae | transition_entropy_within_band_share | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold | selection_failed_closed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 2072.0 | 1.9260873084445418 | -0.22807849114242829 | 0.7237605291077005 | 0.02898240500820251 | 0.6836114563046886 | 0.8749034749034749 | 0.20110481649316458 | 0.23085740484621262 | 0.07046332046332046 | 0.8665596809275 | 0.1275424942136147 | 0.38658301158301156 | 0.7237605291077005 | 0.20110481649316458 | 0.07046332046332046 | 0.8116709753766167 | 0.5625934413395154 | 0.8676426577850933 | 0.9438662545201948 | 0.9315634715125881 | 0.6643439094650685 | 0.14357943741908796 | 0.9135297004392505 | True | PASS | 0.2 | 0.15 | 0.05 | False |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.5026`, mean `0.7238`, below-floor share `0.00%`).
