# Final SRD Computation Integrity Gate

## Downstream Allocation Allowed
`True`

| Target | Credibility | Rationale |
| --- | --- | --- |
| structural non-defendability evidence | `COMPUTATIONALLY_TRUSTWORTHY` | recomputed from QQQ open/close gaps, event windows, and policy counterfactual logic |
| event-class defense boundary outputs | `COMPUTATIONALLY_TRUSTWORTHY` | recomputed from event-window gap shares, drawdowns, and loss metrics |
| hybrid transfer decomposition | `COMPUTATIONALLY_TRUSTWORTHY` | recomputed from deterministic stress proxy and executable policy-return attribution |
| gear-shift signal quality | `PARTIALLY_COMPUTATIONALLY_TRUSTWORTHY` | recomputed from price-derived stress proxy; bounded because it is not the production posterior |
| event-class loss contribution | `COMPUTATIONALLY_TRUSTWORTHY` | recomputed from QQQ price losses, tail losses, and drawdown contributions |
| residual protection objective metrics | `COMPUTATIONALLY_TRUSTWORTHY` | derived from rebuilt structural boundary and rebuilt loss contribution |
| convex overlay feasibility metrics | `ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH` | no option-chain, volatility-surface, carry, or execution model was rebuilt in this phase |
| kill-criterion metric used in later prioritization | `PARTIALLY_COMPUTATIONALLY_TRUSTWORTHY` | gap share, drawdown, and signal-flapping metrics are recomputed; prior Phase 5 kill criteria remain artifact-level |
