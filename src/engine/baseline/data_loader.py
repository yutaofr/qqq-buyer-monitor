import logging

import pandas as pd

from src.collector.macro import fetch_fred_data

logger = logging.getLogger(__name__)

# FRED series mapping as per updated implementation plan
BASELINE_SERIES_MAP = {
    "growth_pmi": "IPMAN",
    "growth_margin_numerator": "CP",
    "growth_margin_denominator": "GDP",
    "liquidity_m2": "M2REAL",
    "liquidity_slope": "T10Y2Y",
    "stress_credit": "BAMLH0A0HYM2",
    "stress_vix": "VIXCLS",
    "stress_vxn": "^VXN",
}


def fetch_baseline_series(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Fetch and normalize a baseline FRED series."""
    raw = fetch_fred_data(series_id, timeout=timeout)
    if raw is None or raw.empty:
        logger.warning(f"Failed to fetch baseline series: {series_id}")
        return None

    # Normalize column names to match common patterns
    if "observation_date" not in raw.columns:
        for candidate in ("date", "DATE"):
            if candidate in raw.columns:
                raw = raw.rename(columns={candidate: "observation_date"})
                break

    if "observation_date" not in raw.columns:
        return None

    raw["observation_date"] = pd.to_datetime(raw["observation_date"]).dt.tz_localize(None)
    # Find the data column (it's usually the one matching the ID or "value")
    data_col = (
        series_id
        if series_id in raw.columns
        else (raw.columns[1] if len(raw.columns) > 1 else None)
    )
    if data_col:
        raw = raw.rename(columns={data_col: series_id})
    else:
        return None

    raw[series_id] = pd.to_numeric(raw[series_id], errors="coerce")
    return raw.set_index("observation_date")[[series_id]].dropna()


def get_growth_margin(timeout: int = 15) -> pd.DataFrame | None:
    """Calculate Corporate Profit Margin (CP/GDP)."""
    cp = fetch_baseline_series(BASELINE_SERIES_MAP["growth_margin_numerator"], timeout=timeout)
    gdp = fetch_baseline_series(BASELINE_SERIES_MAP["growth_margin_denominator"], timeout=timeout)

    if cp is None or gdp is None:
        return None

    merged = cp.merge(gdp, left_index=True, right_index=True, how="inner")
    margin = (
        merged[BASELINE_SERIES_MAP["growth_margin_numerator"]]
        / merged[BASELINE_SERIES_MAP["growth_margin_denominator"]]
    ) * 100.0
    return pd.DataFrame({"growth_margin": margin}, index=merged.index)


def load_all_baseline_data(timeout: int = 15) -> pd.DataFrame:
    """Fetch all baseline data and align on daily index with PIT (forward-fill)."""
    frames = []

    # 1. IPMAN (Monthly)
    ipman = fetch_baseline_series(BASELINE_SERIES_MAP["growth_pmi"], timeout=timeout)
    if ipman is not None:
        frames.append(ipman)

    # 2. Margin (Quarterly)
    margin = get_growth_margin(timeout=timeout)
    if margin is not None:
        frames.append(margin)

    # 3. M2REAL (Monthly)
    m2 = fetch_baseline_series(BASELINE_SERIES_MAP["liquidity_m2"], timeout=timeout)
    if m2 is not None:
        frames.append(m2)

    # 4. T10Y2Y (Daily)
    slope = fetch_baseline_series(BASELINE_SERIES_MAP["liquidity_slope"], timeout=timeout)
    if slope is not None:
        frames.append(slope)

    # 5. Credit Spread (Daily)
    credit = fetch_baseline_series(BASELINE_SERIES_MAP["stress_credit"], timeout=timeout)
    if credit is not None:
        frames.append(credit)

    # 6. VIX (Daily)
    vix = fetch_baseline_series(BASELINE_SERIES_MAP["stress_vix"], timeout=timeout)
    if vix is not None:
        frames.append(vix)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, axis=1).sort_index()
    # Forward-fill monthly/quarterly data to daily frequency (PIT-safe)
    return combined.ffill()


def fetch_qqq_technical_signals(start_date: str = "1999-01-01") -> pd.DataFrame:
    """
    Fetch QQQ data and calculate 50d/200d MA Cross signal.
    1 = Death Cross (50d < 200d), 0 = Golden Cross or Neutral.
    """
    import yfinance as yf

    logger.info("Fetching QQQ price history for technical signals...")
    qqq = yf.download("QQQ", start=start_date, progress=False)
    if qqq.empty:
        return pd.DataFrame()

    qqq.index = qqq.index.tz_localize(None)
    close = qqq["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    # Signal: 1 if MA50 < MA200 (Death Cross)
    signal = (ma50 < ma200).astype(int)

    return pd.DataFrame({"qqq_ma_cross": signal, "qqq_close": close}, index=qqq.index).dropna()
