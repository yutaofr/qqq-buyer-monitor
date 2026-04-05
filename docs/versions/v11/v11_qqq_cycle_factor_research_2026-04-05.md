# v11 QQQ Cycle Factor Research 2026-04-05

## Question

Why did the mainline look low-accuracy and high-entropy, and is the real problem that the QQQ-cycle likelihood set is too large?

## Short Answer

No. After fixing the backtest quality-gating bug, the evidence says:

- the old "high entropy / low accuracy" narrative was materially overstated by a broken audit path
- the active QQQ-cycle model is much better than the stale report implied
- the main residual weakness is not feature count by itself, but regime-boundary confusion, especially `BUST` vs `LATE_CYCLE`
- aggressive pruning to a small first-principles core hurts holdout quality
- two real-economy proxies, `pmi_momentum` and `labor_slack`, are currently redundant and can be removed with no holdout penalty

## Research Protocol

- Selection window: `2016-01-01` to `2017-12-29`
- Holdout window: `2018-01-01` onward
- Universe: QQQ-cycle posterior only
- Candidate families:
  - baseline contract
  - leave-one-out deletions
  - first-principles core plus optional enhancers
  - pair-prune simplification
- Metrics:
  - top-1 accuracy
  - mean Brier
  - mean entropy
  - mean true-regime posterior probability
  - mean true-regime rank
  - mean expected L1 error

Source artifacts:

- `artifacts/v11_feature_subset_research/candidate_scores.csv`
- `artifacts/v11_feature_subset_research/report.md`
- `artifacts/v11_feature_subset_research/selection_winner.json`
- `artifacts/v11_feature_subset_research/production_recommendation.json`

## Root Cause

The first root cause was infrastructure, not modeling.

- `run_v11_audit()` did not preserve raw macro/source fields in the walk-forward audit frame.
- The data-quality gate therefore misread many features as unavailable and flattened or distorted likelihood contribution in backtests.
- That made multiple factor subsets look falsely similar.

Once that was fixed, the posterior surface became distinguishable again, and the factor research started producing meaningful differences.

## What The Corrected Mainline Actually Looks Like

On the corrected `2018+` canonical production audit:

- top-1 accuracy: `68.31%`
- mean Brier: `0.4582`
- mean entropy: `0.5892`
- mean true-regime probability: `0.5436`

That is not a dead high-entropy classifier. The model is usable. The remaining weakness is concentrated in turning-point regimes.

By regime:

- `MID_CYCLE`: strongest and cleanest posterior
- `LATE_CYCLE`: usable but not razor-sharp
- `BUST`: still frequently absorbed by `LATE_CYCLE`
- `RECOVERY`: usually ranked correctly, but with the widest posterior spread

## What Feature Search Found

### 1. The selection-window winner overfit

Selection winner:

- `drop_erp_absolute`

Why it looked good:

- much better `2016-2017` selection accuracy
- much better selection Brier
- much higher selection true-regime probability

Why it was rejected:

- `2018+` holdout accuracy regressed from `0.6831` to `0.6738`
- holdout true-regime probability regressed from `0.5436` to `0.5180`
- holdout entropy worsened from `0.5892` to `0.6686`

This is textbook overfit. It proved the research gate was working.

### 2. Shrinking to the core-6 was too aggressive

`qqq_core_6` holdout:

- accuracy: `0.5948`
- Brier: `0.5396`
- entropy: `0.6150`
- mean true-regime probability: `0.4903`

Interpretation:

- first-principles core alone is not enough
- the model still benefits from several market-sensitive auxiliary factors

### 3. Two features were truly redundant

Dropping `pmi_momentum` alone:

- no change in selection metrics
- no change in holdout metrics

Dropping `labor_slack` alone:

- no change in selection metrics
- no change in holdout metrics

Dropping both together:

- no change in selection metrics
- no change in holdout metrics

This made them eligible for KISS pruning.

## Final Recommendation

Promote the pruned `10`-feature contract for production:

- `real_yield_structural_z`
- `move_21d`
- `breakeven_accel`
- `core_capex_momentum`
- `copper_gold_roc_126d`
- `usdjpy_roc_126d`
- `spread_21d`
- `liquidity_252d`
- `erp_absolute`
- `spread_absolute`

Do not promote:

- `drop_erp_absolute`
- `qqq_core_6`
- any other candidate that improved the selection window but regressed on the `2018+` holdout

## Interpretation

The corrected answer is:

- The mainline did have an audit problem.
- After fixing the audit, the model was not globally broken.
- The model did not primarily fail because it had "too many factors".
- The right production move was not aggressive pruning, but disciplined simplification:
  - keep the informative market-cycle structure
  - remove only the features that proved redundant under holdout

## Production Implication

This research supports the active production contract recorded in:

- `src/engine/v11/resources/regime_audit.json`
- `docs/versions/v11/v11_bayesian_production_baseline_2026-04-05.md`
