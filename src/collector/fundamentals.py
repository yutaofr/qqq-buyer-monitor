import logging

import yfinance as yf

logger = logging.getLogger(__name__)

# Institutional benchmarks for QQQ (Nasdaq 100)
# Sources like FactSet/WSJ show Forward PE around 24x-26x
# YFinance often reports 30x+ due to different EPS definitions.
INSTITUTIONAL_PE_ESTIMATE = 24.38  # Birinyi Associates via WSJ (2026-03-06)


def fetch_forward_pe(ticker: str = "QQQ") -> dict:
    """
    Fetch trailing and forward PE ratios.
    Combines yfinance with institutional consensus logic.
    """
    result = {"trailing_pe": None, "forward_pe": None, "source": "direct:yfinance"}

    # 1. Primary: yfinance
    try:
        q = yf.Ticker(ticker)
        info = q.info
        result["trailing_pe"] = info.get("trailingPE")
        result["forward_pe"] = info.get("forwardPE")
    except Exception as exc:
        logger.warning("yfinance fetch failed: %s", exc)

    # 2. Institutional Check / Sanitization
    # If yfinance is outlier (>31 when consensus is ~25), we flag it or provide institutional overlay
    if result["forward_pe"] and result["forward_pe"] > 31.0:
        logger.info(
            "yfinance PE (%s) seems like an outlier compared to institutional consensus (~25x). Using institutional override.",
            result["forward_pe"],
        )
        result["forward_pe_raw"] = result["forward_pe"]
        result["forward_pe"] = INSTITUTIONAL_PE_ESTIMATE
        result["source"] = "fallback:institutional_consensus"

    # 3. Final Fallback if yfinance is None
    if result["forward_pe"] is None:
        result["forward_pe"] = INSTITUTIONAL_PE_ESTIMATE
        result["source"] = "fallback:institutional_fallback"

    return result
