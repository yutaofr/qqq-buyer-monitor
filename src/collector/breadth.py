"""NYSE market breadth data collector."""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)

# Candidate breadth tickers, tried in order.
# ^ADD  = NYSE net advances minus declines (daily), still active on Yahoo Finance.
# ^ADDN = Nasdaq equivalent, used as secondary candidate.
_BREADTH_CANDIDATES = ["^ADD", "^ADDN"]


def fetch_breadth(as_of: date | None = None) -> dict:
    """
    Fetch NYSE market breadth indicators.

    Strategy (in priority order):
    1. Try ^ADD (NYSE advance-decline daily net value) to derive adv/dec ratio.
    2. Fall back to QQQ 5-day return proxy if all breadth tickers fail.

    Returns:
        {
            "adv_dec_ratio": float,    # 0.0-1.0; >0.5 = more advances
            "pct_above_50d": float,    # proxy: 0.0-1.0
        }
    """
    target_date = as_of or date.today()
    # yfinance end date is exclusive. Query up to target_date + 1.
    query_end = target_date + timedelta(days=1)
    query_start = target_date - timedelta(days=10)

    adv_dec_ratio = _fetch_adv_dec_ratio(query_start, query_end)
    pct_above_50d = _fetch_pct_above_50d_proxy(query_end)
    ndx_concentration = _fetch_ndx_concentration(query_end)

    logger.debug(
        "Breadth: adv_dec_ratio=%.3f pct_above_50d=%.3f ndx_concentration=%.3f as_of=%s",
        adv_dec_ratio, pct_above_50d, ndx_concentration, target_date
    )
    return {
        "adv_dec_ratio": adv_dec_ratio,
        "pct_above_50d": pct_above_50d,
        "ndx_concentration": ndx_concentration
    }


def _fetch_adv_dec_ratio(start: date, end: date) -> float:
    """
    Derive an advance/decline ratio from available breadth tickers.
    """
    yf_logger = logging.getLogger("yfinance")

    for ticker in _BREADTH_CANDIDATES:
        try:
            # Silence yfinance's own ERROR/WARNING for known-bad tickers
            prev_level = yf_logger.level
            yf_logger.setLevel(logging.CRITICAL)
            hist = yf.Ticker(ticker).history(
                start=start.isoformat(), end=end.isoformat()
            )
            yf_logger.setLevel(prev_level)

            if not hist.empty:
                net = float(hist["Close"].iloc[-1])
                ratio = 1.0 / (1.0 + math.exp(-net / 1500.0))
                logger.debug(
                    "Breadth ratio from %s: net=%.0f ratio=%.3f", ticker, net, ratio
                )
                return ratio
        except Exception as exc:  # noqa: BLE001
            yf_logger.setLevel(logging.WARNING)  # restore on exception too
            logger.debug("Ticker %s unavailable: %s", ticker, exc)

    # All tickers failed: derive proxy from QQQ 5-day return
    logger.warning(
        "All breadth tickers unavailable %s; using QQQ return proxy. query_end=%s",
        _BREADTH_CANDIDATES, end
    )
    # The 'end' passed here is already query_end (target_date + 1).
    # We want to use target_date for the proxy, which is end - 1.
    target_date = end - timedelta(days=1)
    return _proxy_ratio_from_qqq_change(target_date)


def _proxy_ratio_from_qqq_change(as_of: date) -> float:
    """
    Fallback: use QQQ's 5-day return to infer market direction.
    """
    # yfinance end date is exclusive. Query up to target_date + 1.
    query_end = as_of + timedelta(days=1)
    start = as_of - timedelta(days=10)
    try:
        hist = yf.Ticker("QQQ").history(start=start.isoformat(), end=query_end.isoformat())
        if len(hist) >= 2:
            ref_idx = min(5, len(hist) - 1)
            ret = (float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[-ref_idx])) / float(
                hist["Close"].iloc[-ref_idx]
            )
            if ret > 0.01:
                return 0.65
            elif ret < -0.01:
                return 0.40
            return 0.55
    except Exception as exc:  # noqa: BLE001
        logger.debug("QQQ proxy ratio failed: %s", exc)
    return 0.55  # neutral — won't trigger any Tier-1 threshold


def _fetch_pct_above_50d_proxy(as_of: date) -> float:
    """
    Proxy for % of stocks above 50-day MA.
    Note: as_of passed here is already query_end (target_date + 1).
    """
    # yfinance end date is exclusive. We use query_end (which is already target_date + 1).
    query_end = as_of
    start = query_end - timedelta(days=90)
    try:
        hist = yf.Ticker("QQQ").history(
            start=start.isoformat(), end=query_end.isoformat()
        )
        if not hist.empty:
            close = float(hist["Close"].iloc[-1])
            ma50 = float(hist["Close"].rolling(50, min_periods=40).mean().iloc[-1])
            deviation = (close - ma50) / ma50
            if deviation > 0.05:
                return 0.65
            elif deviation < -0.05:
                return 0.20
            return 0.40
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not compute pct_above_50d proxy: %s", exc)
    return 0.40

def _fetch_ndx_concentration(as_of: date) -> float:
    """
    Calculate the divergence between QQQ (Cap-Weighted) and QQEW (Equal-Weighted).
    Returns the difference in percentage deviation from their respective 50-day MAs.
    A positive value means QQQ is outperforming QQEW (high concentration).
    """
    query_end = as_of
    start = query_end - timedelta(days=90)
    try:
        def get_dev(ticker: str) -> float | None:
            hist = yf.Ticker(ticker).history(start=start.isoformat(), end=query_end.isoformat())
            if not hist.empty:
                close = float(hist["Close"].iloc[-1])
                ma50 = float(hist["Close"].rolling(50, min_periods=40).mean().iloc[-1])
                return (close - ma50) / ma50
            return None

        qqq_dev = get_dev("QQQ")
        qqew_dev = get_dev("QQEW")

        if qqq_dev is not None and qqew_dev is not None:
            spread = qqq_dev - qqew_dev
            return spread

    except Exception as exc:
        logger.warning("Could not compute NDX concentration proxy: %s", exc)

    return 0.0
