# pi_stress Phase 4 Identification Feasibility

## Decision

`FEASIBLE_AS_SPECIFIED`

## Class Support

| Class | Raw rows | Confidence-weighted rows | Episodes | OOS rows | Independent modeling |
|---|---:|---:|---:|---:|---|
| `normal` | 1025 | 1005.3 | 39 | 469 | YES |
| `ordinary_correction` | 295 | 269.9 | 50 | 112 | YES |
| `elevated_structural_stress` | 406 | 365.7 | 30 | 140 | YES |
| `systemic_crisis` | 121 | 118.3 | 9 | 3 | YES |
| `recovery_healing` | 109 | 101.9 | 13 | 34 | YES |
| `transition_onset` | 116 | 103.5 | 26 | 55 | YES |

## Complexity Budget

- Six-class supportable as specified: `YES`
- Maximum Stage 1 complexity: grouped multinomial or ordinal additive model with ambiguity weighting
- Maximum Stage 2 complexity: conditional low-degree additive severity model; systemic/structural split must be reported as weak-sample if episodes remain sparse

## Stage Coupling Conclusion

Stage 1 outputs add stable incremental value beyond duplicated proxy information.
