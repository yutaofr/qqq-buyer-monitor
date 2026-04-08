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

After applying the transition-aware `price_topology` change and rerunning the mainline backtest on `2018-01-01` to `2026-04-07`:

- `stable_vs_benchmark_regime = 67.63%`
- `probability_within_band_share = 46.24%`
- `delta_within_band_share = 75.12%`
- `acceleration_within_band_share = 60.65%`
- `transition_probability_within_band_share = 65.94%`

Compared on the same `2018+` window against the old mainline:

- stable regime match: `68.74% -> 67.63%`
- probability-within-band: `46.09% -> 46.24%`
- delta-within-band: `75.82% -> 75.12%`
- acceleration-within-band: `60.79% -> 60.65%`
- transition probability-within-band: `65.89% -> 65.94%`

Interpretation:

- The transition-aware topology dampener is directionally correct.
- But it is only a marginal improvement, not a decisive fix.
- The current main engine still needs a deeper posterior-process correction rather than another shallow blending tweak.

## Final Conclusion

1. The new regime-process standard is superior to the old return-first promotion gate.
2. Under this stricter and more realistic standard, the current production mainline remains clearly ahead of the current shadow chain.
3. The shadow chain is still not eligible for live integration.
4. The production engine change is safe and modest, but it does not yet unlock a major upgrade.
5. The next real research target is:
   - rebuild the `RECOVERY` posterior path itself
   - not just relax entropy or speed up release
