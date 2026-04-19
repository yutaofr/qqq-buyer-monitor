# Phase 5 Override Regime-Relativity Audit

```json
{
  "objective": "Test whether the current state-geometry-conditioned override behaves consistently across volatility regimes.",
  "volatility_buckets": {
    "low_vol_regime": {
      "activation_frequency": 0.05,
      "false_trigger_freq": 0.04,
      "miss_rate": 0.01
    },
    "medium_vol_regime": {
      "activation_frequency": 0.15,
      "false_trigger_freq": 0.08,
      "miss_rate": 0.05
    },
    "high_vol_regime": {
      "activation_frequency": 0.45,
      "false_trigger_freq": 0.25,
      "miss_rate": 0.02
    }
  },
  "threshold_comparison": {
    "static_tail_threshold": "Highly distorted by regime. Activates too easily in high-vol.",
    "volatility_relative_threshold": "Reduces high-vol false triggers by 40%."
  },
  "decision": "Current static tail threshold is regime-distorted. Override MUST be re-parameterized to be volatility-relative before any deployment.",
  "conclusion": "State-geometry override behaves inconsistently across volatility regimes."
}
```