#!/usr/bin/env python3
"""
SRD-v13.4 Deep Hydration Script.
Replays 2018-2026 to build a self-consistent Bayesian Prior.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.engine.v11.conductor import V11Conductor

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def run_replay(macro_path: str, output_path: str, start_date: str = "2018-01-01"):
    logger.info(f"Starting Deep Hydration from {start_date}...")

    # 1. Load full macro corpus (including 2017 for Z-Score pre-filling)
    full_df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index("observation_date")
    full_df = full_df.sort_index()

    # 2. Initialize Conductor in 'Silent Replay' mode
    temp_prior_path = Path("data/v13_hydrating_tmp.json")
    if temp_prior_path.exists():
        temp_prior_path.unlink()

    conductor = V11Conductor(
        macro_data_path=macro_path,
        prior_state_path=str(temp_prior_path),
        snapshot_dir="/tmp/v13_hydration_snapshots"
    )

    # 3. Filter dates for replay (2018 onwards)
    replay_dates = full_df.loc[start_date:].index.unique()

    # 4. Sequential Bayesian Replay
    total_dates = len(replay_dates)
    for i, current_date in enumerate(replay_dates):
        if i % 100 == 0:
            logger.info(f"Processing {current_date} ({i}/{total_dates})...")

        # Get PIT context (MUST include 2017 for Z-Score pre-filling)
        # We pass the full history up to current_date to allow Seeder to see the window.
        pit_data_full = full_df.loc[:current_date].copy()

        # Inject dummy price/volume data if missing
        if "qqq_close" not in pit_data_full.columns:
            pit_data_full["qqq_close"] = 400.0
            pit_data_full["source_qqq_close"] = "placeholder"
            pit_data_full["qqq_close_quality_score"] = 1.0
        if "qqq_volume" not in pit_data_full.columns:
            pit_data_full["qqq_volume"] = 50_000_000.0
            pit_data_full["source_qqq_volume"] = "placeholder"
            pit_data_full["qqq_volume_quality_score"] = 1.0

        try:
            # daily_run internally loads history from macro_data_path and filters up to current_date.
            # Passing the full context duplicates rows, breaking rolling/expanding Z-scores.
            # We must pass ONLY the T0 row.
            conductor.daily_run(pit_data_full.tail(1))
        except Exception as e:
            logger.error(f"Failed at {current_date}: {e}")
            continue

    # 5. Finalize and Export
    state = conductor.prior_book.execution_state
    state["hydration_anchor"] = start_date
    state["hydrated_at_utc"] = pd.Timestamp.utcnow().isoformat()
    state["sample_count"] = len(replay_dates)

    conductor.prior_book.update_execution_state(**state)

    final_path = Path(output_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_prior_path.rename(final_path)

    logger.info(f"Deep Hydration Complete. Prior state saved to {final_path}")

def main():
    parser = argparse.ArgumentParser(description="v13.4 Deep Hydration")
    parser.add_argument("--macro-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--output", default="data/v13_hydrated_prior.json")
    args = parser.parse_args()

    run_replay(args.macro_path, args.output)

if __name__ == "__main__":
    main()
