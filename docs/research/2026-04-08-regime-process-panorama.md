# 2026-04-08 Regime Process Panorama

## Mandate

This readout follows the locked regime-process mandate:

- evaluate probabilities as a stochastic process, not just point values
- evaluate first derivative and second derivative alignment
- treat transitions as fuzzy bands, not hard regime flips
- use QQQ price structure, volume structure, and multi-timeframe RSI divergence as the worldview benchmark
- use return and Sharpe only as second-layer validation

## What Changed

### Research benchmark

- `src/research/worldview_benchmark.py`
  - added weekly RSI
  - added monthly RSI
  - added bearish / bullish RSI divergence proxies
  - added transition-intensity scoring
  - added 1-delta lower / upper bands for regime probabilities, momentum, and acceleration

### Main engine

- `src/engine/v11/core/price_topology.py`
  - topology confidence is now transition-aware
  - posterior blend and beta anchor are damped when the benchmark transition band is wide
  - confirmed repair windows now get a dedicated `RECOVERY` posterior-path correction
  - the correction is pairwise: it removes stale `BUST/LATE_CYCLE` mass only when the benchmark shows damage-memory plus repair-impulse confirmation

### Shadow chain

- `src/research/recovery_hmm/audit.py`
  - shadow traces now emit regime probability delta / acceleration / trend columns

### Unified audit

- `src/research/regime_process_audit.py`
- `scripts/run_regime_process_panorama.py`

These compare both production and shadow traces against the same regime-process benchmark.

## Baseline Comparison

Artifacts:

- `artifacts/regime_process_panorama_baseline/summary.json`
- `artifacts/regime_process_panorama_baseline/report.md`

Using the existing production mainline trace versus the best shadow candidate (`recovery_accelerated`):

- Mainline:
  - `stable_vs_benchmark_regime = 67.06%`
  - `probability_within_band_share = 47.05%`
  - `delta_within_band_share = 78.07%`
  - `acceleration_within_band_share = 63.97%`
  - `transition_probability_within_band_share = 63.85%`
- Shadow:
  - `stable_vs_benchmark_regime = 39.85%`
  - `probability_within_band_share = 33.43%`
  - `delta_within_band_share = 57.35%`
  - `acceleration_within_band_share = 39.79%`
  - `transition_probability_within_band_share = 53.39%`

Interpretation:

- Under the new regime-process standard, the current production engine is materially stronger than the current shadow chain.
- The shadow line is not just off on static probabilities; it is also materially off on regime momentum and acceleration.

## Shadow Diagnosis

Comparing `locked_candidate` versus `recovery_accelerated` under the new benchmark:

- `recovery_accelerated` improves:
  - `stable_vs_benchmark_regime`
  - `BUST` probability alignment
  - `BUST` / `RECOVERY` derivative alignment
- but it worsens:
  - `RECOVERY` probability MAE
  - overall probability-within-band share
  - transition probability-within-band share

Interpretation:

- The shadow problem is not only that recovery is released too slowly.
- The deeper issue is that the `RECOVERY` posterior surface itself is still misspecified.
- Simply accelerating release creates a better tactical rebound path but does not make the regime process more truthful.

## Mainline Rebench

Artifacts:

- `artifacts/regime_process_mainline_8yr/full_audit.csv`
- `artifacts/regime_process_panorama_rebench/summary.json`
- `artifacts/regime_process_panorama_rebench/report.md`

After applying the transition-aware `price_topology` change, promoting the accepted `RECOVERY` posterior-path correction, tightening the posterior-path around `posterior_trapped_in_bust` plus `recovery_acceleration_fade`, recalibrating release timing for `stabilizer_barrier_hold`, and then adding a narrow release-credit for mild `BUST` overhangs and mild fade windows, the canonical mainline backtest on `2018-01-01` to `2026-04-07` now reads:

- `stable_vs_benchmark_regime = 72.71%`
- `probability_within_band_share = 51.15%`
- `delta_within_band_share = 73.30%`
- `acceleration_within_band_share = 57.25%`
- `transition_probability_within_band_share = 74.18%`
- `RECOVERY probability_within_band_share = 48.36%`
- `RECOVERY probability_mae = 0.1139`

Compared on the same `2018+` window against the previously promoted mainline:

- stable regime match: `67.83% -> 72.71%`
- probability-within-band: `49.95% -> 51.15%`
- delta-within-band: `74.32% -> 73.30%`
- acceleration-within-band: `58.26% -> 57.25%`
- transition probability-within-band: `73.01% -> 74.18%`
- `RECOVERY` probability-within-band: `45.75% -> 48.36%`
- `RECOVERY` probability MAE: `0.1189 -> 0.1139`

Interpretation:

- The transition-aware topology dampener alone was only marginal.
- The accepted second step was the repair-confirmed, pairwise `BUST/LATE -> RECOVERY` posterior correction.
- The new third step, targeting `posterior_trapped_in_bust` and `recovery_acceleration_fade`, further improves process realism without breaking `2022_TIGHTENING`.
- The new fourth step, targeting `stabilizer_barrier_hold`, improves stable-state release timing while leaving the probability-process metrics broadly intact.
- The new fifth step, adding release-credit for mild `BUST` overhang plus mild fade windows, is narrower than a broad barrier rewrite:
  - it further improves stable label realization and overall probability-in-band share
  - it does so at the cost of a small amount of derivative-process slippage, which remains acceptable under the current gate
- The new sixth step adds a repair-confirmed, high-transition tie-break inside `price_topology`:
  - this does not change `2022_TIGHTENING`
  - it slightly improves overall process truth
  - it converts several former `topology_not_confirmed` dates into explicit `RECOVERY` topology calls
- `2023_RECOVERY` is now materially better on labels and still better on probability path:
  - stable-regime match: `61.95% -> 80.53%`
  - probability-within-band: `60.84% -> 67.26%`
  - delta-within-band: `67.70% -> 65.04%`
  - acceleration-within-band: `47.79% -> 42.70%`

## Final Conclusion

1. The new regime-process standard is superior to the old return-first promotion gate.
2. Under this stricter and more realistic standard, the upgraded production mainline remains clearly ahead of the current shadow chain.
3. The upgraded mainline now clears the process gate for production promotion more comfortably:
   - `2022_TIGHTENING stable_vs_benchmark_regime = 93.15%`
   - `2023_RECOVERY probability_within_band_share = 67.26%`
   - overall `transition_probability_within_band_share = 74.18%`
4. The shadow chain is still not eligible for live integration.
5. Residual risk has narrowed again:
   - `stabilizer_barrier_hold` has been materially reduced
   - `topology_not_confirmed` has now narrowed from `5` to `2`
   - the remaining frontier has shifted back to early-2023 `posterior_trapped_in_bust` cleanup

## Stabilizer Follow-Up

Follow-up work on `stabilizer release timing` produced two hard findings:

- a release-aware `BUST/LATE -> RECOVERY` path inside `RegimeStabilizer` is directionally correct and is now part of the mainline runtime path
- simply lowering the release barrier under high entropy did not improve the 8-year process panorama enough to justify promotion

The failed tuning attempt was deliberately not retained. It improved synthetic unit scenarios but did not move the canonical `2023_RECOVERY` window metrics beyond the current `61.95%` stable-regime match.

To stop future iterations from turning into blind threshold tuning, the audit surface was expanded:

- `price_topology` forensic payload now exports
  - `bullish_divergence`
  - `bearish_divergence`
  - `recovery_prob_delta`
  - `recovery_prob_acceleration`
- canonical backtest forensic traces now export
  - `regime_stabilizer`
  - full topology release diagnostics

Interpretation:

- the remaining lag is not well described by a single entropy barrier coefficient
- the next iteration should use the newly exposed forensic series to identify which days fail release because of
  - negative recovery acceleration
  - lingering bearish divergence
  - insufficient topology confidence
  - or residual posterior mass still trapped in `BUST`

Detailed follow-up findings now live in:

- `docs/research/2026-04-08-stabilizer-release-forensics.md`
