"""FRED macro data loader for the liquidity pipeline.

Thin wrapper around src.collector.macro.fetch_fred_data that adds:
  - start/end date filtering (the underlying fetcher has no date params)
  - explicit failure on empty response (no silent NaN propagation)
  - structured logging

Marked functions that hit the network are NOT called in unit tests.
Use @pytest.mark.external_service to run them in integration context only.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.collector.macro import fetch_fred_data

logger = logging.getLogger(__name__)

# Series IDs required by the liquidity pipeline
REQUIRED_SERIES = {
    "WALCL":    "Fed Reserve Assets (H.4.1) — weekly",
    "RRPONTSYD": "Overnight RRP outstanding — daily",
    "WTREGEN":  "Treasury General Account — weekly",
    "SOFR":     "Secured Overnight Financing Rate — daily",
    "VIXCLS":   "CBOE Volatility Index close — daily",
}


def load_fred_series(
    series_id: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch one FRED series and filter to [start_date, end_date].

    Args:
        series_id:  FRED series identifier (e.g., 'WALCL', 'SOFR').
        start_date: ISO date — lower bound (inclusive).
        end_date:   ISO date — upper bound (inclusive).

    Returns:
        DataFrame with columns: ['observation_date', series_id].
        Sorted ascending by observation_date.

    Raises:
        RuntimeError: if the series cannot be fetched or is empty.
    """
    raw = fetch_fred_data(series_id)

    if raw is None or raw.empty:
        raise RuntimeError(
            f"Failed to fetch FRED series '{series_id}'. "
            f"Check FRED_API_KEY in .env or network connectivity."
        )

    filtered = raw[
        (raw["observation_date"] >= pd.Timestamp(start_date))
        & (raw["observation_date"] <= pd.Timestamp(end_date))
    ].copy()

    if filtered.empty:
        raise RuntimeError(
            f"FRED series '{series_id}' returned no data "
            f"in range [{start_date}, {end_date}]. "
            f"Available range: {raw['observation_date'].min().date()} "
            f"to {raw['observation_date'].max().date()}."
        )

    logger.debug(
        "Loaded FRED %s: %d rows [%s → %s]",
        series_id,
        len(filtered),
        start_date,
        end_date,
    )
    return filtered[["observation_date", series_id]].sort_values("observation_date")
