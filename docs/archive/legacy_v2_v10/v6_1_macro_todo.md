# QQQ-Monitor v6.1 Macro Resilience Upgrade TODO

## Status Legend
- [ ] Todo
- [/] In Progress
- [x] Complete
- [!] Blocked / Issue

## Implementation Plan

### Phase 1: Treasury API Implementation
- [x] **Task 1: Treasury Data Collector**
  - Create `src/collector/treasury.py`.
  - Implement `fetch_treasury_yields()` using the XML feed.
  - **Verification:** Script `tests/poc_treasury_xml.py` confirmed 10Y and 3M data retrieval.
  - **Review:** Spec compliance & Code quality complete.

### Phase 2: Failover Integration
- [x] **Task 2: Resilient Macro Fetching**
  - Update `src/collector/macro.py` with Treasury Yield Curve fallback.
  - Update `src/collector/macro_v3.py` with Treasury Real Yield fallback.
  - Cleaned up imports and synchronized failover chains.
  - **Verification:** Logic verified through manual dry-run logs.
  - **Review:** Spec compliance & Code quality complete.

### Phase 3: Chaos Validation (Strong Test)
- [x] **Task 3: Disaster Recovery Testing**
  - Create `tests/integration/test_v6_macro_resilience.py`.
  - Mock `requests.get` to return 500 for `api.stlouisfed.org`.
  - Verify system successfully falls back to Treasury API and produces a valid `Tier0Result`.
  - **Verification:** Integration tests passed (2/2). Verified failover to Treasury XML.
  - **Review:** Final architectural sign-off complete.
