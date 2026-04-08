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

- failure rows: `24`
- raw recovery share: `45.83%`
- mean barrier gap: `0.3657`

Root causes:

- `posterior_trapped_in_bust`: `7`
- `recovery_acceleration_fade`: `7`
- `stabilizer_barrier_hold`: `5`
- `topology_not_confirmed`: `5`

Interpretation:

1. The release-timing fix worked:
   - `stabilizer_barrier_hold` dropped from `11` to `5`
   - total failure rows dropped from `34` to `24`
2. The remaining blockers are now balanced:
   - `posterior_trapped_in_bust = 7`
   - `recovery_acceleration_fade = 7`
   - `topology_not_confirmed = 5`
3. The lower `raw recovery share` is not a regression in this context. It means more rows that previously had `raw_regime = RECOVERY` are no longer stuck in failure at all.

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

The next justified optimization target has changed again.

`stabilizer_barrier_hold` is no longer the first problem to solve.

It is now these two:

1. `posterior_trapped_in_bust`
   - finish the remaining low-confidence entrapment cases without broadening the uplift too much

2. `recovery_acceleration_fade`
   - preserve repair continuity through mild second-derivative pullbacks
   - without reintroducing the old `BUST` entrapment problem

Operationally, the next round should start from the updated forensic buckets above, not from another large release-timing rewrite.
