# Phase 5 Full Adversarial Candidate Validation

```json
{
  "objective": "Subject current candidate family to explicitly adversarial validation.",
  "evaluations": {
    "rapid_v_shape": {
      "fp_rate": 0.18,
      "recovery_distinction_error": 0.4
    },
    "recovery_with_relapse": {
      "oscillation_rate": 2.5,
      "threshold_local_flip_frequency": 12
    },
    "high_vol_stress": {
      "fp_rate": 0.25,
      "whipsaw_cost_proxy": -3.5
    },
    "blind_basket": {
      "status": "Not available, evaluation impossible"
    }
  },
  "conclusion": "Candidates fail under adversarial slices. High-vol stress and rapid V-shape recoveries exhibit severe threshold flips and FP clustering."
}
```