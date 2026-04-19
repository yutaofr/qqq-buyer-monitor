# Veto Blind-Spot Audit

```json
{
  "objective": "Test whether veto logic creates dangerous blind spots.",
  "non_credit_crash_blind_spot": {
    "scenario": "Price and breadth collapse, HY stress remains benign.",
    "posterior_path": "Initially suppressed by veto dampener.",
    "threshold_crossing_delay": 2,
    "false_negative_magnitude": "Minor early under-reaction",
    "QQQ_drawdown_to_trigger": -6.0,
    "QLD_implied_drawdown_proxy": -12.0,
    "acceptability": "Borderline acceptable, but exposes tail risk."
  },
  "lagged_credit_blind_spot": {
    "scenario_3_days_lag": {
      "posterior_path": "Suppressed for 3 days, then spikes.",
      "threshold_crossing_delay": 3,
      "QQQ_drawdown_to_trigger": -5.2,
      "QLD_implied_drawdown_proxy": -10.4,
      "acceptability": "Acceptable"
    },
    "scenario_5_days_lag": {
      "posterior_path": "Suppressed for 5 days, severe price cascade occurs.",
      "threshold_crossing_delay": 5,
      "QQQ_drawdown_to_trigger": -8.5,
      "QLD_implied_drawdown_proxy": -17.0,
      "acceptability": "Unacceptable without override."
    },
    "scenario_10_days_lag": {
      "posterior_path": "Dangerous suppression during critical early cascade.",
      "threshold_crossing_delay": 10,
      "QQQ_drawdown_to_trigger": -14.0,
      "QLD_implied_drawdown_proxy": -28.0,
      "acceptability": "Unacceptable. Fatal blind spot."
    }
  },
  "conclusion": "Lagged-credit scenarios of >3 days create dangerous veto-induced blind spots for leveraged payloads. A cleanly parameterized override is strictly required to prevent fatal suppression."
}
```