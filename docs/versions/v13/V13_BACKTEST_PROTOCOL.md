# v13 Backtest Protocol

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Purpose

This document defines the only acceptable methodology for evaluating the v13 execution overlay.

The objective is not to maximize CAGR. The objective is to verify that v13 improves execution discipline without changing the v12.1 belief engine and without introducing overfit.

---

## 2. Scope

This protocol covers:

- historical data requirements
- experiment design
- machine learning validation discipline
- non-regression gates
- reproducibility requirements

It does not authorize new posterior features or new regime labels.

---

## 3. Frozen Inputs

Every acceptance run must use:

- a pinned code revision
- a pinned `execution_overlay_audit.json`
- a pinned evaluation start date
- a pinned evaluation end date
- frozen price history
- frozen archived overlay inputs for any weekly or delayed-release source

If any frozen artifact is missing, the acceptance run must fail closed.

---

## 4. Prohibited Backtest Behavior

The following are forbidden in v13 acceptance:

- downloading fresh market history during CI or release acceptance
- using `date.today()` or any moving end date for acceptance metrics
- reconstructing weekly sentiment values without archived publication timestamps
- synthetic backfill for unavailable sources
- fabricating `fear_greed`, short-volume, or other legacy research placeholders

---

## 5. Required Experiment Matrix

Every candidate must be evaluated against all of the following:

1. `v12.1 champion`
2. `v13 code path with overlay disabled`
3. `v13 negative-only overlay`
4. `v13 full overlay`

The difference between `1` and `2` must be zero on posterior and `raw_target_beta`.

---

## 6. Validation Method

v13 tuning must use blocked chronological validation only.

Required procedure:

1. Freeze signal definitions.
2. Split data into nested walk-forward windows.
3. Tune only on inner windows.
4. Evaluate on outer validation windows.
5. Keep one untouched final holdout window.
6. Report median window performance, not best-window performance.

Rejected procedure:

- random shuffle validation
- random K-fold cross-validation
- event-picked regime slices
- retuning until a single crisis looks good

---

## 7. Metrics

The minimum evaluation panel is:

- posterior invariance
- `raw_target_beta` invariance
- target beta delta distribution
- left-tail drawdown behavior
- max adverse excursion on adds
- deployment timing score
- turnover
- state-switch frequency
- holdout stability
- replay determinism

No candidate may be accepted using only return metrics.

---

## 8. Overfitting Rejection

A candidate is rejected if any of the following holds:

- gains appear only in one crisis interval
- gains disappear on the untouched holdout
- signal weights or rankings are unstable across windows
- permuted or randomized controls produce similar gains
- the candidate needs retuning of inherited v12.1 execution thresholds
- the candidate cannot be replayed from frozen artifacts

---

## 9. Backtest Environment Rules

Acceptance runs must use an environment that is deterministic and network-closed for market history.

Required environment behavior:

- load QQQ price history from frozen cache or checked-in artifact
- load overlay raw history from archived files
- reject missing artifacts immediately
- emit enough diagnostics to replay every overlay decision

The current repository backtest path contains a live-download escape hatch and a moving default end date. Those behaviors are incompatible with v13 acceptance and must not be used for release certification.

---

## 10. Acceptance Gates

v13 passes backtest certification only if:

- posterior outputs are unchanged versus v12.1
- `raw_target_beta` is bit-identical versus v12.1
- left-tail execution behavior improves or remains neutral
- reward effects are rarer and smaller than penalty effects
- all required artifacts are reproducible from frozen inputs

---

## 11. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-8` | `raw_target_beta` replay must match v12.1 |
| `AC-9` | gains must hold in holdout and median walk-forward windows |
| `AC-14` | acceptance run fails closed on missing frozen artifacts and does not hit live download path |
| `tests/unit/test_backtest_v13_overlay.py` | experiment matrix, invariance, non-regression |
| `tests/integration/engine/v13/test_v13_shadow_mode.py` | shadow-mode replay and diagnostics |
