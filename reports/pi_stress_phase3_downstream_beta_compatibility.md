# pi_stress Phase 3 Downstream Beta Compatibility

## Research Question

Can a stress posterior be preferred not only for stress discrimination, but also for safer downstream hedge behavior?

## Ranking Integration

`included_in_candidate_ranking`

## Candidate Metrics

| Candidate | Non-stress high-beta trigger rate | Worsening overlap | Worst raw beta delta | Mean raw beta delta | Pathology incidence change |
|---|---:|---:|---:|---:|---:|
| `C9_baseline_reference` | 0.0042 | 0 | 0.0000 | 0.0000 | -0.0627 |
| `multiclass_regime_posterior` | 0.0692 | 48 | -1.1798 | -0.6681 | -0.0164 |
| `hierarchical_stress_posterior` | 0.0010 | 1 | -0.8954 | -0.8954 | -0.0656 |
| `two_stage_anomaly_severity` | 0.0304 | 29 | -1.1798 | -0.8705 | -0.0478 |
| `ordinal_state_transition_posterior` | 0.0189 | 18 | -1.0319 | -0.9207 | -0.0502 |

## Screening Rule

Candidate materially increases high-beta non-stress trigger rate or beta-pathology incidence versus legacy without offsetting structural separation improvement.
