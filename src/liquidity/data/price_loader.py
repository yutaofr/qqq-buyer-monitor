"""Price data loader for the liquidity pipeline.

Loads OHLC for QQQ, QLD, TLT and a proxy NDX universe with:
  - vintage roster masking (time-bounded proxy membership)
  - listing-age gate
  - as-of liquidity filtering

Network calls are isolated here. Unit tests must NOT import this module
without mocking yfinance.
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_VINTAGE_ROSTER_PATH = Path(__file__).parent.parent / "resources" / "ndx_proxy_vintages.csv"
_ROSTER_COLUMNS = ["effective_from", "effective_to", "ticker"]
_YF_CACHE_DIR = Path(".cache/liquidity/yfinance")
_YF_FIELDS = ["Open", "Close", "Volume"]


def load_proxy_vintage_roster(path: str | Path | None = None) -> pd.DataFrame:
    """Load the time-bounded proxy universe roster.

    The roster is intentionally coarse-grained. It is not a true daily PiT
    constituent feed, but it prevents the grossest survivorship leak by
    excluding future listings from earlier eras.
    """
    roster_path = Path(path) if path is not None else _VINTAGE_ROSTER_PATH
    roster = pd.read_csv(roster_path, parse_dates=["effective_from", "effective_to"])
    missing = set(_ROSTER_COLUMNS) - set(roster.columns)
    if missing:
        raise ValueError(f"Vintage roster missing required columns: {sorted(missing)}")
    roster["ticker"] = roster["ticker"].astype(str)
    return roster.loc[:, _ROSTER_COLUMNS].sort_values(["effective_from", "ticker"]).reset_index(drop=True)


def select_active_proxy_tickers(
    roster: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> list[str]:
    """Return the union of tickers whose vintage interval overlaps the request."""
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    active = roster[
        (roster["effective_from"] <= end_ts)
        & (roster["effective_to"] >= start_ts)
    ]
    return sorted(active["ticker"].unique().tolist())


def _normalise_index(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.index = frame.index.normalize()
    if hasattr(frame.index, "tz") and frame.index.tz is not None:
        frame.index = frame.index.tz_localize(None)
    return frame


def _cache_path(cache_dir: Path, ticker: str, start_date: str, end_date: str) -> Path:
    return cache_dir / f"{ticker}_{start_date}_{end_date}.pkl"


def _read_ticker_cache(cache_dir: Path, ticker: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    path = _cache_path(cache_dir, ticker, start_date, end_date)
    if not path.exists():
        return None
    frame = pd.read_pickle(path)
    return _normalise_index(frame)


def _write_ticker_cache(
    cache_dir: Path,
    ticker: str,
    start_date: str,
    end_date: str,
    frame: pd.DataFrame,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _normalise_index(frame).to_pickle(_cache_path(cache_dir, ticker, start_date, end_date))


def _chunked(items: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("chunk_size must be >= 1.")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _extract_ticker_history(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        if ticker not in data.columns.get_level_values(0):
            return pd.DataFrame()
        df = data[ticker].copy()
    else:
        df = data.copy()

    wanted = [field for field in _YF_FIELDS if field in df.columns]
    if not wanted:
        return pd.DataFrame()
    df = _normalise_index(df[wanted])
    return df.rename(columns={field: f"{ticker}_{field}" for field in wanted})


def _download_chunk_with_retry(
    tickers: list[str],
    start_date: str,
    end_date: str,
    max_retries: int,
    base_delay_seconds: float,
    jitter_seconds: float,
) -> pd.DataFrame:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return yf.download(
                tickers,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
            )
        except Exception as exc:  # pragma: no cover - exercised via tests/real network only
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = base_delay_seconds * (2**attempt) + random.uniform(0.0, jitter_seconds)
            logger.warning(
                "yfinance chunk fetch failed for %s on attempt %d/%d: %s. Retrying in %.2fs",
                tickers,
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Failed to fetch yfinance chunk {tickers} after {max_retries + 1} attempts"
    ) from last_exc


def _download_single_ticker_with_retry(
    ticker: str,
    start_date: str,
    end_date: str,
    max_retries: int,
    base_delay_seconds: float,
    jitter_seconds: float,
) -> pd.DataFrame:
    return _download_chunk_with_retry(
        [ticker],
        start_date,
        end_date,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        jitter_seconds=jitter_seconds,
    )


def _fetch_price_history_ensemble_with_diagnostics(
    tickers: list[str],
    start_date: str,
    end_date: str,
    *,
    chunk_size: int,
    max_retries: int,
    base_delay_seconds: float,
    jitter_seconds: float,
    cache_dir: Path | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    """Fetch ticker histories using chunked network calls and per-ticker cache."""
    cache_root = cache_dir if cache_dir is not None else _YF_CACHE_DIR
    requested = list(dict.fromkeys(tickers))
    results: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    cached_tickers: list[str] = []
    downloaded_tickers: list[str] = []
    failed_tickers: list[str] = []
    chunk_failures: list[list[str]] = []

    for ticker in requested:
        cached = _read_ticker_cache(cache_root, ticker, start_date, end_date)
        if cached is not None and not cached.empty:
            results[ticker] = cached
            cached_tickers.append(ticker)
        else:
            missing.append(ticker)

    for chunk in _chunked(missing, chunk_size):
        try:
            payload = _download_chunk_with_retry(
                chunk,
                start_date,
                end_date,
                max_retries=max_retries,
                base_delay_seconds=base_delay_seconds,
                jitter_seconds=jitter_seconds,
            )
        except RuntimeError as exc:
            logger.warning("Chunk %s failed permanently: %s", chunk, exc)
            payload = pd.DataFrame()
            chunk_failures.append(list(chunk))

        empty_tickers: list[str] = []
        for ticker in chunk:
            ticker_frame = _extract_ticker_history(payload, ticker)
            if ticker_frame.empty:
                empty_tickers.append(ticker)
                continue
            results[ticker] = ticker_frame
            downloaded_tickers.append(ticker)
            _write_ticker_cache(cache_root, ticker, start_date, end_date, ticker_frame)

        for ticker in empty_tickers:
            try:
                single_payload = _download_single_ticker_with_retry(
                    ticker,
                    start_date,
                    end_date,
                    max_retries=max_retries,
                    base_delay_seconds=base_delay_seconds,
                    jitter_seconds=jitter_seconds,
                )
            except RuntimeError as exc:
                logger.warning(
                    "Single-ticker fallback failed for %s in [%s, %s]: %s",
                    ticker,
                    start_date,
                    end_date,
                    exc,
                )
                failed_tickers.append(ticker)
                continue

            ticker_frame = _extract_ticker_history(single_payload, ticker)
            if ticker_frame.empty:
                logger.warning(
                    "No usable yfinance payload for ticker %s in [%s, %s]",
                    ticker,
                    start_date,
                    end_date,
                )
                failed_tickers.append(ticker)
                continue
            results[ticker] = ticker_frame
            downloaded_tickers.append(ticker)
            _write_ticker_cache(cache_root, ticker, start_date, end_date, ticker_frame)

    diagnostics = {
        "requested_tickers": requested,
        "cached_tickers": sorted(cached_tickers),
        "downloaded_tickers": sorted(downloaded_tickers),
        "failed_tickers": sorted(set(failed_tickers)),
        "chunk_failures": chunk_failures,
    }
    return results, diagnostics


def _fetch_price_history_ensemble(
    tickers: list[str],
    start_date: str,
    end_date: str,
    *,
    chunk_size: int,
    max_retries: int,
    base_delay_seconds: float,
    jitter_seconds: float,
    cache_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    results, _ = _fetch_price_history_ensemble_with_diagnostics(
        tickers,
        start_date,
        end_date,
        chunk_size=chunk_size,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        jitter_seconds=jitter_seconds,
        cache_dir=cache_dir,
    )
    return results


def _extract_panel_field(data: pd.DataFrame, tickers: list[str], field: str) -> pd.DataFrame:
    """Extract a single field (Close/Volume) from yfinance's panel layout."""
    if len(tickers) == 1:
        series = data[field] if field in data.columns else pd.Series(dtype=float)
        frame = pd.DataFrame({tickers[0]: series})
    else:
        frame = pd.DataFrame({
            ticker: data[ticker][field]
            if ticker in data.columns.get_level_values(0) and field in data[ticker].columns
            else pd.Series(dtype=float)
            for ticker in tickers
        })
    return _normalise_index(frame)


def _build_roster_mask(
    index: pd.DatetimeIndex,
    tickers: list[str],
    roster: pd.DataFrame,
) -> pd.DataFrame:
    """Boolean mask of ticker eligibility implied by vintage intervals."""
    mask = pd.DataFrame(False, index=index, columns=tickers)
    for row in roster.itertuples(index=False):
        if row.ticker not in mask.columns:
            continue
        start = max(pd.Timestamp(row.effective_from), index[0])
        end = min(pd.Timestamp(row.effective_to), index[-1])
        if start > end:
            continue
        mask.loc[start:end, row.ticker] = True
    return mask


def _build_listing_age_mask(
    closes: pd.DataFrame,
    min_listing_days: int,
) -> pd.DataFrame:
    """Ticker becomes eligible only after enough valid observations accrue."""
    if min_listing_days <= 0:
        return pd.DataFrame(True, index=closes.index, columns=closes.columns)
    valid_counts = closes.notna().cumsum(axis=0)
    return valid_counts >= min_listing_days


def _build_liquidity_mask(
    closes: pd.DataFrame,
    volumes: pd.DataFrame,
    liquidity_lookback: int,
    top_n: int,
) -> pd.DataFrame:
    """Keep only the most liquid names using trailing dollar volume."""
    if top_n < 1:
        raise ValueError("top_n must be >= 1.")
    if liquidity_lookback <= 0:
        return pd.DataFrame(True, index=closes.index, columns=closes.columns)

    dollar_volume = closes * volumes
    trailing_liquidity = dollar_volume.rolling(
        window=liquidity_lookback,
        min_periods=liquidity_lookback,
    ).mean()
    ranks = trailing_liquidity.rank(
        axis=1,
        ascending=False,
        method="first",
        na_option="bottom",
    )
    return trailing_liquidity.notna() & (ranks <= top_n)


def load_ohlc(
    tickers: list[str],
    start_date: str,
    end_date: str,
    chunk_size: int = 10,
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    jitter_seconds: float = 0.25,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLC DataFrames for a list of tickers.

    Args:
        tickers:    List of ticker symbols (e.g., ['QQQ', 'QLD', 'TLT']).
        start_date: ISO date string.
        end_date:   ISO date string.

    Returns:
        Dict[ticker → DataFrame] with columns [Open, High, Low, Close, Volume].
        Raises RuntimeError if any ticker is missing.
    """
    history = _fetch_price_history_ensemble(
        tickers,
        start_date,
        end_date,
        chunk_size=chunk_size,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        jitter_seconds=jitter_seconds,
    )

    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        df = history.get(ticker, pd.DataFrame())
        if df.empty:
            raise RuntimeError(
                f"No OHLC data returned for '{ticker}' "
                f"in range [{start_date}, {end_date}]."
            )
        result[ticker] = df[[f"{ticker}_Open", f"{ticker}_Close"]]

    return result


def load_constituent_returns_with_diagnostics(
    start_date: str,
    end_date: str,
    tickers: list[str] | None = None,
    top_n: int = 50,
    roster: pd.DataFrame | None = None,
    min_listing_days: int = 63,
    liquidity_lookback: int = 60,
    chunk_size: int = 10,
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    jitter_seconds: float = 0.25,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Fetch daily returns for the proxy NDX universe.

    Returns:
        Tuple of:
          - DataFrame[date × ticker] of daily close-to-close returns with
            dynamic NaNs for names excluded by the vintage roster,
            listing-age gate, or as-of liquidity filter.
          - Diagnostics dict including valid_names time series and loader audit.
        First row is dropped after pct_change.
    """
    active_roster = roster if roster is not None else load_proxy_vintage_roster()
    if tickers is None:
        tickers = select_active_proxy_tickers(active_roster, start_date, end_date)
    tickers = sorted(dict.fromkeys(tickers))
    if not tickers:
        raise RuntimeError(f"No active proxy universe tickers for [{start_date}, {end_date}].")

    history, audit = _fetch_price_history_ensemble_with_diagnostics(
        tickers,
        start_date,
        end_date,
        chunk_size=chunk_size,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        jitter_seconds=jitter_seconds,
    )
    if not history:
        raise RuntimeError(
            f"No constituent data returned for [{start_date}, {end_date}]."
        )

    closes = pd.DataFrame(
        {
            ticker: frame.get(f"{ticker}_Close", pd.Series(dtype=float))
            for ticker, frame in history.items()
        }
    )
    volumes = pd.DataFrame(
        {
            ticker: frame.get(f"{ticker}_Volume", pd.Series(dtype=float))
            for ticker, frame in history.items()
        }
    )
    closes = _normalise_index(closes)
    volumes = _normalise_index(volumes)
    closes = closes.reindex(columns=tickers)
    volumes = volumes.reindex(columns=tickers)
    returns = closes.pct_change(fill_method=None)

    roster_mask = _build_roster_mask(returns.index, tickers, active_roster)
    listing_mask = _build_listing_age_mask(closes, min_listing_days=min_listing_days)
    liquidity_mask = _build_liquidity_mask(
        closes,
        volumes,
        liquidity_lookback=liquidity_lookback,
        top_n=top_n,
    )
    eligibility_mask = roster_mask & listing_mask & liquidity_mask
    returns = returns.where(eligibility_mask).iloc[1:]  # drop first pct_change NaN row
    valid_names = returns.notna().sum(axis=1).astype(int).rename("ED_VALID_NAMES")
    available_names = closes.notna().iloc[1:].sum(axis=1).astype(int).rename("AVAILABLE_NAMES")

    diagnostics = {
        **audit,
        "loaded_tickers": sorted(history.keys()),
        "available_names": available_names,
        "valid_names": valid_names,
    }

    logger.debug(
        "Loaded proxy constituent returns: %d requested stocks × %d days [%s → %s]",
        len(tickers),
        len(returns),
        start_date,
        end_date,
    )
    return returns, diagnostics


def load_constituent_returns(
    start_date: str,
    end_date: str,
    tickers: list[str] | None = None,
    top_n: int = 50,
    roster: pd.DataFrame | None = None,
    min_listing_days: int = 63,
    liquidity_lookback: int = 60,
    chunk_size: int = 10,
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    jitter_seconds: float = 0.25,
) -> pd.DataFrame:
    returns, _ = load_constituent_returns_with_diagnostics(
        start_date,
        end_date,
        tickers=tickers,
        top_n=top_n,
        roster=roster,
        min_listing_days=min_listing_days,
        liquidity_lookback=liquidity_lookback,
        chunk_size=chunk_size,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        jitter_seconds=jitter_seconds,
    )
    return returns
