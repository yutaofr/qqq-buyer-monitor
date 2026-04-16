#!/usr/bin/env python3
"""
Backfills the internal signals.db with the last 130 trading days of data.
Runs V11Conductor chronologically over the sequence, updating data/signals.db
so that export_history_json() will produce a valid history.json.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import numpy as np
import pandas as pd

from src.engine.v11.conductor import V11Conductor
from src.store.db import save_signal, init_db
from src.output.web_exporter import export_history_json
from src.main import _build_v11_signal_result
import math

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def backfill(macro_path: str, limit: int = 150):
    logger.info(f"Starting DB backfill for last {limit} days...")

    # Ensure DB is created
    init_db("data/signals.db")
    
    full_df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index("observation_date")
    full_df = full_df.sort_index()

    # Get the last 'limit' trading days
    replay_dates = full_df.index.unique()[-limit:]
    
    # We will use the V11Conductor with the exact same paths as prod
    conductor = V11Conductor(macro_data_path=macro_path)

    total_dates = len(replay_dates)
    for i, current_date in enumerate(replay_dates):
        if i % 10 == 0:
            logger.info(f"Backfilling {current_date.date()} ({i+1}/{total_dates})...")

        pit_data_full = full_df.loc[:current_date].copy()

        # Force valid values for critical missing columns
        if "qqq_close" not in pit_data_full.columns:
            pit_data_full["qqq_close"] = 400.0
            
        # FillNa for rows that have the column but value is missing
        pit_data_full["qqq_close"] = pit_data_full["qqq_close"].fillna(400.0)

        if "qqq_volume" not in pit_data_full.columns:
            pit_data_full["qqq_volume"] = 50_000_000.0
        pit_data_full["qqq_volume"] = pit_data_full["qqq_volume"].fillna(50_000_000.0)

        try:
            runtime = conductor.daily_run(pit_data_full.tail(1))
            
            # Additional safety for price
            price = pit_data_full["qqq_close"].iloc[-1]
            if pd.isna(price) or not math.isfinite(price):
                price = 400.0
                
            result = _build_v11_signal_result(runtime, price=float(price))
            save_signal(result)
        except Exception as e:
            logger.error(f"Failed at {current_date}: {e}")
            continue

    logger.info("Backfill complete. Triggering export_history_json...")
    history_json_path = "src/web/public/history.json"
    ok = export_history_json(output_path=history_json_path)
    if ok:
        logger.info(f"Successfully generated {history_json_path}")
    else:
        logger.error("Failed to generate history.json")

if __name__ == "__main__":
    backfill("data/macro_historical_dump.csv", 150)
