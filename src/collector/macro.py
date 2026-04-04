import io
import logging
import os
import subprocess
import time
from collections.abc import Sequence

import pandas as pd
import requests

from src.collector.treasury import fetch_treasury_yields

logger = logging.getLogger(__name__)

FRED_HISTORY_START = os.getenv("FRED_HISTORY_START", "1990-01-01")
FRED_CSV_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
    f"&mode=fred&cosd={FRED_HISTORY_START}&coed=9999-12-31"
    "&fq=Daily&fam=avg&transformation=lin"
)


def fetch_fred_api(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Fetch FRED data using the official API (JSON format)."""
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key or api_key == "your_fred_api_key_here":
        return None

    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json"
    try:
        logger.debug("Fetching FRED %s via API...", series_id)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        observations = data.get("observations", [])
        if not observations:
            return None

        df = pd.DataFrame(observations)
        df = df.rename(columns={"date": "observation_date", "value": series_id})
        # Ensure numeric conversion
        df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
        return df[["observation_date", series_id]]
    except Exception as exc:
        logger.warning("FRED API fetch failed for %s: %s", series_id, exc)
        return None


def fetch_fred_data(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Unified FRED fetcher: API first, then CSV fallback."""
    # 1. API
    df = fetch_fred_api(series_id, timeout)
    if df is not None and not df.empty:
        return df

    # 2. CSV Fallback
    logger.info(
        "Official FRED API failed or no key; falling back to CSV scraping for %s...", series_id
    )
    return fetch_fred_csv(series_id, timeout)


def normalize_fred_history_frame(df: pd.DataFrame | None, series_id: str) -> pd.DataFrame:
    """Normalize a historical FRED series frame to the canonical research shape."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["observation_date", series_id])

    frame = df.copy()
    if "observation_date" not in frame.columns:
        for candidate in ("date", "DATE"):
            if candidate in frame.columns:
                frame = frame.rename(columns={candidate: "observation_date"})
                break

    if "observation_date" not in frame.columns:
        raise ValueError(f"FRED frame for {series_id} is missing observation_date")
    if series_id not in frame.columns:
        raise ValueError(f"FRED frame for {series_id} is missing {series_id}")

    frame = frame.loc[:, ["observation_date", series_id]].copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame[series_id] = pd.to_numeric(frame[series_id], errors="coerce")
    frame = frame.dropna(subset=["observation_date"]).sort_values("observation_date")
    frame = frame.drop_duplicates(subset=["observation_date"], keep="last").reset_index(drop=True)
    return frame


def fetch_historical_fred_series(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """
    Fetch a full historical FRED series for research use.

    This path is intentionally limited to FRED transport only. It does not call
    the runtime heuristic fallbacks used by live signal collection.
    """
    raw = fetch_fred_data(series_id, timeout)
    normalized = normalize_fred_history_frame(raw, series_id)
    return normalized if not normalized.empty else None


def fetch_historical_fred_series_bundle(
    series_ids: Sequence[str], timeout: int = 15
) -> dict[str, pd.DataFrame]:
    """Fetch multiple historical FRED series and return normalized frames keyed by series id."""
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for series_id in series_ids:
        frame = fetch_historical_fred_series(series_id, timeout)
        if frame is None or frame.empty:
            missing.append(series_id)
            continue
        frames[series_id] = frame
    if missing:
        raise ValueError(f"Missing historical FRED series: {', '.join(missing)}")
    return frames


def _fetch_fred_csv_via_curl(url: str, timeout: int) -> pd.DataFrame | None:
    try:
        completed = subprocess.run(
            ["curl", "-sS", "--max-time", str(timeout), url],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout + 5,
        )
        return pd.read_csv(io.StringIO(completed.stdout), na_values=".")
    except Exception as exc:  # noqa: BLE001
        logger.warning("curl fallback failed for FRED url %s: %s", url, exc)
        return None


def fetch_fred_csv(series_id: str, timeout: int = 15, retries: int = 3) -> pd.DataFrame | None:
    """Helper to fetch FRED CSV data with timeout and retries."""
    url = FRED_CSV_URL.format(series_id)
    # Using a very standard browser user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/csv,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    for attempt in range(retries + 1):
        try:
            logger.debug("Fetching FRED %s (attempt %d)...", series_id, attempt + 1)
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return pd.read_csv(io.StringIO(response.text), na_values=".")
        except Exception as exc:
            curl_frame = _fetch_fred_csv_via_curl(url, timeout)
            if curl_frame is not None:
                return curl_frame
            if attempt < retries:
                logger.debug(
                    "FRED %s fetch attempt %d failed: %s. Retrying in 2s...",
                    series_id,
                    attempt + 1,
                    exc,
                )
                time.sleep(2)  # Shorter wait between retries
            else:
                logger.warning(
                    "Failed to fetch FRED %s after %d retries: %s", series_id, retries + 1, exc
                )
    return None


def fetch_chicago_fed_nfci() -> float | None:
    """
    Fetch the National Financial Conditions Index (NFCI) from Chicago Fed.
    URL: https://www.chicagofed.org/~/media/publications/nfci/nfci-indexes-csv.csv
    Returns the latest NFCI value (Positive = tighter/stressed, Negative = looser/calm).
    """
    url = "https://www.chicagofed.org/-/media/publications/nfci/nfci-indexes-csv.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        # The Chicago Fed CSV has some header rows; find where the data starts
        content = response.text
        lines = content.splitlines()

        # Look for the line starting with 'Date' which is the header
        header_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Date"):
                header_idx = i
                break

        if header_idx == -1:
            return None

        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
        if df.empty:
            return None

        # NFCI is usually the second column
        latest_val = float(df.iloc[-1]["NFCI"])
        logger.info("Fetched NFCI from Chicago Fed: %.3f", latest_val)

        # NFCI is a standard deviation index. To "proxy" it as a spread (bps) for our engine:
        # A value of 0 is neutral. A value of 1.0 is high stress.
        # Map 0 -> 350 bps (neutral spread), 1.0 -> 600 bps (stressed spread)
        return 350.0 + (latest_val * 250.0)
    except Exception as exc:
        logger.debug("Chicago Fed NFCI fetch failed: %s", exc)
        return None


def fetch_hyg_proxy() -> float | None:
    """
    Fallback: Use HYG (High Yield ETF) as a proxy for credit spreads.
    Lower HYG relative to its 200d MA implies widening spreads.
    """
    import yfinance as yf

    try:
        hyg = yf.Ticker("HYG")
        hist = hyg.history(period="1y")
        if hist.empty:
            return None

        price = float(hist["Close"].iloc[-1])
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1])

        # If HYG is 5% below its 200d MA, spreads are likely widening (bullish contrarian signal).
        # We return a synthetic "spread" to keep the engine happy.
        # price == ma200 -> 350 bps
        # price == 0.95 * ma200 -> 500 bps
        deviation = (ma200 - price) / ma200
        synthetic_spread = 350.0 + (deviation * 3000.0)
        logger.info(
            "Fetched HYG proxy spread: %.0f bps (deviation from MA200: %.2f%%)",
            synthetic_spread,
            deviation * 100,
        )
        return synthetic_spread
    except Exception as exc:
        logger.debug("HYG proxy fetch failed: %s", exc)
        return None


def fetch_credit_spread_snapshot(
    series_id: str = "BAMLH0A0HYM2",
) -> dict[str, float | str | bool | None]:
    """
    Fetch the latest Ice BofA US High Yield Index Option-Adjusted Spread.
    1. Primary: FRED
    2. Fallback: Chicago Fed NFCI
    3. Fallback: Treasury Yield Curve Inversion (Proxy for stress)
    4. Fallback: HYG Proxy
    """
    # 1. FRED
    try:
        df = fetch_fred_data(series_id)
        if df is not None and not df.empty:
            df = df.dropna(subset=[series_id])
            if not df.empty:
                latest_val = float(df.iloc[-1][series_id])
                return {
                    "value": latest_val * 100,
                    "source": f"fred:{series_id}",
                    "degraded": False,
                }
    except Exception as exc:
        logger.debug("Error processing FRED %s: %s", series_id, exc)

    # 2. Chicago Fed NFCI Fallback
    logger.info("FRED unavailable; attempting Chicago Fed NFCI fallback...")
    nfci_val = fetch_chicago_fed_nfci()
    if nfci_val is not None:
        return {
            "value": nfci_val,
            "source": "proxy:nfci",
            "degraded": True,
        }

    # 3. Treasury Inversion Fallback
    logger.info("Chicago Fed unavailable; attempting Treasury Yield Curve fallback...")
    try:
        yields = fetch_treasury_yields()
        if yields["10Y"] is not None and yields["3M"] is not None:
            # Simple proxy: 10Y - 3M inversion.
            # Inversion (10Y < 3M) signals extreme stress.
            # Normal: 100 bps spread. Inverted: -100 bps spread.
            # Map Normal (100) -> 350 bps credit spread, Inverted (-100) -> 600 bps.
            yc_spread = yields["10Y"] - yields["3M"]
            synthetic_spread = 350.0 + (1.0 - yc_spread) * 125.0
            logger.info(
                "Fetched Treasury proxy spread: %.0f bps (YC Spread: %.2f%%)",
                synthetic_spread,
                yc_spread,
            )
            return {
                "value": synthetic_spread,
                "source": "proxy:treasury_curve",
                "degraded": True,
            }
    except Exception as exc:
        logger.debug("Treasury fallback failed: %s", exc)

    # 4. HYG Proxy Fallback
    logger.info("Treasury unavailable; attempting HYG proxy fallback...")
    hyg_val = fetch_hyg_proxy()
    if hyg_val is not None:
        return {
            "value": hyg_val,
            "source": "proxy:hyg",
            "degraded": True,
        }
    return {
        "value": None,
        "source": "unavailable:credit_spread",
        "degraded": True,
    }


def fetch_credit_spread(series_id: str = "BAMLH0A0HYM2") -> float | None:
    snapshot = fetch_credit_spread_snapshot(series_id)
    value = snapshot.get("value")
    return float(value) if value is not None else None
