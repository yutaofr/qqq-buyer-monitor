# pi_stress Phase 3 Representation Experiments

## Research Question

Can redesigned component representations separate ordinary correction, structural stress, and systemic crisis more cleanly than C9?

## Compared Stacks

- `C9_baseline`: Existing C9-style structural confirmation using S_price, S_market_v2, S_macro_anom, and S_persist.
- `phase3_price_market_persistence_stack`: Redesigned stack with price damage decomposition, market-internal confirmation, persistence/healing semantics, and macro/liquidity subspace.

## Direct Comparison

| Metric | Value |
|---|---:|
| Ordinary mean delta | 0.072651 |
| Structural mean delta | 0.118783 |
| Systemic mean delta | 0.168449 |
| Recovery mean delta | 0.063124 |
| Separation lift | 0.057535 |

## Interpretation

The redesigned stack changes the latent component surface through price damage decomposition, market-internal confirmation, persistence/healing semantics, and macro/liquidity subspace proxies. This is not an operating-threshold experiment.
