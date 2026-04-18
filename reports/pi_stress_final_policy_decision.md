# pi_stress Final Policy Decision

## FINAL_POLICY_DECISION

Single evaluated policy: `calibrated_fixed_threshold` at threshold `0.35` with no hysteresis.

The 0.35 threshold is the least bad fixed operating point in the C9+Platt comparison: it repairs 2022 H1 better than legacy 0.50 and keeps Jul-Oct 2023 below the ghost-window tolerance. It is not a deployable operating point because +/-0.10 threshold robustness fails.

| Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture | 2018 Q1 FPR | 2023 Ghost FPR | 2022 H1 Recall | 2020 COVID Recall |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 0.6136 | 0.8776 | 0.7222 | 0.1640 | 0.3272 | 0.8095 | 0.4808 | 0.0625 | 1.0000 | 0.9756 |
| 0.30 | 0.6689 | 0.8439 | 0.7463 | 0.1239 | 0.2886 | 0.7619 | 0.3462 | 0.0500 | 0.9670 | 0.9024 |
| 0.35 | 0.7244 | 0.7764 | 0.7495 | 0.0876 | 0.2452 | 0.6190 | 0.1923 | 0.0250 | 0.9231 | 0.7561 |
| 0.40 | 0.7901 | 0.7068 | 0.7461 | 0.0557 | 0.2046 | 0.6190 | 0.1731 | 0.0125 | 0.7912 | 0.6585 |
| 0.45 | 0.8527 | 0.6350 | 0.7279 | 0.0325 | 0.1704 | 0.4762 | 0.0385 | 0.0125 | 0.5604 | 0.5854 |
