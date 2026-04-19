# Signal-Role Reclassification

```json
{
  "objective": "Reclassify signal families by functional role.",
  "signals": {
    "breadth": {
      "roles": [
        "additive_evidence",
        "persistence_evidence"
      ]
    },
    "dispersion": {
      "roles": [
        "additive_evidence",
        "persistence_evidence"
      ]
    },
    "vix_term_structure": {
      "roles": [
        "additive_evidence"
      ]
    },
    "high_yield_spread": {
      "roles": [
        "veto_evidence"
      ],
      "notes": "Rejected as additive feature due to lag, but validated as a highly effective multiplicative dampener (veto) for ordinary corrections."
    },
    "recovery_healing_signal": {
      "roles": [
        "persistence_evidence"
      ]
    },
    "beta_instability_signal": {
      "roles": [
        "unsuitable"
      ]
    }
  }
}
```