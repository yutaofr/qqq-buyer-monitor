# Recovery HMM Shadow Readout

This document is reserved for the shadow-only readout of the orthogonalized asymmetric HMM research track.

The decision gate emitted by the audit must be one of:

- `REJECT`
- `SHADOW_ONLY`
- `CANDIDATE_FOR_INTEGRATION`

No result may be treated as production-ready until the audit explicitly demonstrates:

- `2022 Q1` defensive compression
- `2023 Q1` recovery re-acceleration
- no violation of the current production `0.5` floor contract

## 2026-04-08 Local Readiness

The current frozen local dataset is not sufficient to run the full shadow audit under the locked SRD contract.

- Ready-to-map from `data/macro_historical_dump.csv`:
  - `hy_ig_spread` from `credit_spread_bps / 100`
  - `real_yield_10y` from `real_yield_10y_pct * 100`
- Still missing in the frozen local dataset:
  - `chicago_fci`
  - `curve_10y_2y`
  - `ism_new_orders`
  - `ism_inventories`
  - `vix_3m_1m_ratio`
  - `qqq_skew_20d_mean`
- Coverage of mapped fields is also incomplete:
  - `hy_ig_spread`: `0.7972`
  - `real_yield_10y`: `0.6148`

Local readiness artifact:

- `/private/tmp/recovery_hmm_shadow_local_v2/readiness_report.json`

Interpretation:

- The current blocker is a data contract gap, not a failed OOS acceptance result.
- No claim should be made yet about `2022-2024` HMM behavior on real historical inputs until the missing series are frozen locally.

## 2026-04-08 Feasibility Pass

The shadow line has now passed the locked OOS acceptance gate on the real assembled dataset.

- Audit window:
  - train cutoff: `2021-12-31`
  - evaluation: `2022-01-01` to `2024-12-31`
- Result:
  - `q1_2022_below_or_equal_0_5 = true`
  - `q1_2023_above_or_equal_0_85 = true`
  - `decision_gate = CANDIDATE_FOR_INTEGRATION`

Current shadow dataset lineage:

- direct:
  - `hy_ig_spread` from `macro_historical_dump.credit_spread_bps / 100`
  - `real_yield_10y` from `macro_historical_dump.real_yield_10y_pct * 100`
  - `curve_10y_2y` from `FRED:T10Y2Y`
  - `chicago_fci` from `FRED:NFCI`
  - `vix_3m_1m_ratio` from `FRED:VXVCLS / VIXCLS`
- explicit proxies:
  - `ism_new_orders` from `FRED:NEWORDER` 12m pct change
  - `ism_inventories` from `FRED:MNFCTRIMSA` 12m pct change
  - `qqq_skew_20d_mean` from local `QQQ` downside/upside 20d mean ratio

Production comparison against `artifacts/v14_panorama/mainline/execution_trace.csv`:

- `rows_compared = 686`
- `recovery_release_gap = 122`
- `shadow_mean_weight = 0.5989`
- `production_mean_beta = 0.6905`

Interpretation:

- The shadow line now demonstrates the intended 2022 defensive compression and 2023 recovery release.
- The most meaningful divergence versus the production trace is earlier recovery release, not a breach of the `0.5` floor.
- This qualifies the work for formal production-upgrade review, but does not by itself justify mutating the live execution path without that review.
- The accepted candidate is now exported into the production `status.json` diagnostics surface as `diagnostics.recovery_hmm_shadow` for parallel runtime audit.
