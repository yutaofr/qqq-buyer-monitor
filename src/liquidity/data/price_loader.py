"""Price data loader for the liquidity pipeline.

Loads OHLC for QQQ, QLD, TLT and NDX constituent returns (POC: top-50).
Uses yfinance directly (not through src.collector.price which returns
a dict, not a DataFrame).

Network calls are isolated here. Unit tests must NOT import this module
without mocking yfinance.
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# POC: hardcoded top-50 QQQ constituents by weight (approximate as of 2024)
# Production: replace with dynamic lookup from a constituents database
TOP50_QQQ_TICKERS = [
    "MSFT", "AAPL", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO",
    "COST", "ASML", "NFLX", "AMD", "AZN", "PEP", "LIN", "QCOM", "CSCO", "TXN",
    "BKNG", "ISRG", "AMGN", "INTU", "ARM", "HON", "PANW", "VRTX", "ADI", "CMCSA",
    "LRCX", "GILD", "MU", "SBUX", "REGN", "MELI", "KDP", "CTAS", "PDD", "AMAT",
    "KLAC", "MDLZ", "FTNT", "MAR", "CDNS", "AEP", "CSX", "PYPL", "ORLY", "SNPS",
]


def load_ohlc(
    tickers: list[str],
    start_date: str,
    end_date: str,
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
    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        if len(tickers) == 1:
            df = data  # yfinance flat structure for single ticker
        else:
            df = data[ticker] if ticker in data.columns.get_level_values(0) else pd.DataFrame()

        if df.empty:
            raise RuntimeError(
                f"No OHLC data returned for '{ticker}' "
                f"in range [{start_date}, {end_date}]."
            )

        # Normalise index: strip timezone
        df.index = df.index.normalize()
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        result[ticker] = df[["Open", "Close"]].rename(
            columns={"Open": f"{ticker}_Open", "Close": f"{ticker}_Close"}
        )

    return result


def load_constituent_returns(
    start_date: str,
    end_date: str,
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch daily returns for NDX constituents (POC: top-50 fixed list).

    Returns:
        DataFrame[date × ticker] of daily close-to-close returns.
        Index = trading days. No leading NaN (first row dropped after pct_change).
    """
    if tickers is None:
        tickers = TOP50_QQQ_TICKERS

    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    if data.empty:
        raise RuntimeError(
            f"No constituent data returned for [{start_date}, {end_date}]."
        )

    # Extract close prices per ticker
    closes = pd.DataFrame({
        t: data[t]["Close"] if t in data.columns.get_level_values(0) else pd.Series(dtype=float)
        for t in tickers
    })
    closes.index = closes.index.normalize()
    if hasattr(closes.index, "tz") and closes.index.tz is not None:
        closes.index = closes.index.tz_localize(None)

    returns = closes.pct_change().iloc[1:]  # drop first NaN row
    logger.debug(
        "Loaded constituent returns: %d stocks × %d days [%s → %s]",
        len(tickers),
        len(returns),
        start_date,
        end_date,
    )
    return returns
