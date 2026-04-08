# 2026-04-08 Stabilizer Release Forensics

## Scope

This study isolates why `stable_regime` continues to lag the worldview benchmark through the `2023_RECOVERY` window even after:

- release-aware `BUST/LATE -> RECOVERY` stabilizer routing
- transition-aware `price_topology`
- repair-confirmed `RECOVERY` posterior-path correction

Artifacts:

- `artifacts/stabilizer_release_forensics/mainline_2023_recovery/summary.json`
- `artifacts/stabilizer_release_forensics/mainline_2023_recovery/failure_rows.csv`
- `artifacts/stabilizer_release_forensics/mainline_2023_recovery/report.md`

## Method

The forensic pipeline merges:

- canonical `mainline_merged.csv` from the regime-process panorama
- canonical `forensic_trace.jsonl` from the mainline backtest
- flattened `price_topology` diagnostics
- flattened `regime_stabilizer` diagnostics

Failure rows are defined as:

- `benchmark_regime == RECOVERY`
- `stable_regime != RECOVERY`

Each failure row is classified into one root cause bucket:

- `posterior_trapped_in_bust`
- `recovery_acceleration_fade`
- `stabilizer_barrier_hold`
- `topology_not_confirmed`
- `unclassified_release_failure`

## Results

Window: `2023-01-01` to `2023-06-30`

- failure rows: `46`
- raw recovery share: `39.13%`
- mean barrier gap: `0.5410`

Root causes:

- `posterior_trapped_in_bust`: `14`
- `recovery_acceleration_fade`: `14`
- `stabilizer_barrier_hold`: `10`
- `topology_not_confirmed`: `5`
- `unclassified_release_failure`: `3`

Interpretation:

1. Stabilizer thresholding is not the dominant blocker.
2. The largest problem set is upstream of the stable-state switch:
   - either `RECOVERY` posterior mass is still trapped under `BUST`
   - or `RECOVERY` momentum fades too quickly after the first lift
3. Bearish divergence is not currently the limiting factor in this window; representative failure rows showed it near zero.

## Rejected Variant

A follow-up stabilizer experiment retained partial release evidence through mild recovery fades.

Result:

- unit tests could be made internally consistent
- canonical `2023_RECOVERY stable_vs_benchmark_regime` did not improve beyond `61.95%`
- root-cause counts stayed unchanged

Decision:

- do not promote evidence-retention logic into mainline
- keep the mainline stabilizer on the previously accepted release-aware routing

## Next Direction

The next justified optimization target is not `stabilizer barrier` tuning.

It is one of these two:

1. `posterior_trapped_in_bust`
   - refine the pairwise `BUST/LATE -> RECOVERY` uplift capacity
   - but only in windows where topology confidence is not trivially low

2. `recovery_acceleration_fade`
   - add `repair persistence` on the posterior-path side, not the stable-state side
   - specifically for cases where recovery remains dominant over bust but second derivative turns slightly negative

Operationally, the next round should start from the forensic buckets above, not from new stabilizer heuristics.
