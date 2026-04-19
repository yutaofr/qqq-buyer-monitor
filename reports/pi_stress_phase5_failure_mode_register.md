# Phase 5 Governance Failure-Mode Register & Kill Criteria

```json
{
  "objective": "Formalize what would invalidate or downgrade this candidate.",
  "failure_modes": [
    {
      "name": "OOS contamination overhang",
      "detection_metric": "Lack of clean blind basket",
      "severity": "CRITICAL",
      "consequence": "hard block"
    },
    {
      "name": "Gap-penalized TTD breach",
      "detection_metric": "QLD gap-adjusted drawdown > -15%",
      "severity": "CRITICAL",
      "consequence": "downgrade"
    },
    {
      "name": "Volatility-regime override distortion",
      "detection_metric": "High-vol override false trigger > 15%",
      "severity": "HIGH",
      "consequence": "forced redesign"
    }
  ],
  "conclusion": "Kill criteria explicitly block advancement due to OOS contamination and Gap-penalized TTD breaches."
}
```