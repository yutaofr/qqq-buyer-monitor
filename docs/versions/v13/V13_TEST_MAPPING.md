# v13 Test Mapping

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Purpose

This document maps v13 requirements to concrete test responsibilities.

No behavior is considered documented unless it is also mapped to a test contract.

---

## 2. Unit Tests

| Requirement | Test Target |
| :--- | :--- |
| neutral overlay returns `1.0 / 1.0` multipliers | `tests/unit/engine/v13/test_execution_overlay.py` |
| monotone negative score cannot increase beta | `tests/unit/engine/v13/test_execution_overlay.py` |
| degraded or missing inputs revert to neutral | `tests/unit/engine/v13/test_execution_overlay.py` |
| placeholder or rejected sources are excluded | `tests/unit/engine/v13/test_execution_overlay.py` |
| overlay integration leaves posterior unchanged | `tests/unit/engine/v11/test_conductor_overlay_integration.py` |
| runtime snapshot includes overlay block and schema version | `tests/unit/engine/v11/test_conductor_overlay_integration.py` |
| `status.json` exports v13 overlay-aware fields with preserved semantic surfaces | `tests/unit/test_web_exporter.py` |
| Discord payload remains compact while adding overlay execution audit lines | `tests/unit/test_discord_notifier.py` |

---

## 3. Data and PIT Tests

| Requirement | Test Target |
| :--- | :--- |
| weekly sources obey publication lag | `tests/unit/data/test_overlay_pit_contract.py` |
| every admitted source carries provenance and quality metadata | `tests/unit/data/test_overlay_pit_contract.py` |
| repurposed proxy fields are not production-admitted | `tests/unit/data/test_overlay_pit_contract.py` |

---

## 4. Backtest Tests

| Requirement | Test Target |
| :--- | :--- |
| `raw_target_beta` replay matches v12.1 | `tests/unit/test_backtest_v13_overlay.py` |
| candidate gain holds in holdout and median WFO window | `tests/unit/test_backtest_v13_overlay.py` |
| acceptance run fails closed on missing frozen artifacts | `tests/unit/test_backtest_v13_overlay.py` |
| no live download path is exercised in acceptance mode | `tests/unit/test_backtest_v13_overlay.py` |

---

## 5. Integration Tests

| Requirement | Test Target |
| :--- | :--- |
| shadow mode exports diagnostics without changing action | `tests/integration/engine/v13/test_v13_shadow_mode.py` |
| negative-only enablement preserves v12.1 belief path | `tests/integration/engine/v13/test_v13_shadow_mode.py` |
| positive reward affects deployment pace only | `tests/integration/engine/v13/test_v13_shadow_mode.py` |
| `index.html` references all required v13 web-export paths and stays contract-aligned | `tests/integration/test_web_alignment.py` |

---

## 6. Acceptance Criteria Crosswalk

| AC | Primary Test Owner |
| :--- | :--- |
| `AC-1` | `test_execution_overlay.py` |
| `AC-2` | `test_conductor_overlay_integration.py` |
| `AC-3` | `test_execution_overlay.py` |
| `AC-4` | `test_v13_shadow_mode.py` |
| `AC-5` | `test_execution_overlay.py` and `test_overlay_pit_contract.py` |
| `AC-6` | `test_overlay_pit_contract.py` |
| `AC-7` | `test_backtest_v13_overlay.py` |
| `AC-8` | `test_backtest_v13_overlay.py` |
| `AC-9` | `test_backtest_v13_overlay.py` |
| `AC-10` | `test_conductor_overlay_integration.py` |
| `AC-11` | `test_overlay_pit_contract.py` |
| `AC-12` | document review gate |
| `AC-13` | `test_execution_overlay.py` and `test_overlay_pit_contract.py` |
| `AC-14` | `test_backtest_v13_overlay.py` |
| `AC-15` | `test_conductor_overlay_integration.py` |
| `AC-16` | `test_conductor_overlay_integration.py` and `test_v13_shadow_mode.py` |
| `AC-17` | `test_web_exporter.py` and `test_web_alignment.py` |
| `AC-18` | `test_discord_notifier.py` |
