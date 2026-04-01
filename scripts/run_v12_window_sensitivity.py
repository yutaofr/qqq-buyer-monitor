"""Run V12 window sensitivity analysis to detect overfitting vs structural robustness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

from src.backtest import run_v11_audit
from src.engine.v11.probability_seeder import ProbabilitySeeder

EXPERIMENTS: dict[str, dict[str, Any]] = {
    "expanding": {
        "probability_seeder": {
            "orthogonalization_method": "expanding"
        }
    },
    "rolling_252": {
        "probability_seeder": {
            "orthogonalization_method": "rolling",
            "orthogonalization_window": 252
        }
    },
    "rolling_504": {
        "probability_seeder": {
            "orthogonalization_method": "rolling",
            "orthogonalization_window": 504
        }
    },
    "rolling_756": {
        "probability_seeder": {
            "orthogonalization_method": "rolling",
            "orthogonalization_window": 756
        }
    },
    "rolling_1008": {
        "probability_seeder": {
            "orthogonalization_method": "rolling",
            "orthogonalization_window": 1008
        }
    },
    "ewm_504": {
        "probability_seeder": {
            "orthogonalization_method": "ewm",
            "orthogonalization_window": 504
        }
    },
}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V12 window sensitivity experiments.")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--output-dir", default="artifacts/v12_sensitivity")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    
    for name, config in EXPERIMENTS.items():
        print(f"\n>>> Running Sensitivity Experiment: {name}")
        experiment_dir = output_dir / name
        experiment_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            summary = run_v11_audit(
                dataset_path=args.dataset_path,
                regime_path=args.regime_path,
                evaluation_start=args.evaluation_start,
                artifact_dir=str(experiment_dir),
                experiment_config=config,
            )
            
            audit = summary["sentinel_audit"]
            row = {
                "experiment": name,
                "mean_ir_diff": audit["mean_diff"],
                "all_passed": audit["all_passed"],
                "accuracy": summary["top1_accuracy"],
                "brier": summary["mean_brier"],
                "entropy": summary["mean_entropy"]
            }
            
            # Add annual details
            for year, details in audit["annual_details"].items():
                row[f"ir_diff_{year}"] = details["diff"]
                
            results.append(row)
            
        except Exception as e:
            print(f"Error in experiment {name}: {e}")

    df = pd.DataFrame(results)
    df.to_csv(output_dir / "sensitivity_results.csv", index=False)
    
    print("\n" + "="*60)
    print("V12 WINDOW SENSITIVITY RESULTS")
    print("="*60)
    print(df[["experiment", "mean_ir_diff", "all_passed", "accuracy"]].to_string(index=False))
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
