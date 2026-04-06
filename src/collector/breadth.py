"""NYSE market breadth data collector."""

from __future__ import annotations

import json
import logging
import math
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)

# Candidate breadth tickers, tried in order.
# ^ADD  = NYSE net advances minus declines (daily), still active on Yahoo Finance.
# ^ADDN = Nasdaq equivalent, used as secondary candidate.
_BREADTH_CANDIDATES = ["^ADD", "^ADDN"]


@lru_cache(maxsize=1)
def _load_v13_collector_policy() -> dict:
    audit_path = (
        Path(__file__).resolve().parents[1]
        / "engine"
        / "v13"
        / "resources"
        / "execution_overlay_audit.json"
    )
    if not audit_path.exists():
        return {"breadth_sigmoid_scale": 1500.0}
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"breadth_sigmoid_scale": 1500.0}
    return dict(payload.get("collector_policy", {}))


def fetch_breadth(as_of: date | None = None) -> dict:
    """
    Fetch NYSE market breadth indicators.

    Strategy (in priority order):
    1. Try ^ADD (NYSE advance-decline daily net value) to derive adv/dec ratio.
    2. If all breadth tickers fail, return an explicit unavailable marker.

    Returns:
        {
            "adv_dec_ratio": float,    # 0.0-1.0; >0.5 = more advances
            "pct_above_50d": float,    # neutral placeholder when breadth is unavailable
            "source": str,
            "quality": float,
            "transform": str,
            "ndx_concentration": float | None,
            "ndx_concentration_source": str,
            "ndx_concentration_quality": float,
            "observed": bool,
        }
    """
    target_date = as_of or date.today()
    # yfinance end date is exclusive. Query up to target_date + 1.
    query_end = target_date + timedelta(days=1)
    query_start = target_date - timedelta(days=10)

    ndx_concentration, ndx_concentration_source, ndx_concentration_quality = (
        _fetch_ndx_concentration(query_end)
    )
    adv_dec_ratio, source, quality, transform = _fetch_adv_dec_ratio(query_start, query_end)
    if quality <= 0.0:
        proxy_ratio = _derive_proxy_breadth_from_concentration(ndx_concentration)
        if proxy_ratio is not None:
            adv_dec_ratio = proxy_ratio
            source = "derived:qqq-qqew-breadth"
            quality = 0.55
            transform = "sigmoid(-ndx_concentration/0.08)"
    pct_above_50d = adv_dec_ratio if quality > 0.0 else 0.50

    logger.debug(
        "Breadth: adv_dec_ratio=%.3f pct_above_50d=%.3f ndx_concentration=%s breadth_quality=%.2f ndx_quality=%.2f source=%s ndx_source=%s as_of=%s",
        adv_dec_ratio,
        pct_above_50d,
        f"{ndx_concentration:.3f}" if ndx_concentration is not None else "None",
        quality,
        ndx_concentration_quality,
        source,
        ndx_concentration_source,
        target_date,
    )
    return {
        "adv_dec_ratio": adv_dec_ratio,
        "pct_above_50d": pct_above_50d,
        "ndx_concentration": ndx_concentration,
        "source": source,
        "quality": quality,
        "transform": transform,
        "ndx_concentration_source": ndx_concentration_source,
        "ndx_concentration_quality": ndx_concentration_quality,
        "observed": quality > 0.0,
    }


def _derive_proxy_breadth_from_concentration(ndx_concentration: float | None) -> float | None:
    if ndx_concentration is None:
        return None
    spread = float(ndx_concentration)
    if abs(spread) < 0.01:
        return None
    scale = 0.08
    return 1.0 / (1.0 + math.exp(spread / scale))


def _fetch_adv_dec_ratio(start: date, end: date) -> tuple[float, str, float, str]:
    """
    Derive an advance/decline ratio from available breadth tickers.
    """
    yf_logger = logging.getLogger("yfinance")
    collector_policy = _load_v13_collector_policy()
    sigmoid_scale = float(collector_policy.get("breadth_sigmoid_scale", 1500.0))

    for ticker in _BREADTH_CANDIDATES:
        try:
            # Silence yfinance's own ERROR/WARNING for known-bad tickers
            prev_level = yf_logger.level
            yf_logger.setLevel(logging.CRITICAL)
            hist = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat())
            yf_logger.setLevel(prev_level)

            if not hist.empty:
                net = float(hist["Close"].iloc[-1])
                ratio = 1.0 / (1.0 + math.exp(-net / sigmoid_scale))
                logger.debug("Breadth ratio from %s: net=%.0f ratio=%.3f", ticker, net, ratio)
                return ratio, f"observed:{ticker}", 1.0, f"sigmoid(scale={sigmoid_scale:.1f})"
        except Exception as exc:  # noqa: BLE001
            yf_logger.setLevel(logging.WARNING)  # restore on exception too
            logger.debug("Ticker %s unavailable: %s", ticker, exc)

    logger.warning(
        "All breadth tickers unavailable %s; marking breadth unavailable. query_end=%s",
        _BREADTH_CANDIDATES,
        end,
    )
    return 0.50, "unavailable:breadth", 0.0, "neutral_fallback"


def _fetch_ndx_concentration(as_of: date) -> tuple[float | None, str, float]:
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
            return spread, "derived:qqq-qqew", 1.0

    except Exception as exc:
        logger.warning("Could not compute NDX concentration proxy: %s", exc)

    return None, "unavailable:ndx_concentration", 0.0
