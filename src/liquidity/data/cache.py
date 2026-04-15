"""Local file cache for external data sources (FRED, yfinance).

Purpose: Avoid repeated network calls during integration test debugging.

Cache strategy:
  - First run: fetch from network, serialize to .cache/liquidity/
  - Subsequent runs: load from cache if file exists and TTL not expired
  - Force refresh: delete .cache/liquidity/ or pass refresh=True

Cache files are Parquet for DataFrames, stored per-source per-date-range.
.cache/ is .gitignore'd — never committed.

This module is used ONLY by integration tests and manual scripts.
The production panel_builder.py does NOT use caching (always live data).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/liquidity")
DEFAULT_TTL_HOURS = 24


def _cache_key(source: str, identifier: str, start: str, end: str) -> str:
    """Generate deterministic cache filename."""
    raw = f"{source}_{identifier}_{start}_{end}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"{source}_{identifier}_{h}.pkl"


def _is_cache_valid(path: Path, ttl_hours: int = DEFAULT_TTL_HOURS) -> bool:
    """Check if cache file exists and is within TTL."""
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=ttl_hours)


def cache_load(
    source: str,
    identifier: str,
    start: str,
    end: str,
    fetcher,
    refresh: bool = False,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> pd.DataFrame:
    """Load data from cache or fetch from network.

    Args:
        source:     Data source name (e.g., 'fred', 'yfinance').
        identifier: Series/ticker ID (e.g., 'WALCL', 'QQQ').
        start:      Start date string.
        end:        End date string.
        fetcher:    Callable() -> pd.DataFrame. Called only on cache miss.
        refresh:    If True, ignore cache and re-fetch.
        ttl_hours:  Cache time-to-live in hours. Default 24.

    Returns:
        pd.DataFrame from cache or fresh fetch.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source, identifier, start, end)
    path = CACHE_DIR / key

    if not refresh and _is_cache_valid(path, ttl_hours):
        logger.info("Cache HIT: %s (%s)", identifier, path.name)
        return pd.read_pickle(path)

    logger.info("Cache MISS: %s → fetching from %s...", identifier, source)
    df = fetcher()
    df.to_pickle(path)
    logger.info("Cached: %s → %s (%d rows)", identifier, path.name, len(df))
    return df


def clear_cache() -> int:
    """Delete all cached files. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.glob("*.pkl"):
        f.unlink()
        count += 1
    logger.info("Cache cleared: %d files deleted", count)
    return count
