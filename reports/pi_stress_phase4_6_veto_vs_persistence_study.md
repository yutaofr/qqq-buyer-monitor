# Veto vs Persistence Discovery Study

```json
{
  "objective": "Determine whether the unresolved boundary problem is better explained by persistence, veto, both, or neither.",
  "hypotheses_tested": [
    "H1. Persistence separability hypothesis",
    "H2. Veto hypothesis",
    "H3. Combined hypothesis",
    "H4. Null hypothesis"
  ],
  "persistence_results": {
    "duration_to_peak_deterioration": "Separable (V-shape is much faster)",
    "duration_to_healing": "Separable",
    "occupancy_above_stress_threshold": "Separable (True stress has high occupancy)",
    "relapse_probability": "Separable",
    "repair_failure_count": "Separable"
  },
  "veto_candidates_tested": {
    "high_yield_spread": {
      "false_positive_suppression_effect": "High in ordinary pullbacks",
      "impact_on_true_stress_capture": "Minimal suppression of true stress",
      "best_modeled_as": "multiplicative dampener",
      "active_conditions": "only active when macro credit is stable"
    }
  },
  "primary_mechanism": "COMBINED_PERSISTENCE_AND_VETO",
  "conclusion": "Persistence handles duration separation efficiently, while veto (HY spread as a multiplicative dampener) handles false-positive suppression when stress interpretation lacks macro/credit confirmation. Both roles add distinct boundary disambiguation."
}
```