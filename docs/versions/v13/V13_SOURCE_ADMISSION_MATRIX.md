# v13 Source Admission Matrix

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Scope

This document defines which market-internal and sentiment-adjacent sources may enter the v13 execution overlay.

It does not authorize any source to enter the v12.1 posterior engine.

---

## 2. Admission Rules

A source is production-admissible only if all of the following are true:

- the source is free or publicly accessible
- the schema is stable, or the reconstruction rule is stable and documented
- historical values are recoverable
- publication timing is point-in-time safe
- the live path and backtest path can use the same semantic field

If any one of these fails, the source is research-only or rejected.

---

## 3. Matrix

| Signal Family | Raw Source | Frequency | PIT Basis | Production Status | Allowed v13 Use | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `breadth_proxy` | yfinance `^ADD` or `^ADDN` raw advance-decline net series | Daily | Next execution event after market close | Conditional | Negative overlay only | Admitted only if v13 derives a documented monotone transform from raw net breadth. The current repo sigmoid proxy is not itself locked production logic. |
| `ndx_concentration` | yfinance `QQQ` and `QQEW` | Daily | Next execution event after market close | Admitted | Negative overlay only | Must use archived raw prices and deterministic derivation. |
| `qqq_close` | yfinance `QQQ` | Daily | Next execution event after market close | Admitted | Tape confirmation | Raw tape input only. |
| `qqq_volume` | yfinance `QQQ` volume | Daily | Next execution event after market close | Admitted | Tape confirmation | Volume transforms must use only trailing or expanding windows observable at decision time. |
| `CFTC COT` | official CFTC release | Weekly | Official publication timestamp | Conditional | Negative or positive overlay | Requires self-archived release snapshots before production use. |
| `NAAIM Exposure Index` | official weekly publication | Weekly | Official publication timestamp | Research only | None in v13.0 production | Free to view, but usage restrictions and small sample reduce suitability. |
| `AAII Sentiment` | paid structured feed | Weekly | Not acceptable for required free-data path | Rejected | None | Not free in production-ready form. |
| `CNN Fear & Greed` | unofficial or unstable web endpoint | Daily | No audited vintage path | Rejected | None | Not admissible. |
| `FINRA short volume` | official files with correction risk | Daily | Publication timing known, vintage control incomplete | Research only | None in v13.0 production | Not admissible until self-archived corrections are managed. |
| placeholder helpers in `macro_v3.py` | constant returns or neutral fallbacks | N/A | Not PIT data | Rejected | None | Never production evidence. |

---

## 4. Explicit Rejections From Current Repository

The following current helpers or fields are not admissible in v13 production:

- `fetch_fcf_yield()`
- `fetch_earnings_revisions_breadth()`
- `fetch_sector_rotation()`
- `fetch_short_volume_proxy()`
- `fetch_move_index()` neutral constant fallback as overlay evidence
- `pct_above_50d` from the current breadth collector

Reason:

- they are placeholders, neutral constants, or semantically misleading proxy fields
- they cannot support industrial audit, replay, or PIT verification

---

## 5. Canonical Raw Fields

The only raw overlay fields that may be added to the research or runtime contract in v13.0 are:

```text
adv_dec_ratio
source_breadth_proxy
breadth_quality_score
ndx_concentration
source_ndx_concentration
ndx_concentration_quality_score
qqq_close
source_qqq_close
qqq_close_quality_score
qqq_volume
source_qqq_volume
qqq_volume_quality_score
cot_equity_positioning
source_cot_equity_positioning
cot_quality_score
```

Derived overlay scores and multipliers are runtime outputs, not canonical raw history.

---

## 6. PIT Rules

- Daily tape inputs may be observed only after their market-close timestamp.
- Weekly sources must use their official publication timestamp, not the economic reference date.
- No weekly source may be filled into earlier business days before release.
- If a source is missing, stale, or degraded, the overlay must revert the affected component to neutral rather than fabricate a value.

---

## 7. Required Hardening Before Admission

The following hardening work is required before full production rollout:

- replace the current breadth sigmoid shortcut with a documented transform governed by `execution_overlay_audit.json`
- archive raw weekly source releases with publication timestamps
- attach quality and provenance fields to every raw overlay input
- document every fallback path and confirm that degraded inputs map to neutral behavior

---

## 8. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-5` | missing or degraded overlay data reverts to neutral |
| `AC-6` | weekly sources respect publication time |
| `AC-11` | every production signal appears in this matrix with provenance |
| `AC-13` | placeholder helpers and proxy fields are excluded |
| `tests/unit/data/test_overlay_pit_contract.py` | field-level PIT and provenance checks |
| `tests/unit/engine/v13/test_execution_overlay.py` | source gating and neutral fallback behavior |
