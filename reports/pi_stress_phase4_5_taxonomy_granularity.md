# Phase 4.5 Taxonomy & Granularity Constraint Design

## 1. Phase 3/4 Six-class Taxonomy Audit
The original 6-class taxonomy (normal, ordinary_correction, elevated_structural_stress, systemic_crisis, recovery_healing, transition_onset) was audited against real sample support.

## 2. Ambiguity-Adjusted Support
- **normal**: High support.
- **ordinary_correction**: Moderate support, clean boundaries.
- **elevated_structural_stress**: Low support, massive ambiguity overlap with systemic_crisis and transition_onset.
- **systemic_crisis**: Low count, but distinct.
- **recovery_healing**: Moderate support.
- **transition_onset**: Extremely low support, mathematically indistinguishable from elevated_structural_stress in backtest windows.

## 3. Decision
Due to finite effective sample budget and high ambiguity between structural stress and transition states, the training granularity must be reduced.
We will use a 4-class hierarchical collapse (Normal, Correction, Systemic/Stress, Recovery).

**Verdict**: `TRAIN_AS_REDUCED_HIERARCHY`
