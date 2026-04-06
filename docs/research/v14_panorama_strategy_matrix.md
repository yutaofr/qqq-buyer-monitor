# v14 Panorama Strategy Matrix

## Protocol

- Diagnostics Vintage Mode: `ALFRED+PIT_FALLBACK`
- Calibration Window: `2011-01-01` to `2017-12-29`
- Holdout Window: `2021-01-01` onward
- Mainline Trace: `run_v11_audit()` canonical execution trace
- Detector Trace: `scripts/baseline_backtest.py` canonical PIT-safe OOS diagnostics
- Acceptance: no worse max drawdown, no worse left-tail beta, bounded turnover drift

## Default Threshold Holdout

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 1314.0 | 0.6034548862387505 | -0.2517744004547835 | 0.7068823203722022 | 0.0001209064398115345 | 0.7000190298076264 | 0.9279299847793 | 0.23889149424043546 | 0.25252792344660113 | 0.0 | 0.8603567856665256 | 0.0962565744801446 | 0.21080669710806696 | 0.7068823203722022 | 0.23889149424043546 | 0.0 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4_sidecar | 1314.0 | 0.4183696377367354 | -0.27084108093115455 | 0.6520799553589872 | 0.014260711958619103 | 0.6183780478108193 | 0.9279299847793 | 0.2778326771795724 | 0.3030165606237468 | 0.0426179604261796 | 0.8603567856665256 | 0.0962565744801446 | 0.21080669710806696 | 0.7068823203722022 | 0.23889149424043546 | 0.0 | False | Drawdown Regression | 0.25 | 0.2 | 0.1 |
| s5_tractor | 1314.0 | 0.5309806232851688 | -0.2517744004547835 | 0.6906911259567086 | 0.006165004450095972 | 0.6802123451079193 | 0.9279299847793 | 0.25508268865592904 | 0.2753861310286376 | 0.0 | 0.8603567856665256 | 0.0962565744801446 | 0.21080669710806696 | 0.7068823203722022 | 0.23889149424043546 | 0.0 | True | PASS | 0.25 | 0.2 | 0.1 |
| s4s5_panorama | 1314.0 | 0.4358218236331355 | -0.3474705303678429 | 0.7845287469247992 | 0.040298239052393915 | 0.7103259777307314 | 0.9279299847793 | 0.285642637516348 | 0.31104513736611206 | 0.0426179604261796 | 0.8603567856665256 | 0.0962565744801446 | 0.21080669710806696 | 0.7068823203722022 | 0.23889149424043546 | 0.0 | False | Defensive Violation | 0.25 | 0.2 | 0.1 |

## Mainline Bayesian Audit

- Mainline Audit Window: `2011-01-01` onward
- Posterior Top-1 Accuracy: `64.58%`
- Posterior Brier: `0.5670`
- Mean Entropy: `0.6674`
- Raw Beta vs Expectation MAE: `0.1501`
- Target Beta vs Expectation MAE: `0.2523`
- Deployment Exact Match: `53.77%`
- Deployment Rank Error: `0.7682`
- Deployment Pacing Abs Error: `0.4602`
- Deployment Pacing Signed Bias: `-0.3070`
- Raw Beta Min: `0.5000`
- Beta Expectation Min: `0.5000`
- Target Beta Min: `0.5000`
- Raw Beta Within 5pct Of Expected: `22.87%`
- Target Beta Within 5pct Of Expected: `9.76%`
- Target Floor Breach Rate: `0.00%`
- Share At Floor: `17.98%`

## Beta Fidelity Lens

- `mean_raw_beta`: posterior expectation surface before entropy haircut, overlay, and smoothing.
- `mean_standard_beta`: mainline production target beta after the full execution stack.
- `mean_scenario_beta`: S4/S5-adjusted effective beta used for the scenario replay.
- `mean_expected_beta`: regime-policy beta implied by the realized regime label.

| scenario | mean_raw_beta | mean_standard_beta | mean_scenario_beta | mean_expected_beta | raw_beta_expected_mae | standard_beta_expected_mae | scenario_beta_expected_mae |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 0.8603567856665256 | 0.7068823203722022 | 0.7068823203722022 | 0.9279299847793 | 0.0962565744801446 | 0.23889149424043546 | 0.23889149424043546 |
| s4_sidecar | 0.8603567856665256 | 0.7068823203722022 | 0.6520799553589872 | 0.9279299847793 | 0.0962565744801446 | 0.23889149424043546 | 0.2778326771795724 |
| s5_tractor | 0.8603567856665256 | 0.7068823203722022 | 0.6906911259567086 | 0.9279299847793 | 0.0962565744801446 | 0.23889149424043546 | 0.25508268865592904 |
| s4s5_panorama | 0.8603567856665256 | 0.7068823203722022 | 0.7845287469247992 | 0.9279299847793 | 0.0962565744801446 | 0.23889149424043546 | 0.285642637516348 |

## Calibration Winner

- Scenario: `standard`
- Tractor Threshold: `0.20`
- Sidecar Threshold: `0.15`
- Calm Threshold: `0.05`
- Calibration Return: `2.6787`
- Calibration Max Drawdown: `-0.2102`
- Calibration Left-Tail Beta: `0.6273`

## Holdout Result Of Frozen Winner

| scenario | rows | approx_total_return | approx_max_drawdown | mean_target_beta | mean_turnover | left_tail_mean_beta | mean_expected_beta | beta_expectation_mae | beta_expectation_rmse | beta_expectation_within_5pct | mean_raw_beta | raw_beta_expected_mae | raw_beta_expected_within_5pct | mean_standard_beta | standard_beta_expected_mae | standard_beta_expected_within_5pct | acceptance_pass | acceptance_reason | tractor_threshold | sidecar_threshold | calm_threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| standard | 1314.0 | 0.6034548862387505 | -0.2517744004547835 | 0.7068823203722022 | 0.0001209064398115345 | 0.7000190298076264 | 0.9279299847793 | 0.23889149424043546 | 0.25252792344660113 | 0.0 | 0.8603567856665256 | 0.0962565744801446 | 0.21080669710806696 | 0.7068823203722022 | 0.23889149424043546 | 0.0 | True | PASS | 0.2 | 0.15 | 0.05 |

## Production Recommendation

- Promote `standard` with thresholds `tractor=0.20`, `sidecar=0.15`, `calm=0.05`.
- Structural note: the mainline holdout trace now stays above the `0.5x` floor (min `0.6861`, mean `0.7069`, below-floor share `0.00%`).
