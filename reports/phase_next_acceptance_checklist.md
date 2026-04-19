# Phase Next Acceptance Checklist

## Summary
Acceptance checklist is evaluated as a gate. One-vote-fail items must all be false.

## Provenance
Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. Legacy post-Phase-4.2 artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "best_practice_items": {
    "BP1": true,
    "BP2": true,
    "BP3": true,
    "BP4": true,
    "BP5": true
  },
  "expansive_research_verdict_allowed": true,
  "mandatory_pass_items": {
    "MP1": true,
    "MP2": true,
    "MP3": true,
    "MP4": true,
    "MP5": true,
    "MP6": true,
    "MP7": true,
    "MP8": true,
    "MP9": true
  },
  "one_vote_fail_items": {
    "OVF1": false,
    "OVF2": false,
    "OVF3": false,
    "OVF4": false,
    "OVF5": false,
    "OVF6": false,
    "OVF7": false
  },
  "summary": "Acceptance checklist is evaluated as a gate. One-vote-fail items must all be false."
}
```
