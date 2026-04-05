import logging

import pandas as pd

from src.collector.macro import FRED_HISTORY_START, fetch_fred_api, fetch_fred_data

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

# Conservative release lags (in business days) as per SRD / V14 PIT requirements
RELEASE_LAG_MAP = {
    "IPMAN": 22,    # Monthly (~1 month)
    "M2REAL": 22,   # Monthly (~1 month)
    "CP": 66,       # Quarterly (~3 months)
    "GDP": 66,      # Quarterly (~3 months)
    "T10Y2Y": 1,    # Daily
    "BAMLH0A0HYM2": 1,
    "VIXCLS": 1,
    "^VXN": 1,
}

ALFRED_REALTIME_START = "1776-07-04"
ALFRED_REALTIME_END = "9999-12-31"


def _build_alfred_visible_frame(raw: pd.DataFrame, series_id: str) -> pd.DataFrame | None:
    frame = raw.copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce").dt.tz_localize(None)
    frame["realtime_start"] = pd.to_datetime(frame["realtime_start"], errors="coerce").dt.tz_localize(None)
    frame["realtime_end"] = pd.to_datetime(frame["realtime_end"], errors="coerce").dt.tz_localize(None)
    frame[series_id] = pd.to_numeric(frame[series_id], errors="coerce")
    frame = frame.dropna(subset=["observation_date", "realtime_start", series_id]).sort_values(
        ["realtime_start", "observation_date"]
    )
    if frame.empty:
        return None
    # Build a sparse step function keyed by release events instead of scanning a
    # multi-century business-day calendar. For an as-of date, the visible value is
    # the latest released observation on or before that date.
    rows: list[dict[str, object]] = []
    for effective_date, group in frame.groupby("realtime_start", sort=True):
        latest = (
            group.sort_values(["observation_date", "realtime_end"])
            .drop_duplicates(subset=["observation_date"], keep="last")
            .iloc[-1]
        )
        rows.append(
            {
                "effective_date": effective_date,
                "observation_date": latest["observation_date"],
                series_id: float(latest[series_id]),
            }
        )
    if not rows:
        return None
    out = pd.DataFrame(rows).set_index("effective_date").sort_index()
    out.attrs["vintage_mode"] = "ALFRED"
    return out.loc[:, [series_id, "observation_date"]]


def _build_pit_fallback_frame(raw: pd.DataFrame, series_id: str) -> pd.DataFrame | None:
    frame = raw.copy()
    if "observation_date" not in frame.columns:
        for candidate in ("date", "DATE", "Date"):
            if candidate in frame.columns:
                frame = frame.rename(columns={candidate: "observation_date"})
                break
    if "observation_date" not in frame.columns:
        return None
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.tz_localize(None)
    val_series = frame[series_id]
    if isinstance(val_series, pd.DataFrame):
        val_series = val_series.iloc[:, 0]
    frame[series_id] = pd.to_numeric(val_series, errors="coerce")
    frame = frame.dropna(subset=[series_id])
    lag = RELEASE_LAG_MAP.get(series_id, 1)
    frame["effective_date"] = frame["observation_date"] + pd.offsets.BDay(lag)
    out = frame.set_index("effective_date")[[series_id, "observation_date"]].sort_index().groupby(level=0).last()
    out.attrs["vintage_mode"] = "PIT_FALLBACK"
    return out


def fetch_baseline_series(series_id: str, timeout: int = 15) -> pd.DataFrame | None:
    """Fetch and normalize a baseline series (ALFRED if available, else PIT fallback)."""
    if series_id.startswith("^"):
        # YFinance Path
        import yfinance as yf
        try:
            # Explicitly choose the ticker and suppress progress
            raw = yf.download(series_id, start=FRED_HISTORY_START, progress=False)
            if raw.empty:
                return None

            # Flatten multi-index if exists
            if isinstance(raw.columns, pd.MultiIndex):
                # Level 0 is usually Fields (Close, etc), Level 1 is Ticker
                if series_id in raw.columns.get_level_values(0):
                    raw.columns = raw.columns.get_level_values(1)
                elif series_id in raw.columns.get_level_values(1):
                    raw.columns = raw.columns.get_level_values(0)
                else:
                    # Fallback to level 0
                    raw.columns = raw.columns.get_level_values(0)

            logger.debug(f"YFinance {series_id} columns after flattening: {raw.columns.tolist()}")

            # Standardize columns
            raw = raw.reset_index()
            # Rename Date-like column to observation_date
            date_col = next((c for c in raw.columns if "Date" in str(c) or "date" in str(c)), None)
            if date_col:
                raw = raw.rename(columns={date_col: "observation_date"})
            else:
                raw["observation_date"] = raw.index # Fallback

            # Extract closing price
            close_col = next((c for c in ["Close", "Adj Close", series_id] if c in raw.columns), None)
            if close_col:
                raw[series_id] = raw[close_col]
            else:
                return None
            out = raw.set_index("observation_date")[[series_id]].sort_index()
            out["observation_date"] = out.index
            out["effective_date"] = out.index + pd.offsets.BDay(1)
            out = out.set_index("effective_date")[[series_id, "observation_date"]].sort_index().groupby(level=0).last()
            out.attrs["vintage_mode"] = "DIRECT_TAPE"
            return out
        except Exception as e:
            logger.warning(f"YFinance fetch failed for {series_id}: {e}")
            return None
    else:
        # ALFRED Path: Only for low-frequency series with archival needs (Monthly/Quarterly)
        # Daily series (lag=1) should skip this to avoid 400 Bad Request / No Observations on ALFRED.
        is_daily = RELEASE_LAG_MAP.get(series_id, 1) == 1

        alfred_raw = None
        if not is_daily:
            alfred_raw = fetch_fred_api(
                series_id,
                timeout=timeout,
                observation_start=FRED_HISTORY_START,
                realtime_start=ALFRED_REALTIME_START,
                realtime_end=ALFRED_REALTIME_END,
            )

        if alfred_raw is not None and not alfred_raw.empty and {"realtime_start", "realtime_end"}.issubset(alfred_raw.columns):
            alfred_frame = _build_alfred_visible_frame(alfred_raw, series_id)
            if alfred_frame is not None and not alfred_frame.empty:
                return alfred_frame

        # Fallback (or primary for Daily): Standard FRED path with PIT-lag
        raw = fetch_fred_data(series_id, timeout=timeout)
        if raw is None or raw.empty:
            logger.warning(f"Failed to fetch baseline series: {series_id}")
            return None
        pit_frame = _build_pit_fallback_frame(raw, series_id)
        if pit_frame is not None and not pit_frame.empty:
            return pit_frame
        return None


def get_growth_margin(timeout: int = 15) -> pd.DataFrame | None:
    """Calculate Corporate Profit Margin (CP/GDP) with PIT alignment."""
    cp = fetch_baseline_series(BASELINE_SERIES_MAP["growth_margin_numerator"], timeout=timeout)
    gdp = fetch_baseline_series(BASELINE_SERIES_MAP["growth_margin_denominator"], timeout=timeout)

    if cp is None or gdp is None:
        return None

    # Align on effective_date (the index)
    merged = cp.merge(gdp, left_index=True, right_index=True, how="inner")
    margin = (
        merged[BASELINE_SERIES_MAP["growth_margin_numerator"]]
        / merged[BASELINE_SERIES_MAP["growth_margin_denominator"]]
    ) * 100.0
    out = pd.DataFrame({"growth_margin": margin}, index=merged.index)
    cp_mode = cp.attrs.get("vintage_mode", "UNKNOWN")
    gdp_mode = gdp.attrs.get("vintage_mode", "UNKNOWN")
    out.attrs["vintage_mode"] = "ALFRED" if cp_mode == gdp_mode == "ALFRED" else "+".join(
        sorted({mode for mode in (cp_mode, gdp_mode) if mode})
    )
    return out


def load_all_baseline_data(timeout: int = 15) -> pd.DataFrame:
    """
    Fetch all baseline data and align on daily index with true PIT (effective_date).
    Does NOT use observation_date as the available date for monthly/quarterly series.
    """
    frames = []
    metadata = {"degraded": []}
    vintage_modes: list[str] = []

    # 1. IPMAN (Monthly)
    ipman = fetch_baseline_series(BASELINE_SERIES_MAP["growth_pmi"], timeout=timeout)
    if ipman is not None:
        if ipman.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(ipman.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(ipman[[BASELINE_SERIES_MAP["growth_pmi"]]])
    else:
        metadata["degraded"].append("IPMAN")

    # 2. Margin (Quarterly)
    margin = get_growth_margin(timeout=timeout)
    if margin is not None:
        if margin.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(margin.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(margin)
    else:
        metadata["degraded"].append("growth_margin")

    # 3. M2REAL (Monthly)
    m2 = fetch_baseline_series(BASELINE_SERIES_MAP["liquidity_m2"], timeout=timeout)
    if m2 is not None:
        if m2.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(m2.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(m2[[BASELINE_SERIES_MAP["liquidity_m2"]]])
    else:
        metadata["degraded"].append("M2REAL")

    # 4. T10Y2Y (Daily)
    slope = fetch_baseline_series(BASELINE_SERIES_MAP["liquidity_slope"], timeout=timeout)
    if slope is not None:
        if slope.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(slope.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(slope[[BASELINE_SERIES_MAP["liquidity_slope"]]])
    else:
        metadata["degraded"].append("T10Y2Y")

    # 5. Credit Spread (Daily)
    credit = fetch_baseline_series(BASELINE_SERIES_MAP["stress_credit"], timeout=timeout)
    if credit is not None:
        if credit.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(credit.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(credit[[BASELINE_SERIES_MAP["stress_credit"]]])
    else:
        metadata["degraded"].append("BAMLH0A0HYM2")

    # 6. VIX (Daily)
    vix = fetch_baseline_series(BASELINE_SERIES_MAP["stress_vix"], timeout=timeout)
    if vix is not None:
        if vix.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(vix.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(vix[[BASELINE_SERIES_MAP["stress_vix"]]])
    else:
        metadata["degraded"].append("VIXCLS")

    # 7. VXN (Daily) - Explicitly handle missing as degraded
    vxn = fetch_baseline_series(BASELINE_SERIES_MAP["stress_vxn"], timeout=timeout)
    if vxn is not None:
        if vxn.attrs.get("vintage_mode") != "DIRECT_TAPE":
            vintage_modes.append(vxn.attrs.get("vintage_mode", "UNKNOWN"))
        frames.append(vxn[[BASELINE_SERIES_MAP["stress_vxn"]]])
    else:
        metadata["degraded"].append("^VXN")

    if not frames:
        return pd.DataFrame()

    # Join on effective_date (PIT)
    combined = pd.concat(frames, axis=1, sort=False).sort_index()
    logger.debug(f"Combined columns before daily index: {combined.columns.tolist()}")
    logger.debug(f"Combined index sample: {combined.index[:5]}")

    # Forward-fill only AFTER PIT alignment to daily frequency
    # We create a daily range to ensure we have a point for every trading day
    daily_idx = pd.date_range(start=combined.index.min(), end=combined.index.max(), freq="B")
    combined = combined.reindex(daily_idx).ffill()

    logger.debug(f"Combined columns after daily reindex: {combined.columns.tolist()}")
    logger.info(f"Loaded baseline data: {len(combined)} rows, Columns: {combined.columns.tolist()}")

    # Attach metadata as an attribute for downstream use
    unique_modes = sorted({mode for mode in vintage_modes if mode})
    metadata["vintage_mode"] = "ALFRED" if unique_modes == ["ALFRED"] else ("+".join(unique_modes) if unique_modes else "UNKNOWN")
    combined.attrs["metadata"] = metadata
    return combined


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
