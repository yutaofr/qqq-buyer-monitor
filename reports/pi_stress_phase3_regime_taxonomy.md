# pi_stress Phase 3 Regime Taxonomy

## Purpose

Phase 3 treats the prior failure as a representation question. The taxonomy separates economically distinct states before any posterior-family comparison.

## Classes

| Class | Definition |
|---|---|
| `normal` | No material price damage, no persistent market confirmation, and no active healing state. |
| `ordinary_correction` | Moderate drawdown or volatility correction without systemic confirmation or persistent stress occupancy. |
| `elevated_structural_stress` | Persistent drawdown/late-cycle or bust pressure with market-internal confirmation, but not acute crash dynamics. |
| `systemic_crisis` | Acute crash state with fast price damage, volatility shock, and crisis-window confirmation. |
| `recovery_healing` | Post-stress repair regime where rebound and recovery impulse are present but residual scars can remain. |
| `transition_onset` | Optional fuzzy onset state for high transition intensity before clean structural-stress confirmation. |

## Label Construction

The labels are proxy research labels. They combine price drawdown topology, volatility shock, transition intensity, recovery impulse, and explicit historical windows. They are not conductor rules.

## Ambiguity Zones

- Total ambiguous rows: `754`
- Ambiguous fraction: `0.3639`
- Zone counts: `{'ordinary_vs_structural_boundary': 353, 'stress_vs_healing_overlap': 279, 'transition_band': 116, 'macro_price_disagreement': 151}`

## Required Episodes

| Window | Dominant label | Rows | Label mix |
|---|---:|---:|---|
| ordinary_correction_2018_q1 | ordinary_correction | 65 | {'ordinary_correction': 54, 'transition_onset': 11} |
| ordinary_correction_2018_q4 | ordinary_correction | 59 | {'elevated_structural_stress': 15, 'ordinary_correction': 29, 'systemic_crisis': 2, 'transition_onset': 13} |
| systemic_crisis_2020_covid | systemic_crisis | 52 | {'systemic_crisis': 52} |
| recovery_2020_q2_q3 | recovery_healing | 127 | {'elevated_structural_stress': 44, 'recovery_healing': 62, 'systemic_crisis': 21} |
| elevated_structural_stress_2022_h1 | elevated_structural_stress | 124 | {'elevated_structural_stress': 79, 'systemic_crisis': 45} |
| recovery_2022_h2 | elevated_structural_stress | 127 | {'elevated_structural_stress': 108, 'systemic_crisis': 19} |
| ordinary_correction_2023_jul_oct | elevated_structural_stress | 85 | {'elevated_structural_stress': 41, 'ordinary_correction': 39, 'transition_onset': 5} |
| ordinary_correction_2025_spring | ordinary_correction | 72 | {'elevated_structural_stress': 21, 'ordinary_correction': 34, 'recovery_healing': 4, 'systemic_crisis': 3, 'transition_onset': 10} |

## Audit Finding

The prior binary proxy collapses ordinary corrections, structural stress, acute crash, and recovery scars into one stress/non-stress target.
