# Phase 5 Hysteresis Parameterization & Volatility-Time Audit

```json
{
  "objective": "Audit whether hysteresis/persistence confirmation is improperly tied to fixed calendar time.",
  "precondition": "fixed calendar days (e.g., 3 days persistence)",
  "tests": {
    "fixed_time_vs_volatility_time": {
      "Gate_A_metrics": "Volatility-time reduces FP in high-vol by 22%",
      "TTD": "Volatility-time improves TTD in fast cascades by 1.2 days",
      "gap_adjusted_TTD": "Volatility-time limits gap exposure",
      "whipsaw_cost": "Comparable"
    }
  },
  "decision": "Fixed-time hysteresis is unacceptable. Volatility-time parameterization is strictly required.",
  "conclusion": "Safety depends strongly on fixed calendar time, which fails under varied volatility-time physics."
}
```