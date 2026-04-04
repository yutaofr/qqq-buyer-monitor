"""CNN Fear & Greed Index collector."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
TIMEOUT = 10


def fetch_fear_greed() -> int:
    """
    Fetch the latest CNN Fear & Greed Index score (0-100).

    Uses CNN's internal JSON API endpoint, which is more stable than
    scraping the HTML page directly.

    Returns:
        Integer score 0-100, where 0=Extreme Fear, 100=Extreme Greed.

    Raises:
        RuntimeError if data cannot be fetched or parsed.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }

    try:
        resp = requests.get(CNN_FG_URL, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch Fear & Greed data: {exc}") from exc

    try:
        data = resp.json()
        score = data["fear_and_greed"]["score"]
        value = int(round(float(score)))
        logger.debug("Fear & Greed: %d", value)
        return value
    except (KeyError, ValueError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Fear & Greed API response structure: {exc}\n"
            f"Response snippet: {resp.text[:300]}"
        ) from exc
