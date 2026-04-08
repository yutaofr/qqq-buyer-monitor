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

## 2026-04-08 Eight-Year Review

An extended review window was generated to mirror the existing 8-year four-panel regime study and test whether the shadow line should actually replace the live regime path.

- Review window:
  - train cutoff: `2017-12-31`
  - evaluation: `2018-01-01` to `2026-04-02`
- Artifacts:
  - `artifacts/recovery_hmm_shadow/review_8yr/recovery_hmm_8yr_four_panel.png`
  - `artifacts/recovery_hmm_shadow/review_8yr/review.md`
  - `artifacts/recovery_hmm_shadow/review_8yr/review_summary.json`
- Result:
  - `decision = DO_NOT_LIVE_INTEGRATE_YET`

Performance snapshot:

- Shadow:
  - `total_return = 1.7031`
  - `cagr = 0.1357`
  - `max_drawdown = -0.2462`
  - `sharpe = 0.8568`
- Production beta replay:
  - `total_return = 1.7613`
  - `cagr = 0.1388`
  - `max_drawdown = -0.2372`
  - `sharpe = 0.8619`
- `2022 Q1` weight min/avg/max:
  - `0.5000 / 0.7060 / 1.0000`
- `2023 Q1` weight min/avg/max:
  - `0.5000 / 0.5874 / 1.0000`

Interpretation:

- The shadow line passes the narrow `2022-2024` feasibility gate, but fails the broader 8-year promotion gate.
- Relative to the current production beta replay, the shadow line is still too slow to compress risk in `2022 Q1` and too reluctant to re-risk in `2023 Q1`.
- The shadow line also underperforms the current production replay on both total return and Sharpe over the full review horizon.
- Therefore the correct status is:
  - keep `recovery_hmm_shadow` in diagnostics and research artifacts
  - do not wire it into live execution yet

## 2026-04-08 Five-Variant Panorama

To evaluate future optimization directions without violating the current worldview contract, five bounded variants were tested on the same 8-year window and the same `0.5` production floor:

- `stress_hardened`
- `recovery_accelerated`
- `orthogonal_consensus`
- `barbell_balance`
- `fdas_guardrail`

Artifacts:

- `artifacts/recovery_hmm_shadow/variant_panorama_8yr/variant_matrix.csv`
- `artifacts/recovery_hmm_shadow/variant_panorama_8yr/variant_report.md`
- `artifacts/recovery_hmm_shadow/variant_panorama_8yr/variant_nav_8yr.png`
- per-variant four-panel plots under `artifacts/recovery_hmm_shadow/variant_panorama_8yr/<variant>/`

Ranking summary:

- `recovery_accelerated`
  - `total_return = 2.1803`
  - `sharpe = 0.9062`
  - `2022 Q1 avg_weight = 0.7710`
  - `2023 Q1 avg_weight = 0.8160`
  - verdict: fails only because defense is too late in `2022 Q1`
- `orthogonal_consensus`
  - `total_return = 1.8103`
  - `sharpe = 0.8645`
  - `2022 Q1 avg_weight = 0.7164`
  - `2023 Q1 avg_weight = 0.6771`
  - verdict: still misses both defense and release thresholds
- `barbell_balance`
  - `total_return = 1.7303`
  - `sharpe = 0.8509`
  - verdict: no longer beats production and still misses both critical windows
- `stress_hardened`
  - `total_return = 1.5657`
  - `sharpe = 0.8519`
  - `2022 Q1 avg_weight = 0.6596`
  - `2023 Q1 avg_weight = 0.5000`
  - verdict: closest to fixing defense, but it kills recovery release
- `fdas_guardrail`
  - `total_return = 1.4609`
  - `sharpe = 0.8104`
  - `2022 Q1 avg_weight = 0.6102`
  - `2023 Q1 avg_weight = 0.5874`
  - verdict: strongest protection, but too expensive in return and still too slow to re-risk

Conclusion:

- Best performer: `recovery_accelerated`
- Promotion gate result: `KEEP_SHADOW_ONLY_AND_CONTINUE_RESEARCH`
- Why no live integration:
  - fast-release variants improve full-period return, but they become too tolerant in `2022 Q1`
  - hard-defense variants reduce `2022` weight, but they suppress `2023` release too much
  - the unresolved problem is no longer simple threshold tuning; it is the lack of a state path that defends earlier without trapping the system in post-crisis ambiguity
