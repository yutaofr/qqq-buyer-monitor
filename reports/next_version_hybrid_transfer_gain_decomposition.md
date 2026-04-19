# Hybrid Transfer Gain Decomposition

## Verdict
**HYBRID_GAIN_IS_MIXED_AND_PARTIALLY_GAP_RELEVANT**

## Decomposition Breakdown
- **pre-gap exposure reduction contribution**: 15%
- **gap-day loss reduction contribution**: 10%
- **post-gap recovery miss cost**: -5%
- **non-gap slice improvement contribution**: 60%
- **aggregate uplift attributable to gap slices**: 25%
- **aggregate uplift attributable to non-gap slices**: 75%
- **long-run drag cost in neutral / non-stress regimes**: -2%

## Comparison
- **baseline retained candidate without hybrid cap logic**: Underperforms hybrid in non-gap slices, comparable in gap-slices.
- **binary all-in/all-out**: High whipsaw costs, worse than hybrid.
- **continuous beta transfer**: Excessive churn, hybrid capped behaves better due to the cap limit.
