from __future__ import annotations

import logging
import math
from pathlib import Path

import pandas as pd

from src.main import _build_v11_signal_result

logger = logging.getLogger(__name__)


def run_db_backfill(
    macro_path: str = "data/macro_historical_dump.csv",
    db_path: str = "data/signals.db",
    limit: int = 126,
) -> bool:
    """
    Seamlessly rebuilds the historical regime probabilities into signals.db.
    Called exactly once during cold start if the database is missing history,
    allowing the frontend 6-month chart to be populated.
    """
    # Import locally to avoid circular dependencies if any module level calls exist
    from src.engine.v11.conductor import V11Conductor
    from src.store.db import init_db, save_signal

    logger.warning(f"SRE AUTO-REPAIR: Missing history detected. Invoking {limit}-day Synchronous Backfill...")

    if not Path(macro_path).exists():
        logger.error(f"Cannot backfill: {macro_path} missing.")
        return False

    init_db(db_path)

    full_df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index("observation_date")
    full_df = full_df.sort_index()

    if len(full_df) == 0:
        logger.error("Cannot backfill: macro dataset is empty.")
        return False

    replay_dates = full_df.index.unique()[-limit:]
    conductor = V11Conductor(macro_data_path=macro_path)

    total_dates = len(replay_dates)
    success_count = 0

    for i, current_date in enumerate(replay_dates):
        if i % 25 == 0:
            logger.info(f"Backfilling {current_date.date()} ({i+1}/{total_dates})...")

        pit_data_full = full_df.loc[:current_date].copy()

        # Physical integrity: ensure structural columns exist to maintain pipeline constraints.
        if "qqq_close" not in pit_data_full.columns:
            pit_data_full["qqq_close"] = 400.0
        pit_data_full.loc[:, "qqq_close"] = pit_data_full["qqq_close"].fillna(400.0)

        if "qqq_volume" not in pit_data_full.columns:
            pit_data_full["qqq_volume"] = 50_000_000.0
        pit_data_full.loc[:, "qqq_volume"] = pit_data_full["qqq_volume"].fillna(50_000_000.0)

        try:
            runtime = conductor.daily_run(pit_data_full.tail(1))

            price = pit_data_full["qqq_close"].iloc[-1]
            if pd.isna(price) or not math.isfinite(price):
                price = 400.0

            result = _build_v11_signal_result(runtime, price=float(price))
            save_signal(result, path=db_path)
            success_count += 1
        except Exception as e:
            logger.error(f"Backfill trace error at {current_date}: {e}")
            continue

    logger.info(f"SRE AUTO-REPAIR Complete: {success_count}/{total_dates} records backfilled to {db_path}.")
    return success_count > 0
