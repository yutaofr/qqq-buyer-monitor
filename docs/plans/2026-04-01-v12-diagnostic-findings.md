# V12 Diagnostic Findings

**Date:** 2026-04-01

## Baseline Diagnosis

The first v12 baseline (`Accuracy 65.85%`, `Brier 0.4929`, `Entropy 0.225`) did not fail because the regime stabilizer blocked valid crisis signals. Crisis-slice diagnostics showed:

- `2018Q4`, `2020_COVID`, and `2022_H1` all preserved high raw/stable critical recall.
- `raw_target_beta` was more aggressive, but `target_beta` delivered better crisis drawdown control.
- The main degradation came from flattened regime separation in normal and transition periods, not from a broken crisis detector.

## Structural Finding

The audit contract still contains `CAPITULATION`, but `data/v11_poc_phase1_results.csv` does not provide label support for that regime. This is now surfaced explicitly in:

- `run_v11_audit(...)[\"state_support\"]`
- `artifacts/v12_diagnostics/diagnostic_report.json`

The state remains unsupported and must not be treated as silently valid.

## Controlled Ablations

The following ablations were run through `scripts/run_v12_ablation.py`:

- `var_smoothing_1e-3`
- `var_smoothing_1e-4`
- `clip_12`
- `roc_63d`
- `roc_21d`
- `capex_ewma3`
- `move_orth_none`
- `move_orth_half`
- focused round-two combinations around `var_smoothing_1e-4`
- `classifier_only` posterior mode variants
- 4-state structural experiments without `CAPITULATION`

## Accepted Defaults

Three changes were accepted because they improved aggregate metrics and crisis recall without relying on narrow window-specific wins:

1. `GaussianNB var_smoothing`: `1e-2 -> 1e-4`
2. `core_capex_momentum`: add `ewma_span: 3` before expanding z-score normalization
3. posterior computation: switch default from runtime-prior reweighting to `classifier_only`

These changes became the new baseline through:

- `src/engine/v11/resources/regime_audit.json`
- `src/backtest.py`
- `src/engine/v11/conductor.py`
- `src/engine/v11/probability_seeder.py`

## Rejected Variants

The following variants were rejected:

- `roc_63d`, `roc_21d`: accuracy and Brier deteriorated materially
- `move_orth_none`: worse accuracy and worse Brier
- `move_orth_half` as a standalone default: better than baseline but weaker than the accepted pair
- `clip_12` as a standalone default: near-neutral change with no decisive benefit
- 4-state removal of `CAPITULATION`: no decisive classification gain, despite cleaning up the unsupported-state warning
- `classifier_only` with smaller `var_smoothing` (`1e-5`, `1e-6`): marginal Brier gains but weaker return and no decisive accuracy gain over `1e-4`

## Current Best Verified Baseline

After adopting the accepted defaults, the verified backtest result is:

- `Accuracy`: `67.38%`
- `Brier`: `0.4475`
- `Entropy`: `0.333`
- `Lock`: `1.2%`
- `Stable critical recall`: `74.41%`

## Interpretation

This remains materially below the original `>=80%` accuracy aspiration, but the diagnostic evidence does not support forcing the model back toward v11.5-style pseudo-certainty. The currently accepted improvements increase separation without restoring the old leakage-prone confidence profile.

The new baseline is also more conservative in rebound windows than the prior v12 baseline, but it buys that with materially better calibration and shallower drawdown. In other words, the system is now more honest and more defensive, not simply more hesitant.

## Work Log: v11.5 Overfit Confirmation

The previous v11.5 headline result (`Top-1 Accuracy 98.71%`) remains best interpreted as an overfit / leakage-tainted benchmark, not a trustworthy production truth.

Evidence used for this confirmation:

1. `docs/WIKI_V11.md` records the extreme v11.5 headline accuracy as `98.71%`.
2. `docs/V12_ORTHOGONAL_FACTOR_SPEC.md` explicitly documents two root causes:
   - factor collinearity created repeated votes on the same credit/rate axis
   - PIT-safe lag enforcement removed a residual look-ahead advantage
3. Under v12 causal enforcement, entropy rose into the `0.214-0.333` range while crisis recall stayed intact. This pattern is consistent with removal of pseudo-certainty, not with random model collapse.
4. The strongest new gain in this iteration came from reducing prior-induced overconfidence and letting the classifier posterior remain more honest (`classifier_only`). That direction is the opposite of the old v11.5 “certainty inflation” pattern.

Conclusion: v11.5's exaggerated backtest quality should still be treated as a structurally biased reference point, not a valid target to recover.
