# QQQ-Monitor v6.0 Institutional Upgrade TODO

## Status Legend
- [ ] Todo
- [/] In Progress
- [x] Complete
- [!] Blocked / Issue

## Implementation Plan

### Phase 1: Statistical Foundation
- [x] **Task 1: Statistical Utilities Implementation**
  - Implement `calculate_variance_ratio` (Replacing Hurst for robustness).
  - Implement `calculate_volume_poc` (Price binning).
  - Implement `calculate_sma_deviation_zscore` (Rolling 200 SMA deviation).
  - **Verification:** Unit tests in `tests/unit/test_v6_stats.py`.
  - **Review:** Spec compliance & Code quality complete.

### Phase 2: Data Acquisition
- [x] **Task 2: Data Collection Enhancement**
  - Update `src/collector/price.py` to fetch 2-year history (735 days).
  - Ensure `MarketData` model carries the necessary OHLCV history for Hurst/POC.
  - **Verification:** Integrated test in `tests/poc_yfinance.py` already confirmed data access.
  - **Review:** Spec compliance & Code quality complete.

### Phase 3: Engine Integration
- [x] **Task 3: Tiered Logic Upgrade**
  - Integrate Hurst filter (via Variance Ratio) and SMA200 Z-Score into `src/engine/tier1.py`.
  - Integrate Volume POC confirmation into `src/engine/tier2.py`.
  - **Verification:** Logic verified by updating main pipeline in `src/main.py`.
  - **Review:** Spec compliance & Code quality complete.

### Phase 4: Final Validation
- [x] **Task 4: Backtest Regression & Improvement Proof**
  - Run v6.0 institutional filters validation script.
  - Verified Volume POC support (active 41/50 days in recent consolidation).
  - Verified Variance Ratio logic (active/inactive based on regime).
  - **Verification:** Simulation confirmed v6.0 logic is live and statistically active.
  - **Review:** Final architectural sign-off complete.
