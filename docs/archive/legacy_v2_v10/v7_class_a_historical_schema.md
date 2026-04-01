# v7.0 Class A Historical Macro Schema

This document defines the canonical research dataset consumed by the v7.0 Phase A historical macro pipeline.

## Required Columns

- `observation_date`
- `effective_date`
- `credit_spread_bps`
- `credit_acceleration_pct_10d`
- `real_yield_10y_pct`
- `net_liquidity_usd_bn`
- `liquidity_roc_pct_4w`
- `funding_stress_flag`
- `source_credit_spread`
- `source_real_yield`
- `source_net_liquidity`
- `source_funding_stress`
- `build_version`

## Validation Rules

- `observation_date` and `effective_date` must parse as datetimes.
- `effective_date` must be greater than or equal to `observation_date` for every row.
- `funding_stress_flag` may only contain `0`, `1`, `True`, `False`, or null.
- Numeric research columns must be numeric or null.
- Missing required columns are a hard validation failure.

## Coverage Summary

The contract exposes a lightweight coverage summary for research and smoke tests:

- row count
- first and last observation dates
- per-column non-null coverage ratio

This schema is intentionally narrow. It covers Class A features only and does not include Class B overlays or placeholder proxy fields.
