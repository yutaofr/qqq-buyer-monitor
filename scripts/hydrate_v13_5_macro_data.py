#!/usr/bin/env python3
"""
v13.5 Data Hydration Patch.
Fetches Real-Economy factors (PMI Proxy, UNRATE, JTSJOL) from FRED and merges into macro corpus.
"""

import logging
import os
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_DATA_PATH = Path("data/macro_historical_dump.csv")


def fetch_fred_series(series_id: str, retries: int = 3):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data["observations"])
                df["date"] = pd.to_datetime(df["date"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                return df.set_index("date")[["value"]].rename(columns={"value": series_id})
            else:
                logger.warning(
                    f"Attempt {attempt + 1} failed for {series_id}: {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {series_id}: {e}")

    raise ConnectionError(f"Failed to fetch {series_id} after {retries} attempts.")


def run_hydration():
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY not found in .env")

    logger.info("Fetching Real-Economy series from FRED...")
    # MANEMP: Manufacturing Employment (PMI Proxy)
    # UNRATE: Unemployment Rate
    # JTSJOL: Job Openings: Total Nonfarm
    try:
        pmi_proxy = fetch_fred_series("MANEMP")
        unrate = fetch_fred_series("UNRATE")
        jtsjol = fetch_fred_series("JTSJOL")
    except Exception as e:
        logger.error(f"FRED fetch failed: {e}")
        return

    logger.info("Merging into master macro dataset...")
    master_df = pd.read_csv(BASE_DATA_PATH, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )

    # Forward fill monthly data to daily frequency (PIT-safe)
    # We use 'ffill' because monthly macro data is usually released once and stays valid until next release
    pmi_daily = pmi_proxy.reindex(master_df.index, method="ffill")
    unrate_daily = unrate.reindex(master_df.index, method="ffill")
    jtsjol_daily = jtsjol.reindex(master_df.index, method="ffill")

    master_df["pmi_proxy_manemp"] = pmi_daily
    master_df["unemployment_rate"] = unrate_daily
    master_df["job_openings"] = jtsjol_daily

    # Source tagging for v13.4+ Quality Scoring
    master_df["source_pmi_proxy"] = "fred:MANEMP"
    master_df["source_unemployment"] = "fred:UNRATE"
    master_df["source_job_openings"] = "fred:JTSJOL"

    master_df.to_csv(BASE_DATA_PATH)
    logger.info(f"v13.5 Data Hydration complete. Master dataset updated at {BASE_DATA_PATH}")


if __name__ == "__main__":
    run_hydration()
