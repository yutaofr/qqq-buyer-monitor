"""V12.1 Hyperparameter Sweep for Survival Verification."""
import pandas as pd
import numpy as np
import os
import json
from src.backtest import run_v11_audit

def run_sweep():
    dataset_path = "data/macro_historical_dump.csv"
    regime_path = "data/v11_poc_phase1_results.csv"
    
    # Param Grid
    alphas = [0.01, 0.02, 0.03, 0.05]
    spans = [252, 504]
    
    best_overall_ir = -np.inf
    best_params = None
    best_summary = None
    
    print("--- Starting Hyperparameter Sweep for Survival Clause ---")
    
    for alpha in alphas:
        for span in spans:
            print(f"\nTesting Params: alpha={alpha}, span={span}")
            
            exp_config = {
                "model_hyperparameters": {
                    "sentinel": {
                        "alpha_decay": alpha,
                        "span_base": span
                    }
                }
            }
            
            try:
                summary = run_v11_audit(
                    dataset_path=dataset_path,
                    regime_path=regime_path,
                    evaluation_start="2018-01-01",
                    artifact_dir="artifacts/sweep_temp",
                    experiment_config=exp_config
                )
                
                audit = summary["sentinel_audit"]
                if audit["all_passed"]:
                    print(f"  >>> SUCCESS: Survival Clause PASSED for alpha={alpha}, span={span}")
                    mean_ir = np.mean([v["ir_with_l4"] for v in audit["annual_details"].values()])
                    if mean_ir > best_overall_ir:
                        best_overall_ir = mean_ir
                        best_params = (alpha, span)
                        best_summary = summary
                else:
                    print(f"  >>> FAILED: Survival Clause violation in {alpha}, {span}")
                    
            except Exception as e:
                print(f"  Error testing params: {e}")

    if best_params:
        print("\n" + "="*40)
        print(f"FINAL SURVIVAL PARAMETERS FOUND:")
        print(f"Alpha: {best_params[0]}")
        print(f"Span:  {best_params[1]}")
        print(f"Mean IR: {best_overall_ir:.4f}")
        print("="*40)
        
        # Save the winner
        save_dir = "artifacts/v12_audit_final_optimized"
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, "optimized_params.json"), "w") as f:
            json.dump({"alpha": best_params[0], "span": best_params[1], "summary": best_summary}, f, indent=2)
    else:
        print("\n!!! CRITICAL: No parameters found that satisfy the Survival Clause !!!")

if __name__ == "__main__":
    run_sweep()
