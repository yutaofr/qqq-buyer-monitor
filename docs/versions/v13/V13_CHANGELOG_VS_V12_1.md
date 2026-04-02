# v13 Change Log vs v12.1

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. What Remains Unchanged

v13 does not change the v12.1 belief engine.

Frozen items:

- 10-factor `ProbabilitySeeder`
- `GaussianNB` posterior engine
- recursive priors
- entropy haircut semantics
- regime definitions
- v12.1 beta surface
- inherited `BehavioralGuard` bucket boundaries
- inherited deployment-state multipliers

---

## 2. What v13 Adds

v13 adds an execution overlay layer that:

- consumes market-internal execution inputs
- penalizes `protected_beta` under negative tape conditions
- may accelerate incremental deployment pace under validated repair conditions
- exports overlay diagnostics into runtime snapshots and UI surfaces

v13 also adds:

- a versioned overlay audit artifact
- a source governance whitelist
- explicit PIT rules for weekly sentiment-style inputs
- a stricter backtest reproducibility protocol
- output-layer adaptation for `status.json`, `index.html`, and Discord notifications without a visual redesign

---

## 3. What v13 Explicitly Rejects

The following are not part of v13:

- 4-bucket replacement of the 10-factor core
- hand-written replacement of the GaussianNB posterior
- execution-router or realized-residual meta-routing in the action path
- proprietary or unstable sentiment feeds
- placeholder collectors, neutral constants, or semantically misleading proxy fields as production evidence

---

## 4. Companion Work Not Absorbed Into v13

These are valid issues, but not part of the v13 overlay rollout:

- v12.1 base conductor quality semantics and fallback aggregation
- research collector hardening outside overlay-admitted sources
- removal of live-download escape hatches from acceptance backtest workflows

These must be tracked separately so attribution remains clean.

---

## 5. Migration Impact

Expected code areas touched by v13 implementation:

- `conductor.py`
- new `execution_overlay.py`
- `deployment_policy.py` integration
- `web_exporter.py`
- `discord_notifier.py`
- `src/web/public/index.html`
- runtime snapshot writer
- v13 tests and overlay audit artifact

Expected code areas that must remain semantically unchanged:

- `probability_seeder.py`
- `bayesian_inference.py`
- posterior calibration path
- base regime labels

---

## 6. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-2` | posterior and `raw_target_beta` invariance |
| `AC-4` | positive overlay limited to deployment pace |
| `AC-8` | replay is bit-identical against v12.1 for raw beta |
| `AC-16` | inherited execution interfaces remain frozen |
