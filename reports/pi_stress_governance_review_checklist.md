# pi_stress Governance Review Checklist

## One-Vote-Fail Items

| Check | Status | Evidence |
|---|---|---|
| Conclusion language is internally consistent | PASS | Four separate decisions are reported: posterior, legacy 0.50 policy, deployment policy, production recommendation. |
| Threshold adjustment is not presented as model improvement | PASS | Decision matrix separates posterior Brier/ECE/AUC/mean gap from threshold precision/recall/FPR. |
| Threshold policy exists as code/config artifact | PASS | `DeploymentPolicySpec` and `artifacts/pi_stress_governance/policy_matrix.json`. |
| Calibration appendix exists | PASS | `reports/pi_stress_calibration_appendix.md` covers isotonic plateaus, threshold sensitivity, flip frequency, and Platt alternatives. |
| Rollback plan is complete | PASS | Final recommendation and rollout plan define switch, triggers, and restoration path. |
| No raw macro / market hard gates in top-level policy | PASS | Policy uses calibrated pi_stress thresholds only; conductor receives abstract feature history and does not implement raw-feature gates. |

## Mandatory Pass Items

| Check | Status | Evidence |
|---|---|---|
| Posterior Model Acceptance reported | PASS | Final recommendation. |
| Legacy Fixed-Threshold Policy Acceptance reported | FAIL | Final recommendation and decision matrix. |
| Deployment Policy Acceptance reported | CONDITIONAL PASS | Final recommendation and policy spec. |
| Production Merge Recommendation reported | CONDITIONAL PRODUCTION REVIEW | Final recommendation. |
| Posterior vs policy comparison complete | PASS | Decision matrix includes posterior quality and threshold 0.25 / 0.35 / 0.50 policy metrics. |
| Required windows covered | PASS | Jul-Oct 2023, 2022 H1, 2020 COVID, 2018 Q1 ordinary correction, 2020 Q2-Q3 recovery. |
| Required residual risks retained | PASS | 2022 H1 legacy 0.50 miss, beta-surface task, proxy-label mismatch, isotonic plateaus. |
| Rollout plan executable | PASS | Six rollout stages with entry criteria, metrics, exit criteria, and rollback triggers. |
| Monitoring separated by layer | PASS | Posterior drift, policy drift, data drift, calibration drift, FP drift, episode capture, beta pathology. |

## Governance Self-Assessment

The package is review-ready for conditional production review only. It is not an unconditional approval package.
