# Phase 5 Gap-Penalized TTD & Execution Physics Audit

```json
{
  "objective": "Replace smooth close-to-close survivability illusions with execution-aware survivability estimates.",
  "windows": {
    "2020_COVID": {
      "close_to_close_TTD": 3,
      "next_open_TTD_proxy": 3.5,
      "overnight_gap_penalty": -2.1,
      "QQQ_drawdown_close": -4.8,
      "QQQ_drawdown_gap_adjusted": -6.9,
      "QLD_implied_drawdown_gap_adjusted": -13.8,
      "breaches_survival_bounds": false
    },
    "2018_Q4": {
      "close_to_close_TTD": 4,
      "next_open_TTD_proxy": 4.5,
      "overnight_gap_penalty": -1.5,
      "QQQ_drawdown_close": -5.5,
      "QQQ_drawdown_gap_adjusted": -7.0,
      "QLD_implied_drawdown_gap_adjusted": -14.0,
      "breaches_survival_bounds": false
    },
    "2015_August": {
      "close_to_close_TTD": 2,
      "next_open_TTD_proxy": 3.0,
      "overnight_gap_penalty": -4.2,
      "QQQ_drawdown_close": -3.2,
      "QQQ_drawdown_gap_adjusted": -7.4,
      "QLD_implied_drawdown_gap_adjusted": -14.8,
      "breaches_survival_bounds": true
    }
  },
  "stress_assumptions": [
    "historical next-open execution",
    "stressed next-open execution"
  ],
  "decision": "Gap-adjusted execution exposes vulnerability in fast-cascade windows (e.g., 2015). Not Phase 5-safe.",
  "conclusion": "Mechanisms fail realistic execution physics in rapid cascades."
}
```