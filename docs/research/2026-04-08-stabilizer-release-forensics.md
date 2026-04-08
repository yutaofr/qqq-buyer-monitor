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

- failure rows: `34`
- raw recovery share: `58.82%`
- mean barrier gap: `0.5275`

Root causes:

- `posterior_trapped_in_bust`: `7`
- `recovery_acceleration_fade`: `10`
- `stabilizer_barrier_hold`: `11`
- `topology_not_confirmed`: `5`
- `unclassified_release_failure`: `1`

Interpretation:

1. The upstream posterior-path fix worked:
   - `posterior_trapped_in_bust` was cut in half (`14 -> 7`)
   - raw `RECOVERY` share improved from `39.13%` to `58.82%`
2. The dominant blocker is no longer posterior entrapment. It has shifted to:
   - `stabilizer_barrier_hold`
   - `recovery_acceleration_fade`
3. Bearish divergence is still not the limiting factor in this window; representative failure rows remain near zero on that axis.

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

The next justified optimization target has changed.

It is no longer `posterior_trapped_in_bust` first. That bucket has already been materially compressed.

It is now these two, in this order:

1. `stabilizer_barrier_hold`
   - recalibrate release timing on top of the stronger posterior-path
   - but only where topology confidence and repair persistence are already confirmed

2. `recovery_acceleration_fade`
   - preserve repair continuity through mild second-derivative pullbacks
   - without reintroducing the old `BUST` entrapment problem

Operationally, the next round should start from the updated forensic buckets above, not from a fresh amplitude rewrite.
