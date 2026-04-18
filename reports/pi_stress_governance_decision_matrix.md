# pi_stress Governance Decision Matrix

## Decision Taxonomy

| Layer | Verdict |
|---|---|
| Posterior Model Acceptance | `PASS` |
| Legacy 0.50 Fixed-Threshold Policy Acceptance | `FAIL` |
| Deployment Policy Acceptance | `CONDITIONAL PASS` |
| Production Merge Recommendation | `CONDITIONAL PRODUCTION REVIEW` |

## Posterior Quality

| Metric | Baseline | Selected |
|---|---:|---:|
| Brier | 0.0971 | 0.0709 |
| ECE | 0.0870 | 0.0253 |
| AUC / rank AUC | 0.9180 | 0.9413 |
| Mean gap | 0.3439 | 0.6111 |

These are posterior improvements. They are not created by changing the operational threshold.

## Policy Threshold Comparison

| Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 0.6597 | 0.8629 | 0.7477 | 0.1320 | 0.2992 | 0.8095 |
| 0.35 | 0.6597 | 0.8629 | 0.7477 | 0.1320 | 0.2992 | 0.8095 |
| 0.50 | 0.9655 | 0.5907 | 0.7330 | 0.0063 | 0.1400 | 0.2857 |

The recall restoration around 0.25-0.35 is a policy-layer effect. It must not be reported as a posterior-model improvement.

## Window-Level Policy Behavior

| Window | Threshold | Average pi_stress | Fraction Above Threshold | Precision | Recall | F1 | FPR | Predicted Positive Rate | Episode Capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jul-Oct 2023 | 0.25 | 0.1369 | 0.0588 | 0.0000 | 0.0000 | 0.0000 | 0.0625 | 0.0588 | 0.0000 |
| Jul-Oct 2023 | 0.35 | 0.1369 | 0.0588 | 0.0000 | 0.0000 | 0.0000 | 0.0625 | 0.0588 | 0.0000 |
| Jul-Oct 2023 | 0.50 | 0.1369 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 2022 H1 | 0.25 | 0.6071 | 0.8790 | 0.8165 | 0.9780 | 0.8900 | 0.6061 | 0.8790 | 1.0000 |
| 2022 H1 | 0.35 | 0.6071 | 0.8790 | 0.8165 | 0.9780 | 0.8900 | 0.6061 | 0.8790 | 1.0000 |
| 2022 H1 | 0.50 | 0.6071 | 0.3468 | 0.9302 | 0.4396 | 0.5970 | 0.0909 | 0.3468 | 0.1667 |
| 2020 COVID | 0.25 | 0.6042 | 0.8077 | 0.9048 | 0.9268 | 0.9157 | 0.3636 | 0.8077 | 1.0000 |
| 2020 COVID | 0.35 | 0.6042 | 0.8077 | 0.9048 | 0.9268 | 0.9157 | 0.3636 | 0.8077 | 1.0000 |
| 2020 COVID | 0.50 | 0.6042 | 0.4231 | 1.0000 | 0.5366 | 0.6984 | 0.0000 | 0.4231 | 1.0000 |
| 2018 Q1 ordinary correction | 0.25 | 0.1922 | 0.2923 | 0.0000 | 0.0000 | 0.0000 | 0.3654 | 0.2923 | 0.0000 |
| 2018 Q1 ordinary correction | 0.35 | 0.1922 | 0.2923 | 0.0000 | 0.0000 | 0.0000 | 0.3654 | 0.2923 | 0.0000 |
| 2018 Q1 ordinary correction | 0.50 | 0.1922 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 2020 Q2-Q3 recovery | 0.25 | 0.2446 | 0.2992 | 0.4474 | 0.8947 | 0.5965 | 0.1944 | 0.2992 | 0.5000 |
| 2020 Q2-Q3 recovery | 0.35 | 0.2446 | 0.2992 | 0.4474 | 0.8947 | 0.5965 | 0.1944 | 0.2992 | 0.5000 |
| 2020 Q2-Q3 recovery | 0.50 | 0.2446 | 0.0630 | 1.0000 | 0.4211 | 0.5926 | 0.0000 | 0.0630 | 0.5000 |

## Non-Improved Items

- Legacy 0.50 still under-captures 2022 H1.
- Downstream raw beta delta is not repaired here.
- Proxy-label mismatch may inflate apparent false positives in stressed windows.
