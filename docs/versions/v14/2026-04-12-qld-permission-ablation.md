# QLD Permission Hardening and Ablation

**Date:** 2026-04-12

## Scope

This change hardens the execution path that decides whether `QLD` is legally available, whether sub-`1.0x` `QLD + Cash` is allowed, and when tactical sell signals can directly revoke leverage. The posterior engine, raw beta expectation, and overlay beta math remain unchanged. The work only changes the execution-permission layer.

## Architectural Changes

1. `resonance` is now binding through a dedicated `QLDPermissionEvaluator`.
   - `SELL_QLD` can force `QLD -> QQQ`.
   - `BUY_QLD` no longer acts as a UI-only label; it can relax the re-entry path only after the hard permission gate is open.

2. Live and backtest now share the same QLD permission chain.
   - Live still consumes `run_baseline_inference(...)`.
   - Canonical backtest now consumes the frozen `artifacts/v14_panorama/baseline_oos_trace.csv` and reconstructs per-day `tractor/sidecar` state before calling `daily_run(..., baseline_result=...)`.

3. A PIT-safe `fundamental_override` proxy now exists.
   - Inputs are limited to checked-in, replayable series: `erp_ttm_pct` and `core_capex_mm`.
   - Missing or degraded inputs fail closed.
   - When the proxy is active and the recovery price process is confirmed, it can release an otherwise noisy `SELL_QLD` veto.

4. Overlay breadth/concentration collinearity is suppressed.
   - When breadth is already derived from `QQQ/QQEW`, the separate concentration penalty is dropped so the same narrow-leadership signal is not counted twice.

5. Sub-`1.0x` `QLD` is no longer governed by the generic bucket inertia alone.
   - Once the hard gate is open, the permission layer can directly authorize the `QLD` execution path.
   - This preserves the same portfolio beta while switching the path from `QQQ + Cash` to `QLD + Cash`.

## Ablation Protocol

Reference artifacts:

- `artifacts/qld_permission_ablation/summary.json`
- `artifacts/qld_permission_ablation/scenario_metrics.csv`
- `artifacts/qld_permission_ablation/report.md`

Evaluation windows:

- Defense window: `2022-01-03` to `2022-10-31`
- Re-risk window: `2023-02-01` to `2023-06-30`

No-regression gate:

- regime-process alignment metrics must remain within tolerance versus `parity_only`
- the 2022 defense window must not become more levered
- the 2023 re-risk window must not lose beta versus `parity_only`

## Verified Results

All six scenarios passed the no-regression gate.

| Scenario | 2022 Defense QLD Days | 2023 Re-risk QLD Days | First 2023 QLD Date |
| :--- | ---: | ---: | :--- |
| `parity_only` | 0 | 0 | - |
| `bind_resonance_sell` | 0 | 0 | - |
| `fundamental_override` | 0 | 5 | `2023-03-09` |
| `collinear_suppression` | 0 | 0 | - |
| `sub1x_guard` | 0 | 5 | `2023-03-09` |
| `all_on` | 0 | 2 | `2023-03-09` |

Important interpretation:

- `bind_resonance_sell` and `collinear_suppression` are safety fixes. They preserve process quality and do not worsen the 2022 defense window.
- The first material 2023 execution-path change appears only after the sub-`1.0x` authorization path is made real.
- `all_on` stays more conservative than `sub1x_guard` alone because the binding sell path is still active; the fundamental override now releases part of that pressure, but not all of it.

## Production Read

The final `all_on` posture is accepted because:

- it preserves the 2022 defense behavior
- it keeps regime-process metrics unchanged versus the parity baseline
- it releases `QLD` earlier than the historical parity path during the 2023 re-risk window

Residual risk:

- the PIT-safe `fundamental_override` is still a proxy, not a true analyst-revision series
- `all_on` improves execution-path timing, but it does not fully replicate the full 2023 AI melt-up
- further gains would require checked-in, replayable earnings-revision history rather than looser macro overrides
