import pandas as pd
import numpy as np
import concurrent.futures
import time
import os
from pathlib import Path
from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder

# Paths (Docker paths)
QQQ_DATA_PATH = "/app/data/qqq_history_cache.csv"
MACRO_DATA_PATH = "/app/data/macro_historical_dump.csv"

def run_single_node_backtest(node_name, start_date, end_date):
    """Worker function for parallel backtest execution."""
    print(f"[*] Starting Backtest for: {node_name} ({start_date} -> {end_date})")
    
    # 1. Load data
    ohlcv = pd.read_csv(QQQ_DATA_PATH, parse_dates=["Date"])
    ohlcv = ohlcv.sort_values("Date").set_index("Date")
    ohlcv.index = pd.to_datetime(ohlcv.index, utc=True).tz_convert(None).normalize()
    
    # Slice with buffer (e.g. 504 days for features)
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    buffer_start = start_dt - pd.Timedelta(days=700) # Ensure enough history for indicators
    
    ohlcv_slice = ohlcv.loc[buffer_start:end_dt]
    if ohlcv_slice.empty:
        return {"node": node_name, "error": "No data in range"}

    # 2. Setup Seeder
    seeder = HistoricalMacroSeeder(csv_path=MACRO_DATA_PATH)
    
    # 3. Execute Backtest
    tester = Backtester(initial_capital=100_000.0)
    
    start_time = time.time()
    summary = tester.simulate_portfolio(
        ohlcv_slice.loc[start_dt:end_dt],
        macro_seeder=seeder,
        enable_dynamic_search=False
    )
    duration = time.time() - start_time
    
    # 4. Extract Efficacy Metrics
    # Real Baseline: Buy & Hold (Lump sum at start)
    prices = ohlcv_slice.loc[start_dt:end_dt, "Close"]
    bh_nav = prices / prices.iloc[0] * 100_000.0
    bh_mdd = (bh_nav / bh_nav.expanding().max() - 1).min()
    
    tactical_mdd = summary.tactical_mdd
    # Normalize RAE relative to Buy & Hold
    rae = 1.0 - (abs(tactical_mdd) / abs(bh_mdd)) if bh_mdd < 0 else 0.0
    
    # Export audit for lead/lag analysis
    if node_name == "GFC":
        summary.daily_timeseries.to_csv(f"/app/data/audit_gfc_daily.csv")

    print(f"[+] Completed: {node_name} in {duration:.2f}s | RAE: {rae:.2%} | BH_MDD: {bh_mdd:.2%}")
    
    return {
        "node": node_name,
        "start": start_date,
        "end": end_date,
        "tactical_mdd": tactical_mdd,
        "bh_mdd": bh_mdd,
        "rae": rae,
        "signal_beta": summary.signal_beta,
        "duration": duration
    }

def parallel_crisis_audit():
    stress_nodes = [
        ("Dot-com", "2000-03-01", "2002-10-31"),
        ("GFC", "2007-10-01", "2009-03-31"),
        ("2011 Debt Ceiling", "2011-07-01", "2011-10-31"),
        ("2018 QT", "2018-10-01", "2018-12-31"),
        ("COVID-19 Crash", "2020-02-01", "2020-04-30"),
        ("2022 Inflation", "2022-01-01", "2022-10-31")
    ]
    
    print(f"=== Parallel Crisis Audit Initiated (Cores: {os.cpu_count()}) ===")
    total_start = time.time()
    
    results = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(run_single_node_backtest, *node) for node in stress_nodes]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    total_duration = time.time() - total_start
    print(f"\n=== Parallel Audit Completed in {total_duration:.2f}s ===")
    
    df = pd.DataFrame(results).sort_values("start")
    print("\n--- Crisis Efficacy Scorecard ---")
    print(df[["node", "rae", "tactical_mdd", "bh_mdd", "duration"]])
    
    output_path = "/app/data/crisis_efficacy_scorecard.csv"
    df.to_csv(output_path, index=False)
    print(f"\nResults exported to {output_path}")

if __name__ == "__main__":
    parallel_crisis_audit()
