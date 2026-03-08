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
    end = as_of or date.today()
    start = end - timedelta(days=10)

    adv_dec_ratio = _fetch_adv_dec_ratio(start, end)
    pct_above_50d = _fetch_pct_above_50d_proxy(end)

    logger.debug(
        "Breadth: adv_dec_ratio=%.3f pct_above_50d=%.3f",
        adv_dec_ratio, pct_above_50d,
    )
    return {"adv_dec_ratio": adv_dec_ratio, "pct_above_50d": pct_above_50d}


def _fetch_adv_dec_ratio(start: date, end: date) -> float:
    """
    Derive an advance/decline ratio from available breadth tickers.

    ^ADD gives the daily net (advances - declines). We convert to a
    bounded ratio using a sigmoid so the Tier-1 thresholds apply cleanly:

        ratio = sigmoid(net / scale)

    With scale=1500 (typical single-day |ADD| range ≈ 500–3000):
        net = +3000  →  ratio ≈ 0.87  (very broad advance)
        net =     0  →  ratio = 0.50  (neutral)
        net = -3000  →  ratio ≈ 0.13  (very broad decline / capitulation)
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
        "All breadth tickers unavailable %s; using QQQ return proxy.", _BREADTH_CANDIDATES
    )
    return _proxy_ratio_from_qqq_change(end)


def _proxy_ratio_from_qqq_change(as_of: date) -> float:
    """
    Fallback: use QQQ's 5-day return to infer market direction.
        QQQ up >1%   → ratio 0.65  (probably more advances than declines)
        QQQ flat     → ratio 0.55  (neutral, won't trigger thresholds)
        QQQ down >1% → ratio 0.40  (probably more declines)
    """
    start = as_of - timedelta(days=10)
    try:
        hist = yf.Ticker("QQQ").history(start=start.isoformat(), end=as_of.isoformat())
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

    Uses QQQ's deviation from its own 50-day MA:
        QQQ > MA50 by >5%   → 0.65  (broad rally)
        QQQ within ±5%      → 0.40  (mixed)
        QQQ < MA50 by >5%   → 0.20  (broad weakness / capitulation)
    """
    start = as_of - timedelta(days=80)
    try:
        hist = yf.Ticker("QQQ").history(
            start=start.isoformat(), end=as_of.isoformat()
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
