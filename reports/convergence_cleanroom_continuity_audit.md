# Convergence Clean-Room Continuity Audit

## Summary
Decision-driving metrics are recomputed from executable paths in this script.

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "event_window_count": 7,
  "final_budget_allocation_allowed_by_audit": true,
  "legacy_artifacts_used_as_numeric_truth": false,
  "metric_families": [
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "baseline event-window metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "structural non-defendability metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "loss contribution metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "exit-repair metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "hybrid decomposition metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "hazard timing metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "interaction validation metrics",
      "trace": "scripts/convergence_research.py"
    },
    {
      "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
      "metric_family": "execution-layer metrics",
      "trace": "scripts/convergence_research.py"
    }
  ],
  "price_rows": 6611,
  "source_policy": {
    "macro_source": "data/macro_historical_dump.csv",
    "post_phase_4_2_artifacts_used_as_numeric_truth": false,
    "primary_price_source": "data/qqq_history_cache.csv"
  },
  "summary": "Decision-driving metrics are recomputed from executable paths in this script."
}
```
