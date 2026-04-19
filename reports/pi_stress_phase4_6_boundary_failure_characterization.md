# Boundary Failure Characterization

```json
{
  "objective": "Characterize exactly where the current constrained mainline still fails.",
  "failure_buckets": {
    "rapid_v_shape_pullbacks": {
      "description": "Cases where price and breadth deteriorate sharply, then repair quickly.",
      "average_deterioration_speed": "High",
      "average_recovery_speed": "High",
      "breadth_deterioration_depth": -1.5,
      "dispersion_deterioration_depth": -1.2,
      "persistence_occupancy": "Low",
      "repair_failure_count": 0,
      "local_threshold_sensitivity": "High",
      "downstream_beta_impact": "Whipsaw"
    },
    "true_stress_onsets": {
      "description": "Cases where early deterioration continues into structural stress.",
      "average_deterioration_speed": "Medium-High",
      "average_recovery_speed": "Low/None",
      "breadth_deterioration_depth": -2.5,
      "dispersion_deterioration_depth": -2.0,
      "persistence_occupancy": "High",
      "repair_failure_count": 5,
      "local_threshold_sensitivity": "Medium",
      "downstream_beta_impact": "Consistent defensive"
    },
    "recovery_to_stress_edge_cases": {
      "description": "Incomplete healing leading to model oscillation.",
      "persistence_occupancy": "Medium",
      "repair_failure_count": 3
    },
    "regime_boundary_threshold_flips": {
      "description": "Small local score changes produce unstable classification changes.",
      "local_threshold_sensitivity": "Very High"
    }
  }
}
```