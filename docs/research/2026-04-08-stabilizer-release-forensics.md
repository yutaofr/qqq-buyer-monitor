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

- failure rows: `17`
- raw recovery share: `41.18%`
- mean barrier gap: `0.3401`

Root causes:

- `posterior_trapped_in_bust`: `8`
- `recovery_acceleration_fade`: `4`
- `stabilizer_barrier_hold`: `3`
- `topology_not_confirmed`: `2`

Interpretation:

1. The new topology tie-break worked in the exact area it targeted:
   - `topology_not_confirmed` dropped from `5` to `2`
   - total failure rows dropped from `18` to `17`
2. The residual problem shifted categories rather than disappearing:
   - `posterior_trapped_in_bust` increased from `6` to `8`
   - this is an improvement in diagnosability, not a free win
   - several dates that were previously failing because topology stayed in `BUST/LATE_CYCLE` are now explicitly recognized as repair windows, but the posterior path still fails to release enough mass
3. The higher `raw recovery share` is directionally good here. More remaining failures now at least have `raw_regime = RECOVERY` before stabilizer or posterior friction blocks full release.

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

1. residual `posterior_trapped_in_bust`
   - this is now the clear first blocker
   - especially the early-February cluster where topology now recognizes repair but posterior mass remains stuck in `BUST`

2. residual `topology_not_confirmed`
   - now only two dates remain: `2023-02-10` and `2023-04-14`

Operationally, the next round should move back to posterior release capacity, not another broad stabilizer rewrite.
