#!/usr/bin/env python3
"""
v11.5 Historical Macro Analyzer & Reproduction Tool.
Consolidates timeline analysis, regime transitions, and accuracy auditing.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.engine.v11.conductor import V11Conductor

# Suppress noisy logs
logging.getLogger("src.engine.v11").setLevel(logging.WARNING)


def run_historical_audit(start_date: str, end_date: str, csv_path: str):
    print(f"=== v11.5 Historical Audit: {start_date} to {end_date} ===")

    # 1. Load Dataset
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} not found.")
        return

    full_df = pd.read_csv(csv_path, parse_dates=["observation_date"])
    window_df = full_df[
        (full_df["observation_date"] >= start_date) & (full_df["observation_date"] <= end_date)
    ].sort_values("observation_date")

    if window_df.empty:
        print("No records found in the specified range.")
        return

    print(f"Auditing {len(window_df)} trading days...")

    # 2. Setup Engine
    conductor = V11Conductor()
    history = []

    # 3. Simulate Daily Lifecycle
    for _, row_raw in window_df.iterrows():
        dt = row_raw["observation_date"]
        # Wrap as T+0 input
        t0_df = pd.DataFrame([row_raw])
        t0_df.index = [dt]
        t0_df.index.name = "observation_date"

        runtime = conductor.daily_run(t0_df)

        # Capture context
        history.append(
            {
                "date": dt,
                "regime": runtime["stable_regime"],
                "beta": runtime["target_beta"],
                "entropy": runtime.get("entropy", 0.0),
                "actual_regime": row_raw.get("regime"),  # May be None if not labeled
                "liq": row_raw.get("net_liquidity_usd_bn"),
                "spread": row_raw.get("credit_spread_bps"),
                "price": row_raw.get("qqq_close"),
            }
        )

    history_df = pd.DataFrame(history)

    # 4. Chronology of Transitions
    history_df["regime_change"] = history_df["regime"] != history_df["regime"].shift(1)
    changes = history_df[history_df["regime_change"]].dropna(subset=["regime"])

    print("\n[CHRONOLOGY] Regime Transitions:")
    if changes.empty:
        print("  (No transitions detected in this window)")
    else:
        for _, c in changes.iterrows():
            print(
                f"  {c['date'].date()}: -> {c['regime']:12} | Beta={c['beta']:.2f}x | Entropy={c['entropy']:.4f}"
            )

    # 5. Accuracy Metrics (If Ground Truth Available)
    if history_df["actual_regime"].notna().any():
        valid = history_df.dropna(subset=["actual_regime", "regime"])
        accuracy = (valid["regime"] == valid["actual_regime"]).mean()
        print("\n[METRICS] Predictive Quality:")
        print(f"  Top-1 Accuracy: {accuracy:.2%}")

    # 6. Stability Statistics
    print("\n[STABILITY] Analysis:")
    print(f"  Total Transitions: {len(changes)}")
    print(f"  Avg Entropy:       {history_df['entropy'].mean():.4f}")
    print(f"  Avg Target Beta:   {history_df['beta'].mean():.2f}x")

    # 7. Milestone Detection (BUST periods)
    bust_periods = history_df[history_df["regime"] == "BUST"]
    if not bust_periods.empty:
        print(f"\n[ALERT] BUST periods detected: {len(bust_periods)} days")
        print(f"  Min Beta during window: {history_df['beta'].min():.2f}x")


def main():
    parser = argparse.ArgumentParser(description="V11 historical analysis tool")
    parser.add_argument("--start", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date (YYYY-MM-DD)")
    parser.add_argument("--dataset", default="data/macro_historical_dump.csv", help="Path to CSV")

    args = parser.parse_args()
    run_historical_audit(args.start, args.end, args.dataset)


if __name__ == "__main__":
    main()
