# Cycle Stage Signal Mapping

## Decision
`STAGE_SIGNAL_MAPPING_IS_SUFFICIENTLY_COHERENT`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "STAGE_SIGNAL_MAPPING_IS_SUFFICIENTLY_COHERENT",
  "hard_rule": "No hidden score may dominate stage assignment without being surfaced in the evidence panel.",
  "source_signals": [
    "hazard_score",
    "exit/repair activation state",
    "breadth proxy",
    "volatility proxy / percentile",
    "relapse flags",
    "structural stress indicators",
    "repair confirmation indicators"
  ],
  "stage_mapping": {
    "EXPANSION": {
      "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
      "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
      "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
      "mandatory_evidence": "low stress, healthy breadth, contained volatility",
      "signals_that_matter_most": [
        "hazard",
        "breadth",
        "volatility"
      ]
    },
    "FAST_CASCADE_BOUNDARY": {
      "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
      "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
      "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
      "mandatory_evidence": "execution-dominated warning",
      "signals_that_matter_most": [
        "gap_pressure",
        "volatility_percentile",
        "hazard_delta"
      ]
    },
    "LATE_CYCLE": {
      "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
      "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
      "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
      "mandatory_evidence": "rising pressure without repair lock",
      "signals_that_matter_most": [
        "hazard_delta",
        "breadth_delta",
        "volatility_percentile"
      ]
    },
    "RECOVERY": {
      "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
      "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
      "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
      "mandatory_evidence": "repair exists but relapse remains possible",
      "signals_that_matter_most": [
        "repair_confirmation",
        "breadth_delta",
        "volatility_delta"
      ]
    },
    "STRESS": {
      "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
      "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
      "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
      "mandatory_evidence": "confirmed damage accumulation",
      "signals_that_matter_most": [
        "repair_active",
        "structural_stress",
        "breadth_proxy"
      ]
    }
  }
}
```
