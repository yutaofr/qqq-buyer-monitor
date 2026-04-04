# v11 Bayesian Production Baseline 2026-04-05

## Production Stance

- `standard` mainline remains the production champion.
- `S4 sidecar`, `S5 tractor`, and `S4+S5 panorama` remain `shadow-only`.
- The business redline is now enforced end-to-end: `beta_expectation >= 0.5`, `raw_target_beta >= 0.5`, `target_beta >= 0.5`.

## User Philosophy To Execution Surface

- The system assumes a permanent core long bias toward `QQQ`.
- `0.5x` is the non-negotiable structural core. Entropy and overlays may reduce only the **surplus above 0.5x**, not the core allocation itself.
- `QLD` is only the marginal lever:
  - `RECOVERY`: permitted to re-accelerate exposure.
  - `MID_CYCLE`: maintain normal `QQQ`-dominant exposure, with `QLD` only under strong support.
  - `LATE_CYCLE`: de-lever first, slow new cash deployment.
  - `BUST`: keep the `QQQ` core, avoid `QLD`, pause or nearly pause new cash.

## Hard Invariants

- `target_beta` may not fall below `0.5x`.
- `raw_target_beta` and `beta_expectation` may not fall below `0.5x`.
- Entropy haircut acts on `(beta - 0.5)` only.
- Overlay penalties may not break the `0.5x` floor.
- `QLD` is implemented only for `beta > 1.0`.

## Canonical Mainline Audit

Source:
- `artifacts/v14_mainline_audit/summary.json`
- `artifacts/v14_mainline_diagnostics/diagnostic_report.json`

Protocol:
- walk-forward OOS
- evaluation window: `2018-01-01` to `2026-04-06`
- frozen QQQ cache, no live price download

Measured result:
- Posterior top-1 accuracy: `44.93%`
- Mean Brier: `0.6442`
- Mean entropy: `0.9303`
- Raw beta vs realized-regime expected beta MAE: `0.1435`
- Target beta vs realized-regime expected beta MAE: `0.2848`
- Deployment exact match: `44.84%`
- Deployment rank error: `0.6459`
- Deployment pacing abs error: `0.3701`
- Deployment pacing signed bias: `-0.1299`
- Target floor breach rate: `0.00%`
- Raw beta minimum: `0.7841x`
- Beta expectation minimum: `0.7841x`
- Target beta minimum: `0.6396x`
- Raw beta within `5pct` of realized-regime expected beta: `13.06%`
- Target beta within `5pct` of realized-regime expected beta: `0.00%`

Interpretation:
- The floor problem is solved structurally.
- The engine is no longer pinned to `0.5x`; the entire audited `2018+` production window stays above the floor.
- The posterior remains high-entropy, especially in `2020_COVID` (`0.9507`) and `2022_H1` (`0.9896`).
- The engine is materially better as a **critical-regime detector** than as a low-entropy regime classifier.
- Stable critical recall remains usable: `76.67%`.
- The deployment layer is systematically too conservative relative to the realized-regime policy surface; the signed pacing bias is negative (`-0.1299`), which means capital is typically deployed slower than the regime policy would imply.
- `target beta within 5pct of expected = 0.00%` confirms the smoothed execution surface is not a literal copy of the discrete regime policy beta map; it is a deliberately cautious allocator with inertia and entropy damping.

## Detector Layer Audit

Source:
- `docs/research/v14_full_panorama_audit.md`

Measured result:
- `S5 tractor` OOS AUC / Brier: `0.6018 / 0.1478`
- `S4 sidecar` OOS AUC / Brier: `0.5782 / 0.1564`
- `S5 tractor` AC-2: `0.4931`
- `S4 sidecar` AC-2: `0.4961`
- Sidecar status: `FULL`
- Leakage falsification: `PIT 0.39 vs Leaky 0.92`

Interpretation:
- The detector layer has real OOS signal after PIT enforcement.
- `S4` is important and valid, but its current value is as a shadow detector, not as an automatic production override.
- The limiting factor is now the composition policy with the mainline, not the existence of detector signal itself.

## Mainline Configuration Sweep

Holdout sweep on `2018-01-01+` over:
- `posterior_mode in {classifier_only, runtime_reweight}`
- `var_smoothing in {1e-4, 1e-3, 1e-2, 1e-1}`

Best-balanced result remains the current production config:
- `posterior_mode=classifier_only`
- `gaussian_nb_var_smoothing=1e-4`

Reason:
- `var_smoothing=0.1` raises top-1 accuracy to `48.14%`, but worsens Brier, entropy, beta-expectation fidelity, and deployment alignment.
- `runtime_reweight` lowers entropy, but Brier degrades sharply to roughly `1.0+`, which is unacceptable for posterior-distribution fidelity.
- `1e-4` keeps the best Brier and the best overall posterior-quality balance on the audited grid.

## Panorama Combination Audit

Source:
- `docs/research/v14_panorama_strategy_matrix.md`

Holdout result on `2018-01-01+`:
- `standard`: return `1.5059`, max DD `-0.2362`, mean scenario beta `0.6465`, scenario-vs-expected MAE `0.2754`
- `s4_sidecar`: return `1.1682`, max DD `-0.2339`, mean scenario beta `0.5924`, scenario-vs-expected MAE `0.3104`
- `s5_tractor`: return `1.2299`, max DD `-0.2362`, mean scenario beta `0.6170`, scenario-vs-expected MAE `0.2945`
- `s4s5_panorama`: return `1.2978`, max DD `-0.2589`, mean scenario beta `0.6307`, scenario-vs-expected MAE `0.3345`, rejected for drawdown regression

Shared holdout beta lens:
- Mean raw beta: `0.8681`
- Mean mainline standard beta: `0.6465`
- Mean realized-regime expected beta: `0.8753`

Interpretation:
- The mainline itself already sits materially below the realized-regime policy beta surface.
- `S4` and `S5` push the effective beta even lower, so they worsen both return and beta-policy fidelity on holdout.
- `S4+S5 panorama` partially restores beta relative to `S4` or `S5` alone, but still degrades fidelity and worsens drawdown.

Decision:
- `standard` wins both by return and by expectation fidelity.
- `S4` and `S5` are no longer structurally broken after the floor fix, but they still underperform the mainline on holdout.
- `S4+S5` remains non-production because it worsens drawdown.

## Window Semantics

- `artifacts/v14_mainline_audit/` is the canonical production audit window: `2018-01-01` onward.
- `docs/research/v14_panorama_strategy_matrix.md` uses `2015-01-01` onward because it needs a calibration segment before the `2018+` holdout.
- Do not compare the mainline metrics in those two reports without noting the window difference. The `2015+` matrix audit is stricter and includes early low-support years; the `2018+` production audit is the correct live-governance window.

## Operational Guidance

- Live production path: `standard` mainline only.
- Shadow monitoring:
  - keep `S4 sidecar`
  - keep `S5 tractor`
  - keep `S4+S5 panorama`
- Review triggers:
  - if posterior entropy remains above `0.95` for prolonged windows
  - if deployment exact match falls below `40%`
  - if deployment pacing abs error drifts materially above the current `~0.37`
  - if signed pacing bias becomes materially more conservative than the current `~-0.13`
  - if target beta expectation MAE widens materially above the current `~0.28`

## Report Set

- Detector audit: `docs/research/v14_full_panorama_audit.md`
- Panorama strategy audit: `docs/research/v14_panorama_strategy_matrix.md`
- Mainline artifacts: `artifacts/v14_mainline_audit/`
- Mainline diagnostics: `artifacts/v14_mainline_diagnostics/`
