# v11 Bayesian Production Baseline 2026-04-05

## Production Stance

- `standard` mainline remains the production champion.
- `S4 sidecar`, `S5 tractor`, and `S4+S5 panorama` remain shadow-only.
- The business redline is enforced end-to-end: `beta_expectation >= 0.5`, `raw_target_beta >= 0.5`, `target_beta >= 0.5`.

## Root Cause Review

The earlier complaint of "low accuracy / high entropy" had two different causes and they were being mixed together:

1. A real backtest bug existed in `run_v11_audit()`.
   - Raw macro/source fields were not being carried into the walk-forward frame.
   - The quality gate therefore zeroed or distorted feature contributions in backtest.
   - This made many feature subsets look falsely similar and contaminated the previous audit narrative.

2. After the backtest bug was fixed, the remaining model weakness was no longer "too many factors" in general.
   - The corrected `2018+` canonical audit is materially stronger than the stale report.
   - The true posterior weakness is concentrated in regime boundaries:
     - `BUST` is still often absorbed into `LATE_CYCLE`.
     - `RECOVERY` remains the highest-entropy regime.
   - The model is strongest on `MID_CYCLE`, usable on `LATE_CYCLE`, and still softer at the two turning-point states.

## User Philosophy To Execution Surface

- The system assumes a permanent core long bias toward `QQQ`.
- `0.5x` is the non-negotiable structural core.
- Entropy and overlays may reduce only the surplus above `0.5x`, never the core allocation itself.
- `QLD` is only the marginal lever:
  - `RECOVERY`: allowed to re-accelerate beta.
  - `MID_CYCLE`: hold the core and add leverage only with strong support.
  - `LATE_CYCLE`: de-lever first and slow deployment.
  - `BUST`: hold the `QQQ` core, avoid `QLD`, and nearly pause new cash.

## Active Feature Contract

The active production contract is now a pruned `10`-feature QQQ-cycle set:

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

What changed:

- `pmi_momentum` and `labor_slack` were removed from the active contract.
- They remain implemented in `ProbabilitySeeder`, but they are not active in production.
- Reason: dropping them individually or together produced no regression in the corrected QQQ-cycle holdout. KISS wins.

What did **not** survive research:

- Removing `erp_absolute` looked best on the `2016-2017` selection window, but it degraded `2018+` holdout accuracy and posterior truth probability. That is classic overfit and was rejected.
- Collapsing to a first-principles `core_6` subset materially worsened holdout accuracy, Brier, entropy, and posterior alignment. The problem was not "too many factors" by itself.

## Canonical Production Audit

Source:

- `artifacts/v14_mainline_audit/summary.json`
- `artifacts/v14_mainline_diagnostics/diagnostic_report.json`

Protocol:

- walk-forward OOS
- evaluation window: `2018-01-01` to `2026-03-31`
- frozen QQQ cache, no live price download
- active feature contract: `10` features

Measured result:

- Posterior top-1 accuracy: `68.31%`
- Mean Brier: `0.4582`
- Mean entropy: `0.5892`
- Mean true-regime posterior probability: `0.5436`
- Mean true-regime rank: `1.4452`
- Mean expected L1 error: `0.9128`
- Raw beta vs realized-regime expected beta MAE: `0.1187`
- Target beta vs realized-regime expected beta MAE: `0.1875`
- Deployment exact match: `55.25%`
- Deployment rank error: `0.6231`
- Deployment pacing abs error: `0.3587`
- Deployment pacing signed bias: `-0.1371`
- Target floor breach rate: `0.00%`
- Raw beta minimum: `0.5016x`
- Beta expectation minimum: `0.5016x`
- Target beta minimum: `0.5392x`
- Raw beta within `5pct` of realized-regime expected beta: `31.51%`
- Target beta within `5pct` of realized-regime expected beta: `5.20%`

Interpretation:

- The mainline is not a dead `0.5x` floor machine anymore.
- The posterior is not high-entropy in the old pathological sense; `0.5892` is a usable uncertainty level for a 4-state regime engine.
- The mainline is still conservative relative to the discrete regime-policy surface, but the gap is much smaller than the stale audit implied.
- The execution layer still under-deploys relative to the realized-regime policy surface, but the bias is now moderate rather than structurally broken.

## Regime-Level Posterior Lens

From `artifacts/v14_mainline_diagnostics/diagnostic_report.json`:

- `MID_CYCLE`
  - mean true-regime probability: `0.6675`
  - mean true-regime rank: `1.3602`
  - mean entropy: `0.5295`
- `LATE_CYCLE`
  - mean true-regime probability: `0.4837`
  - mean true-regime rank: `1.3963`
  - mean entropy: `0.5869`
- `BUST`
  - mean true-regime probability: `0.3327`
  - mean true-regime rank: `1.9327`
  - mean entropy: `0.6547`
  - dominant confusion: `LATE_CYCLE` mean posterior `0.5304`
- `RECOVERY`
  - mean true-regime probability: `0.4507`
  - mean true-regime rank: `1.1921`
  - mean entropy: `0.7853`

Interpretation:

- The hardest residual confusion is still `BUST -> LATE_CYCLE`.
- `RECOVERY` is usually ranked correctly, but with wider posterior spread than the other states.
- This is why the engine feels softer at turning points than in stable trend regimes.

## Extended Research Window

Source:

- `artifacts/v11_cycle_baseline_2015/summary.json`
- `artifacts/v11_cycle_baseline_2015/diagnostics/diagnostic_report.json`
- `artifacts/v11_feature_subset_research/`

Window:

- `2015-01-01` to `2026-03-31`

Measured result:

- Posterior top-1 accuracy: `54.29%`
- Mean Brier: `0.6123`
- Mean entropy: `0.5867`
- Mean true-regime posterior probability: `0.4637`

Interpretation:

- The `2015-2017` pre-holdout segment is materially noisier than `2018+`.
- That is exactly why feature selection must not blindly optimize the selection window and then be promoted without a hard holdout gate.

## QQQ Cycle Feature Research

Source:

- `artifacts/v11_feature_subset_research/candidate_scores.csv`
- `artifacts/v11_feature_subset_research/report.md`
- `artifacts/v11_feature_subset_research/selection_winner.json`
- `artifacts/v11_feature_subset_research/production_recommendation.json`

Research protocol:

- selection window: `2016-01-01` to `2017-12-29`
- holdout window: `2018-01-01` onward
- metric family:
  - top-1 accuracy
  - Brier
  - entropy
  - mean true-regime posterior probability
  - mean true-regime rank
  - mean expected L1 error

Research conclusions:

- Selection winner: `drop_erp_absolute`
  - rejected for production because holdout accuracy and posterior truth probability regressed.
- Production recommendation: `drop_pmi_momentum__labor_slack`
  - accepted because holdout quality was unchanged while the contract became simpler.
- First-principles `core_6`
  - rejected because holdout dropped to `59.48%` accuracy with materially worse Brier/entropy.

## Detector Layer

Source:

- `docs/research/v14_full_panorama_audit.md`

Measured result:

- `S5 tractor` OOS AUC / Brier: `0.6018 / 0.1478`
- `S4 sidecar` OOS AUC / Brier: `0.5782 / 0.1564`
- `S5 tractor` AC-2: `0.4931`
- `S4 sidecar` AC-2: `0.4961`
- Sidecar status: `FULL`

Interpretation:

- The detector layer has real OOS signal.
- The limiter is no longer detector existence; it is the portfolio composition tradeoff against the already-improved mainline.

## Panorama Layer

Source:

- `docs/research/v14_panorama_strategy_matrix.md`

Holdout result on `2018-01-01+`:

- `standard`: return `1.5898`, max DD `-0.2315`, mean scenario beta `0.7313`
- `s4_sidecar`: return `1.2104`, max DD `-0.2294`, mean scenario beta `0.6551`
- `s5_tractor`: return `1.3375`, max DD `-0.2315`, mean scenario beta `0.6922`
- `s4s5_panorama`: return `1.3365`, max DD `-0.2550`, rejected for drawdown regression

Decision:

- Keep `standard` in production.
- Keep `S4`, `S5`, and `S4+S5` in shadow.

## Artifact Set

- Mainline audit: `artifacts/v14_mainline_audit/`
- Mainline diagnostics: `artifacts/v14_mainline_diagnostics/`
- Extended mainline research window: `artifacts/v11_cycle_baseline_2015/`
- QQQ-cycle feature research: `artifacts/v11_feature_subset_research/`
- Detector audit: `docs/research/v14_full_panorama_audit.md`
- Panorama strategy matrix: `docs/research/v14_panorama_strategy_matrix.md`
