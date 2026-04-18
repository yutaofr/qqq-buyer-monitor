# pi_stress Repair Final Recommendation

Chosen candidate: `C9_structural_confirmation_isotonic`.

## Layered Decision Taxonomy

- Posterior Model Acceptance: `PASS`
- Legacy Fixed-Threshold Policy Acceptance: `FAIL`
- Deployment Policy Acceptance: `CONDITIONAL PASS`
- Production Merge Recommendation: `CONDITIONAL PRODUCTION REVIEW`

This is not unconditional production approval. The posterior model is acceptable for production review, but the legacy 0.50 trigger fails governance because 2022 H1 remains under-captured at that threshold.

## Basis

- All Brier: baseline `0.0971` vs selected `0.0709`.
- All ECE: baseline `0.0870` vs selected `0.0253`.
- All recall @ 0.50: baseline `0.5338` vs selected `0.5907`.
- OOS false-positive average: baseline `0.1536` vs selected `0.1263`.
- Jul-Oct 2023 average pi_stress: baseline `0.3205` vs selected `0.1369`.
- 2022 H1 selected recall @ 0.50: `0.4396`.

## What Is Fixed

The posterior has better calibration and separation, and the Jul-Oct 2023 ordinary-correction pathology is materially reduced.

## What Is Not Fixed

The legacy 0.50 policy cut remains unsuitable as the sole operational trigger. Beta-surface / raw beta delta behavior remains a downstream separate task. Proxy-label mismatch may make stressed-window false positives look worse than the economic state warrants.

## Required Approval Condition

Production review may proceed only if the deployment policy migrates to the explicit threshold-policy artifact in `artifacts/pi_stress_governance/policy_matrix.json`, with monitoring and rollback gates active.

## Rollback Path

Set stress posterior mode to `legacy_topology` and policy mode to `legacy_fixed_0_50`. Roll back immediately on false-positive inflation, recall degradation, unstable threshold behavior, calibration drift, or worsening downstream beta instability.
