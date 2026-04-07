from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import yfinance as yf

from src.collector.macro import fetch_historical_fred_series

logger = logging.getLogger(__name__)

SHILLER_DATA_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
DEFAULT_MACRO_CACHE_PATH = Path("data/macro_historical_dump.csv")


def _normalize_history_frame(frame: pd.DataFrame, value_column: str) -> pd.DataFrame:
    out = frame.copy()
    out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce")
    out[value_column] = pd.to_numeric(out[value_column], errors="coerce")
    out = out.dropna(subset=["observation_date"]).sort_values("observation_date")
    out = out.drop_duplicates(subset=["observation_date"], keep="last").reset_index(drop=True)
    return out.loc[:, ["observation_date", value_column]]


def _next_business_day(series: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(series, errors="coerce") + pd.offsets.BDay(1))


def _month_end(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce") + pd.offsets.MonthEnd(0)


def _history_from_yfinance(
    symbol: str, *, auto_adjust: bool = False, period: str = "max"
) -> pd.DataFrame:
    chart_url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
        f"?range={period}&interval=1d&includeAdjustedClose=true"
    )
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(chart_url, timeout=20, headers=headers)
        response.raise_for_status()
        payload = response.json()
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if result:
            timestamps = result.get("timestamp") or []
            indicators = result.get("indicators") or {}
            quote_block = (indicators.get("quote") or [{}])[0]
            closes = quote_block.get("close") or []
            if auto_adjust:
                closes = (indicators.get("adjclose") or [{}])[0].get("adjclose") or closes

            frame = pd.DataFrame(
                {
                    "observation_date": pd.to_datetime(timestamps, unit="s", errors="coerce"),
                    "close": pd.to_numeric(pd.Series(closes), errors="coerce"),
                }
            )
            frame["observation_date"] = frame["observation_date"].dt.normalize()
            frame = frame.dropna(subset=["observation_date", "close"])
            if not frame.empty:
                return frame.loc[:, ["observation_date", "close"]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Yahoo chart API fetch failed for %s: %s", symbol, exc)

    history = yf.Ticker(symbol).history(period=period, auto_adjust=auto_adjust)
    if history.empty:
        return pd.DataFrame(columns=["observation_date", "close"])

    close_column = "Close"
    if auto_adjust and "Close" not in history.columns and "Adj Close" in history.columns:
        close_column = "Adj Close"

    frame = history.reset_index()
    date_column = "Date" if "Date" in frame.columns else frame.columns[0]
    frame = frame.rename(columns={date_column: "observation_date", close_column: "close"})
    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"], errors="coerce"
    ).dt.normalize()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["observation_date", "close"])
    return frame.loc[:, ["observation_date", "close"]]


def fetch_historical_treasury_vol_series(timeout: int = 15) -> pd.DataFrame:
    frame = fetch_historical_fred_series("DGS10", timeout=timeout)
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["observation_date", "treasury_vol_21d", "effective_date"])

    daily = frame.copy()
    daily["DGS10"] = pd.to_numeric(daily["DGS10"], errors="coerce") / 100.0
    daily["treasury_vol_21d"] = daily["DGS10"].rolling(21, min_periods=21).std()
    daily["effective_date"] = _next_business_day(daily["observation_date"])
    return daily.loc[:, ["observation_date", "effective_date", "treasury_vol_21d"]]


def fetch_treasury_realized_vol() -> dict[str, float | str | bool | None]:
    try:
        frame = fetch_historical_treasury_vol_series()
        if not frame.empty and pd.notna(frame["treasury_vol_21d"].iloc[-1]):
            return {
                "value": float(frame["treasury_vol_21d"].iloc[-1]),
                "source": "direct:fred_dgs10",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Treasury realized vol fetch failed: %s", exc)

    return {"value": None, "source": "unavailable:treasury_vol", "degraded": True}


def fetch_historical_breakeven_series(timeout: int = 15) -> pd.DataFrame:
    frame = fetch_historical_fred_series("T10YIE", timeout=timeout)
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["observation_date", "breakeven_10y", "effective_date"])

    daily = frame.copy()
    daily["breakeven_10y"] = pd.to_numeric(daily["T10YIE"], errors="coerce") / 100.0
    daily["effective_date"] = _next_business_day(daily["observation_date"])
    return daily.loc[:, ["observation_date", "effective_date", "breakeven_10y"]]


def fetch_breakeven_inflation() -> dict[str, float | str | bool | None]:
    try:
        frame = fetch_historical_breakeven_series()
        if not frame.empty and pd.notna(frame["breakeven_10y"].iloc[-1]):
            return {
                "value": float(frame["breakeven_10y"].iloc[-1]),
                "source": "direct:fred_t10yie",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Breakeven fetch failed: %s", exc)

    return {"value": None, "source": "unavailable:breakeven", "degraded": True}


def fetch_historical_usdjpy_series() -> pd.DataFrame:
    frame = _history_from_yfinance("USDJPY=X", auto_adjust=False)
    if frame.empty:
        return pd.DataFrame(columns=["observation_date", "effective_date", "usdjpy"])

    frame = frame.rename(columns={"close": "usdjpy"})
    frame["effective_date"] = _next_business_day(frame["observation_date"])
    return frame.loc[:, ["observation_date", "effective_date", "usdjpy"]]


def fetch_usdjpy_snapshot() -> dict[str, float | str | bool | None]:
    try:
        frame = fetch_historical_usdjpy_series()
        if not frame.empty:
            return {
                "value": float(frame["usdjpy"].iloc[-1]),
                "source": "direct:yfinance",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("USDJPY fetch failed: %s", exc)

    return {"value": None, "source": "unavailable:usdjpy", "degraded": True}


def fetch_historical_copper_gold_ratio_series() -> pd.DataFrame:
    copper = _history_from_yfinance("HG=F", auto_adjust=True)
    gold = _history_from_yfinance("GC=F", auto_adjust=False)
    if copper.empty or gold.empty:
        return pd.DataFrame(columns=["observation_date", "effective_date", "copper_gold_ratio"])

    merged = copper.rename(columns={"close": "copper_close"}).merge(
        gold.rename(columns={"close": "gold_close"}),
        on="observation_date",
        how="inner",
    )
    merged["copper_gold_ratio"] = merged["copper_close"] / merged["gold_close"]
    merged["effective_date"] = _next_business_day(merged["observation_date"])
    return merged.loc[:, ["observation_date", "effective_date", "copper_gold_ratio"]]


def fetch_copper_gold_ratio() -> dict[str, float | str | bool | None]:
    try:
        frame = fetch_historical_copper_gold_ratio_series()
        if not frame.empty and pd.notna(frame["copper_gold_ratio"].iloc[-1]):
            return {
                "ratio": float(frame["copper_gold_ratio"].iloc[-1]),
                "source": "direct:yfinance",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Copper/gold fetch failed: %s", exc)

    return {"ratio": None, "source": "unavailable:copper_gold", "degraded": True}


def fetch_historical_core_capex_series(timeout: int = 15) -> pd.DataFrame:
    frame = fetch_historical_fred_series("NEWORDER", timeout=timeout)
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["observation_date", "effective_date", "core_capex_mm"])

    monthly = frame.copy()
    monthly["observation_date"] = _month_end(monthly["observation_date"])
    monthly["NEWORDER"] = pd.to_numeric(monthly["NEWORDER"], errors="coerce")
    monthly = monthly.dropna(subset=["NEWORDER"])
    monthly["core_capex_mm"] = monthly["NEWORDER"].diff()
    monthly["effective_date"] = monthly["observation_date"] + pd.offsets.BDay(30)
    return monthly.loc[:, ["observation_date", "effective_date", "core_capex_mm"]]


def fetch_core_capex_momentum() -> dict[str, float | str | bool | None]:
    try:
        frame = fetch_historical_core_capex_series()
        if not frame.empty and pd.notna(frame["core_capex_mm"].iloc[-1]):
            return {
                "delta": float(frame["core_capex_mm"].iloc[-1]),
                "source": "direct:fred_neworder",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Core capex fetch failed: %s", exc)

    return {"delta": None, "source": "unavailable:core_capex", "degraded": True}


def fetch_vix_term_structure_snapshot(timeout: int = 15) -> dict[str, float | str | bool | None]:
    """Fetch VIX (1m) and VXV (3m) to calculate term structure ratio."""
    try:
        vix_frame = fetch_historical_fred_series("VIXCLS", timeout=timeout)
        vxv_frame = fetch_historical_fred_series("VXVCLS", timeout=timeout)

        vix = None
        vxv = None

        if vix_frame is not None and not vix_frame.empty:
            vix = float(pd.to_numeric(vix_frame["VIXCLS"], errors="coerce").iloc[-1])

        if vxv_frame is not None and not vxv_frame.empty:
            vxv = float(pd.to_numeric(vxv_frame["VXVCLS"], errors="coerce").iloc[-1])

        if vix is not None and vxv is not None:
            return {
                "vix": vix,
                "vxv": vxv,
                "ratio": vix / vxv,
                "source": "direct:fred_vix_vxv",
                "degraded": False
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX term structure fetch failed: %s", exc)

    return {
        "vix": None,
        "vxv": None,
        "ratio": None,
        "source": "unavailable:vix_term_structure",
        "degraded": True
    }


def _load_shiller_sheet(timeout: int = 20) -> pd.DataFrame:
    errors: list[str] = []
    for url in (SHILLER_DATA_URL, SHILLER_DATA_URL.replace("http://", "https://", 1)):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return pd.read_excel(io.BytesIO(response.content), sheet_name="Data", skiprows=7)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
    raise RuntimeError(" / ".join(errors))


def fetch_historical_shiller_erp_series(
    *,
    real_yield_frame: pd.DataFrame | None = None,
    timeout: int = 20,
) -> pd.DataFrame:
    try:
        raw = _load_shiller_sheet(timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Shiller sheet fetch failed: %s", exc)
        return pd.DataFrame(
            columns=["observation_date", "effective_date", "erp_ttm_pct", "eps_ttm", "spx_price"]
        )

    frame = raw.rename(columns={"Date": "date", "P": "price", "E": "eps"})
    if "date" not in frame.columns or "price" not in frame.columns or "eps" not in frame.columns:
        return pd.DataFrame(
            columns=["observation_date", "effective_date", "erp_ttm_pct", "eps_ttm", "spx_price"]
        )

    date_values = pd.to_numeric(frame["date"], errors="coerce")
    year = date_values.fillna(0).astype(int)
    month_fraction = ((date_values - year).fillna(0.0) * 12.0 + 1.0).round().clip(1, 12).astype(int)
    observation_date = pd.to_datetime(
        {"year": year, "month": month_fraction, "day": 1},
        errors="coerce",
    ) + pd.offsets.MonthEnd(0)

    out = pd.DataFrame(
        {
            "observation_date": observation_date,
            "spx_price": pd.to_numeric(frame["price"], errors="coerce"),
            "eps_ttm": pd.to_numeric(frame["eps"], errors="coerce"),
        }
    ).dropna(subset=["observation_date", "spx_price", "eps_ttm"])
    out = out[out["spx_price"] > 0].copy()

    if real_yield_frame is not None and not real_yield_frame.empty:
        real_yield = real_yield_frame.loc[:, ["observation_date", "real_yield_10y_pct"]].copy()
        real_yield["observation_date"] = _month_end(real_yield["observation_date"])
        real_yield = real_yield.drop_duplicates(subset=["observation_date"], keep="last")
        out = out.merge(real_yield, on="observation_date", how="left")
    else:
        out["real_yield_10y_pct"] = 0.0

    out["erp_ttm_pct"] = (out["eps_ttm"] / out["spx_price"]) - out["real_yield_10y_pct"].fillna(0.0)
    out["effective_date"] = out["observation_date"] + pd.offsets.BDay(30)
    return out.loc[:, ["observation_date", "effective_date", "erp_ttm_pct", "eps_ttm", "spx_price"]]


def fetch_shiller_ttm_eps() -> dict[str, float | str | bool | None]:
    try:
        real_yield_frame = fetch_historical_fred_series("DFII10")
        if real_yield_frame is not None and not real_yield_frame.empty:
            real_yield_frame = real_yield_frame.rename(columns={"DFII10": "real_yield_10y_pct"})
            real_yield_frame["real_yield_10y_pct"] = (
                pd.to_numeric(real_yield_frame["real_yield_10y_pct"], errors="coerce") / 100.0
            )
        frame = fetch_historical_shiller_erp_series(real_yield_frame=real_yield_frame)
        if not frame.empty:
            latest = frame.iloc[-1]
            return {
                "eps": float(latest["eps_ttm"]),
                "price": float(latest["spx_price"]),
                "erp": float(latest["erp_ttm_pct"]),
                "source": "direct:shiller",
                "degraded": False,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Shiller ERP fetch failed: %s", exc)

    cached_snapshot = _load_cached_erp_snapshot()
    if cached_snapshot is not None:
        return cached_snapshot

    return {
        "eps": None,
        "price": None,
        "erp": None,
        "source": "unavailable:erp_ttm",
        "degraded": True,
    }


def _load_cached_erp_snapshot() -> dict[str, float | str | bool | None] | None:
    cache_path = Path(os.getenv("MACRO_DATA_PATH", str(DEFAULT_MACRO_CACHE_PATH)))
    if not cache_path.exists():
        return None

    try:
        frame = pd.read_csv(cache_path, usecols=["observation_date", "erp_ttm_pct"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cached ERP history load failed: %s", exc)
        return None

    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame["erp_ttm_pct"] = pd.to_numeric(frame["erp_ttm_pct"], errors="coerce")
    frame = frame.dropna(subset=["observation_date", "erp_ttm_pct"]).sort_values("observation_date")
    if frame.empty:
        return None

    latest = frame.iloc[-1]
    return {
        "eps": None,
        "price": None,
        "erp": float(latest["erp_ttm_pct"]),
        "source": "derived:macro_history_cache",
        "degraded": True,
    }


def fetch_v12_historical_series_bundle(timeout: int = 20) -> dict[str, pd.DataFrame]:
    real_yield = fetch_historical_fred_series("DFII10", timeout=timeout)
    if real_yield is None or real_yield.empty:
        real_yield_frame = pd.DataFrame(columns=["observation_date", "real_yield_10y_pct"])
    else:
        real_yield_frame = real_yield.rename(columns={"DFII10": "real_yield_10y_pct"})
        real_yield_frame["real_yield_10y_pct"] = (
            pd.to_numeric(real_yield_frame["real_yield_10y_pct"], errors="coerce") / 100.0
        )

    return {
        "credit_spread": fetch_historical_fred_series("BAMLH0A0HYM2", timeout=timeout),
        "real_yield": real_yield_frame,
        "treasury_vol": fetch_historical_treasury_vol_series(timeout=timeout),
        "breakeven": fetch_historical_breakeven_series(timeout=timeout),
        "capex": fetch_historical_core_capex_series(timeout=timeout),
        "copper_gold": fetch_historical_copper_gold_ratio_series(),
        "usdjpy": fetch_historical_usdjpy_series(),
        "erp_ttm": fetch_historical_shiller_erp_series(
            real_yield_frame=real_yield_frame, timeout=timeout
        ),
    }
