# Product Patch Probability Diffusion Repair

## Decision
`PROBABILITY_DIFFUSION_IS_IMPROVED_BUT_STILL_NOTICEABLE`

## Summary
Batch 2 must improve RECOVERY without replacing diffusion with fake confidence. The guardrail checks both diffuse-share behavior and dominant-label overconfidence.

## Machine-Readable Snapshot
```json
{
  "comparison": {
    "no_fake_confidence": true,
    "post_patch": {
      "average_entropy_by_stage": {
        "EXPANSION": 0.551947,
        "FAST_CASCADE_BOUNDARY": 0.719811,
        "LATE_CYCLE": 0.745645,
        "STRESS": 0.641287
      },
      "confidence_concentration_profile": {
        "CONCENTRATED": 3621,
        "DIFFUSE_OR_UNSTABLE": 835,
        "MIXED": 512,
        "MODERATELY_CONCENTRATED": 1643
      },
      "critical_stage_diffuse_share": 0.05748,
      "diffuse_or_unstable_count": 835,
      "dominant_minus_secondary_margin": {
        "EXPANSION": 0.537688,
        "FAST_CASCADE_BOUNDARY": 0.182852,
        "LATE_CYCLE": 0.227738,
        "STRESS": 0.376463
      },
      "dominant_stage_overconfidence_rate": 0.033429,
      "one_day_reversal_rate": 0.003783
    },
    "pre_patch": {
      "average_entropy_by_stage": {
        "EXPANSION": 0.550427,
        "FAST_CASCADE_BOUNDARY": 0.720673,
        "LATE_CYCLE": 0.747265,
        "STRESS": 0.643624
      },
      "confidence_concentration_profile": {
        "CONCENTRATED": 3641,
        "DIFFUSE_OR_UNSTABLE": 822,
        "MIXED": 498,
        "MODERATELY_CONCENTRATED": 1650
      },
      "critical_stage_diffuse_share": 0.057177,
      "diffuse_or_unstable_count": 822,
      "dominant_minus_secondary_margin": {
        "EXPANSION": 0.544516,
        "FAST_CASCADE_BOUNDARY": 0.182905,
        "LATE_CYCLE": 0.227796,
        "STRESS": 0.375623
      },
      "dominant_stage_overconfidence_rate": 0.041295,
      "one_day_reversal_rate": 0.00348
    }
  },
  "decision": "PROBABILITY_DIFFUSION_IS_IMPROVED_BUT_STILL_NOTICEABLE",
  "summary": "Batch 2 must improve RECOVERY without replacing diffusion with fake confidence. The guardrail checks both diffuse-share behavior and dominant-label overconfidence."
}
```
