# pi_stress Calibration Appendix

## Isotonic Plateau Risk

The selected candidate uses isotonic calibration. Isotonic is monotone and empirically strong in the current registry, but it can create posterior plateaus. Plateaued posteriors can make threshold-local behavior discontinuous near deployment cuts.

Selected plateau summary:

```json
{
  "largest_plateau_count": 365.0,
  "largest_plateau_fraction": 0.17615830115830117,
  "unique_score_levels": 18.0
}
```

## Calibrator Comparison

| Calibrator | Brier | ECE | Unique Levels | Largest Plateau Fraction | Recommended Threshold | Flip Freq @ 0.25 | Flip Freq @ 0.35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| isotonic | 0.0709 | 0.0253 | 18 | 0.1762 | 0.25 | 0.0343 | 0.0343 |
| platt | 0.0793 | 0.0758 | 2058 | 0.0010 | 0.30 | 0.0401 | 0.0372 |
| weighted_platt | 0.1237 | 0.2049 | 2064 | 0.0010 | 0.50 | 0.0613 | 0.0729 |
| platt_balanced | 0.1006 | 0.1583 | 2065 | 0.0010 | 0.50 | 0.0604 | 0.0507 |

## Threshold-Local Sensitivity

| Threshold | Recall | FPR | F1 | Episode Capture |
|---:|---:|---:|---:|---:|
| 0.20 | 0.8861 | 0.1702 | 0.7204 | 0.8861 |
| 0.25 | 0.8629 | 0.1320 | 0.7477 | 0.8629 |
| 0.30 | 0.8629 | 0.1320 | 0.7477 | 0.8629 |
| 0.35 | 0.8629 | 0.1320 | 0.7477 | 0.8629 |
| 0.40 | 0.8080 | 0.1014 | 0.7517 | 0.8080 |

## Calibration Curve

Detailed calibration-curve bins are stored in `artifacts/pi_stress_governance/policy_matrix.json` under `trace_analysis.calibrator_comparison`.

## Governance Conclusion

Keep isotonic only with deployment caveats. It is acceptable for conditional production review because Brier and ECE improve, but monitoring must explicitly track plateau mass, threshold-local trigger drift, and transition flip frequency. A smoother Platt-family calibrator remains the rollback candidate if isotonic plateaus produce unstable policy behavior. Legacy 0.50 remains a failed sole operating rule for the selected posterior, with 2022 H1 as the explicit under-capture example.
