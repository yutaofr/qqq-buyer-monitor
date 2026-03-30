#!/usr/bin/env python3
"""v11.2 High-Performance Parallel Benchmark: Full Class A Feature Expansion.
Tests all Class A factors with Level + Momentum using parallel processing.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import multiprocessing as mp
from src.engine.v11.conductor import V11Conductor

def calculate_brier(posterior, actual_regime):
    regimes = ["MID_CYCLE", "BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE"]
    return sum((posterior.get(name, 0.0) - (1.0 if name == actual_regime else 0.0)) ** 2 for name in regimes)

def run_chunk(chunk_df, train_df, feature_cols):
    """Run a chunk of the backtest sequentially to maintain library history."""
    conductor = V11Conductor(persist_library=False)
    conductor.library.df = train_df
    
    results = []
    for _, row in chunk_df.iterrows():
        t0_data = pd.DataFrame([row])
        res = conductor.daily_run(t0_data, feature_cols=feature_cols)
        
        brier = calculate_brier(res["probabilities"], row["regime"])
        pred = max(res["probabilities"], key=res["probabilities"].get)
        is_correct = 1 if pred == row["regime"] else 0
        
        results.append({
            "brier": brier,
            "is_correct": is_correct
        })
        # Update library for next day in chunk
        conductor.library.update_library(row)
    return results

def run_parallel_benchmark():
    # 1. Load Data
    data_path = Path("data/v11_poc_phase1_results.csv")
    df = pd.read_csv(data_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.dropna(subset=["regime"]).sort_values("observation_date")
    
    # 2. Split test window
    split_idx = int(len(df) * 0.2)
    train_df_initial = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    # 3. Chunking for parallelism
    n_chunks = min(mp.cpu_count(), 8)
    chunk_indices = np.array_split(np.arange(len(test_df)), n_chunks)
    chunks = [test_df.iloc[idx] for idx in chunk_indices]
    
    # 4. Experiments
    experiments = {
        "V11.0 (Baseline 6)": [
            "spread_stress_pct", "liquidity_stress_pct", "vix_stress_pct", 
            "drawdown_stress_pct", "breadth_stress_pct", "erp_stress_pct"
        ],
        "V11.2 (Full Class A Expansion)": None 
    }

    final_results = []
    print(f"Starting Parallel Benchmark: {len(df)} samples, using {n_chunks} cores.")

    for name, feature_cols in experiments.items():
        print(f"\nEvaluating: {name}...")
        
        pool_args = []
        for i in range(n_chunks):
            history_df = pd.concat([train_df_initial] + chunks[:i])
            pool_args.append((chunks[i], history_df, feature_cols))
            
        with mp.Pool(processes=n_chunks) as pool:
            chunk_results = pool.starmap(run_chunk, pool_args)
            
        all_stats = [item for sublist in chunk_results for item in sublist]
        accuracy = sum(s["is_correct"] for s in all_stats) / len(all_stats)
        mean_brier = np.mean([s["brier"] for s in all_stats])
        
        final_results.append({
            "Experiment": name,
            "Accuracy": accuracy,
            "Mean Brier": mean_brier
        })
        print(f"  -> Accuracy: {accuracy:.2%}, Brier: {mean_brier:.4f}")

    print("\n" + "="*60)
    print("V11.2 PARALLEL ARCHITECTURAL AUDIT")
    print("="*60)
    print(pd.DataFrame(final_results).to_string(index=False))

if __name__ == "__main__":
    run_parallel_benchmark()
