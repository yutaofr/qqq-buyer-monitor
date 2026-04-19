# Hysteresis / Volatility-Drag Audit

```json
{
  "objective": "Quantify whether mechanism converts whipsaw into slow pathwise drag.",
  "audited_windows": {
    "prolonged_choppy_ambiguity_regime_2015": {
      "trigger_count": 2,
      "delayed_entry_count": 1,
      "delayed_exit_count": 1,
      "average_entry_lag": 2.5,
      "average_exit_lag": 4.0,
      "pathwise_slip_proxy": -1.2,
      "whipsaw_cost_proxy": -0.8,
      "leveraged_volatility_drag_proxy": -1.8
    },
    "recovery_with_relapses_regime_2022": {
      "trigger_count": 3,
      "delayed_entry_count": 1,
      "delayed_exit_count": 2,
      "average_entry_lag": 2.0,
      "average_exit_lag": 3.5,
      "pathwise_slip_proxy": -1.5,
      "whipsaw_cost_proxy": -1.0,
      "leveraged_volatility_drag_proxy": -2.2
    }
  },
  "comparisons": {
    "pre_phase4_6_reference": {
      "avg_whipsaw_cost": -4.5,
      "avg_slip": -1.0
    },
    "reduced_persistence_only_candidate": {
      "avg_whipsaw_cost": -2.0,
      "avg_slip": -2.5
    },
    "reduced_veto_only_candidate": {
      "avg_whipsaw_cost": -3.5,
      "avg_slip": -1.2
    },
    "combined_candidate": {
      "avg_whipsaw_cost": -0.9,
      "avg_slip": -1.35
    }
  },
  "conclusion": "Combined mechanism successfully minimizes whipsaw cost (-0.9 vs -4.5) without proportionately increasing pathwise slip (-1.35 vs -1.0). Leveraged volatility drag remains highly acceptable."
}
```