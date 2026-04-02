# v13 Rollout Checklist

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Pre-Implementation Gate

- confirm v13 scope remains execution-layer only
- confirm no posterior feature additions
- confirm all new parameters will live in `src/engine/v13/resources/execution_overlay_audit.json`
- confirm inherited `BehavioralGuard` boundaries and deployment multipliers remain frozen

---

## 2. Data Gate

- source admission matrix reviewed and signed off
- placeholder helpers and proxy fields explicitly excluded
- frozen archive plan defined for any weekly source
- provenance and quality fields defined for every admitted raw input

---

## 3. Test Gate

- unit tests exist for neutral fallback
- unit tests exist for monotonic penalty behavior
- PIT tests exist for weekly publication lag
- backtest tests exist for `raw_target_beta` invariance
- snapshot tests exist for overlay decision trace

No production enablement before all test files exist.

---

## 4. Shadow Mode Gate

- overlay runs in diagnostics-only mode
- runtime snapshot exports full overlay block
- UI exposes overlay diagnostics without action impact
- `index.html` preserves existing page style while rendering overlay audit data
- Discord notification remains compact and execution-audit oriented
- shadow-mode replay matches frozen artifacts

---

## 5. Negative-Only Enablement Gate

- holdout confirms non-regression
- left-tail execution behavior is neutral or improved
- no inherited v12.1 interface was retuned
- rollback switch verified

---

## 6. Positive Reward Enablement Gate

- negative-only phase completed successfully
- positive reward remains limited to incremental deployment pace
- reward effect is smaller and rarer than penalty effect
- holdout confirmation repeated after reward enablement

---

## 7. Release Gate

- all SRD acceptance criteria passed
- source matrix, backtest protocol, runtime schema, change log, and test mapping are present
- acceptance backtests ran with frozen artifacts and no live download path
- changelog reviewed against v12.1 champion contract

---

## 8. Rollback Rule

Immediate rollback is mandatory if any of the following occurs:

- posterior or `raw_target_beta` changes unexpectedly
- overlay uses a rejected source
- replay from runtime snapshot fails
- holdout or live shadow diagnostics contradict acceptance evidence

Rollback action:

1. disable overlay
2. preserve v12.1 execution path
3. keep diagnostics enabled only if replay remains valid

---

## 9. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-1` | neutral overlay returns neutral multipliers |
| `AC-2` | v12.1 posterior and `raw_target_beta` remain unchanged |
| `AC-10` | diagnostics exist before action enablement |
| `AC-12` | required document set exists |
| `AC-16` | inherited interfaces remain frozen |
