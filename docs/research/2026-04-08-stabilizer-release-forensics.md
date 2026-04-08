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

- failure rows: `18`
- raw recovery share: `38.89%`
- mean barrier gap: `0.4417`

Root causes:

- `posterior_trapped_in_bust`: `6`
- `recovery_acceleration_fade`: `4`
- `stabilizer_barrier_hold`: `3`
- `topology_not_confirmed`: `5`

Interpretation:

1. The latest posterior-path tightening worked:
   - total failure rows dropped from `24` to `18`
   - `stabilizer_barrier_hold` dropped from `5` to `3`
   - `recovery_acceleration_fade` dropped from `7` to `4`
2. The worst `posterior_trapped_in_bust` tail also improved:
   - `posterior_trapped_in_bust = 6`
   - `2023-03-15` is no longer trapped in `BUST`; it now advances to `raw_regime = RECOVERY`
3. The lower `raw recovery share` is still not a regression in this context. It means more failure rows were removed entirely rather than merely being re-labeled inside the failure set.

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

The next justified target has shifted again:

1. `topology_not_confirmed`
   - these are now the single largest unchanged bucket
   - many of them are early-February low-confidence dates where the benchmark is already in `RECOVERY` but topology confidence is still near zero

2. residual `posterior_trapped_in_bust`
   - finish the remaining low-confidence entrapment cases without broadening the uplift too much

Operationally, the next round should start from topology-confidence construction, not from another broad stabilizer rewrite.
