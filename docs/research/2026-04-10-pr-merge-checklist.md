# PR Merge Checklist (2026-04-10)

## Branch / PR

- Source branch: `verify-QLD-point`
- Target branch: `main`
- Pull request: `#44`

## Local Verification

- `ruff check .`
  - Status: `PASS`
- `pytest tests/unit/test_v14_panorama_matrix.py tests/unit/test_worldview_benchmark.py tests/unit/test_regime_process_audit.py tests/unit/test_backtest_v11.py tests/unit/test_breadth.py -q`
  - Status: `34 passed`
- `docker run --rm -v "$PWD":/app -w /app qqq-monitor:py313 python -m pytest tests -q`
  - Status: `337 passed, 2 deselected`

## Mainline Process Audit

Source: `artifacts/v14_panorama/mainline/summary.json`

- `stable_vs_benchmark_regime = 0.8009`
- `probability_within_band_share = 0.5605`
- `delta_within_band_share = 0.8326`
- `acceleration_within_band_share = 0.8538`
- `transition_probability_within_band_share = 0.9405`
- `entropy_within_band_share = 0.6224`
- `transition_entropy_within_band_share = 0.8706`
- Assessment: `PASS` versus current conditional-process minima

## Panorama Matrix

Sources:
- `artifacts/v14_panorama/default_holdout_report.csv`
- `artifacts/v14_panorama/selected_candidate.csv`
- `docs/research/v14_panorama_strategy_matrix.md`

- Candidate report now uses the same conditional expected-process gate language as mainline
- Default holdout `standard`:
  - `acceptance_pass = True`
  - `approx_total_return = 1.9302`
  - `approx_max_drawdown = -0.2277`
  - `entropy_within_band_share = 0.6614`
- Selected candidate:
  - `scenario = standard`
  - `selection_failed_closed = False`
  - `acceptance_pass = True`

## Worldview / Process Audits

Sources:
- `docs/research/v14_macro_cycle_worldview_audit.md`
- `artifacts/v14_worldview_audit/summary.json`
- `artifacts/regime_process_panorama/report.md`
- `artifacts/regime_process_panorama/summary.json`

- Worldview audit:
  - `overall_beta_mae = 0.1469`
  - `stable_vs_benchmark_regime = 0.6286`
  - `left_tail covered_share = 0.6627`
- Regime-process panorama:
  - Mainline dominates shadow on overall process fit
  - Mainline entropy/process metrics now materially exceed shadow baseline

## Visual Artifacts

- Full-period panorama chart:
  - `artifacts/v14_panorama/analysis/panorama_full_period.png`
- Recent-window panorama chart:
  - `artifacts/v14_panorama/analysis/panorama_recent_period.png`
- Mainline probabilistic audit chart:
  - `artifacts/v14_panorama/mainline/v12_probabilistic_audit.png`
- Mainline beta fidelity chart:
  - `artifacts/v14_panorama/mainline/v12_target_beta_fidelity.png`

## Merge Readiness

- Code changes: verified
- Artifacts refreshed: verified
- Research docs refreshed: verified
- Lint: verified
- Local unit/integration tests: verified
- Docker full suite: verified
- PR remote checks: `pending` after final merge-prep push (`verify` x2, `Vercel`)
