# Cycle Stage Taxonomy Finalization

## Decision
`STAGE_TAXONOMY_IS_STABLE_AND_USABLE`

## Operating Statement
This document treats the system as a cycle-stage navigator for human judgment. It does not restore automatic leverage targeting or claim exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "decision": "STAGE_TAXONOMY_IS_STABLE_AND_USABLE",
  "design_rule": "Coarse enough to be stable; fine enough to separate expansion, deterioration, stress, repair, and boundary warning.",
  "stages": {
    "EXPANSION": {
      "likely_confusion": "Can be confused with quiet late cycle if breadth erosion is early.",
      "neighbor_distinction": "Differs from LATE_CYCLE by absence of rising hazard and marginal breadth damage.",
      "signal_signature": [
        "low hazard",
        "healthy breadth",
        "contained volatility",
        "no repair lock"
      ],
      "typical_user_interpretation": "beta can be considered high if the human agrees with broader context"
    },
    "FAST_CASCADE_BOUNDARY": {
      "likely_confusion": "Can be mistaken for a tradable regime; the dashboard forbids that inference.",
      "neighbor_distinction": "Differs from all ordinary stages because execution/gap constraints dominate interpretation.",
      "signal_signature": [
        "gap pressure",
        "rapid collapse",
        "execution-dominated uncertainty"
      ],
      "typical_user_interpretation": "prioritize boundary awareness; automatic strategy logic is not trustworthy here"
    },
    "LATE_CYCLE": {
      "likely_confusion": "Can be confused with ordinary correction or early stress.",
      "neighbor_distinction": "Differs from STRESS because stress is not yet structurally confirmed.",
      "signal_signature": [
        "hazard rising",
        "breadth weakening",
        "volatility no longer benign"
      ],
      "typical_user_interpretation": "beta can be considered moderate; aggressiveness deserves review"
    },
    "RECOVERY": {
      "likely_confusion": "Can be confused with bear rally if relapse pressure is rising.",
      "neighbor_distinction": "Differs from EXPANSION because it follows recent stress and still carries relapse risk.",
      "signal_signature": [
        "stress eased",
        "repair evidence exists",
        "relapse risk still nonzero"
      ],
      "typical_user_interpretation": "beta may be phased back with relapse awareness"
    },
    "STRESS": {
      "likely_confusion": "Can be confused with late cycle if damage accumulates slowly.",
      "neighbor_distinction": "Differs from RECOVERY because repair evidence is not yet convincing.",
      "signal_signature": [
        "structural stress active",
        "repair lock active",
        "breadth impaired",
        "volatility elevated"
      ],
      "typical_user_interpretation": "beta thinking should be reduced or defensive"
    }
  }
}
```
