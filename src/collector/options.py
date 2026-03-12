"""
Options chain collector for QQQ.

Fetches open interest and gamma for calls and puts across near-term
expiration dates. Implements a dual-source strategy for gamma:
  1. Primary: use gamma values returned directly by yfinance
  2. Fallback: compute gamma via Black-Scholes if yfinance value is missing
"""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

logger = logging.getLogger(__name__)

RISK_FREE_TICKER = "^IRX"  # 13-week T-bill yield


def fetch_options_chain(ticker: str = "QQQ", as_of: date | None = None) -> pd.DataFrame:
    """
    Fetch options chain for the nearest two expiration dates.

    Returns:
        DataFrame with columns:
            strike (float), expiration (str), option_type ('call'/'put'),
            openInterest (int), impliedVolatility (float),
            gamma (float), gamma_source ('yfinance'|'bs')

    Raises:
        RuntimeError if no options data can be fetched.
    """
    target_date = as_of or date.today()
    spot = _fetch_spot(ticker, target_date)
    risk_free = _fetch_risk_free_rate()

    t_obj = yf.Ticker(ticker)
    expirations = t_obj.options  # tuple of expiration date strings

    if not expirations:
        raise RuntimeError(f"No options expiration dates found for {ticker}")

    # Take at most the 2 nearest expirations after target_date
    future_exps = [
        e for e in expirations
        if date.fromisoformat(e) >= target_date
    ][:2]

    if not future_exps:
        raise RuntimeError(
            f"No future expiration dates found for {ticker} after {target_date}"
        )

    frames: list[pd.DataFrame] = []
    for exp in future_exps:
        chain = t_obj.option_chain(exp)
        calls = _process_side(chain.calls, "call", exp, spot, risk_free, target_date)
        puts = _process_side(chain.puts, "put", exp, spot, risk_free, target_date)
        frames.extend([calls, puts])

    result = pd.concat(frames, ignore_index=True)
    logger.debug(
        "Options chain: %d rows across %d expirations", len(result), len(future_exps)
    )
    return result


def _fetch_spot(ticker: str, as_of: date) -> float:
    """Fetch the most recent closing price for the ticker."""
    start = as_of - timedelta(days=5)
    query_end = as_of + timedelta(days=1)
    hist = yf.Ticker(ticker).history(start=start.isoformat(), end=query_end.isoformat())
    if hist.empty:
        raise RuntimeError(f"Cannot fetch spot price for {ticker}")
    return float(hist["Close"].iloc[-1])


def _fetch_risk_free_rate() -> float:
    """
    Fetch the 13-week US T-bill yield from ^IRX (annualised, percent).
    Falls back to 5.0% if unavailable.
    """
    try:
        hist = yf.Ticker(RISK_FREE_TICKER).history(period="5d")
        if not hist.empty:
            rate_pct = float(hist["Close"].iloc[-1])
            return rate_pct / 100.0  # convert percent to decimal
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch ^IRX risk-free rate: %s. Using 5.0%%.", exc)
    return 0.05


def _process_side(
    df: pd.DataFrame,
    option_type: str,
    expiration: str,
    spot: float,
    risk_free: float,
    as_of: date,
) -> pd.DataFrame:
    """
    Normalise one side (calls or puts) of the options chain.
    Fills missing gamma values using Black-Scholes.
    """
    if df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["strike"] = df["strike"].astype(float)
    out["expiration"] = expiration
    out["option_type"] = option_type
    out["openInterest"] = df["openInterest"].fillna(0).astype(int)
    out["impliedVolatility"] = df["impliedVolatility"].fillna(0.3).astype(float)

    # Gamma: use yfinance value where available
    if "gamma" in df.columns:
        out["gamma"] = df["gamma"].astype(float)
        out["gamma_source"] = "yfinance"
        # Where gamma is NaN or zero, compute via BS
        mask = out["gamma"].isna() | (out["gamma"] == 0)
    else:
        out["gamma"] = 0.0
        out["gamma_source"] = "bs"
        mask = pd.Series(True, index=out.index)

    if mask.any():
        exp_date = date.fromisoformat(expiration)
        T = max((exp_date - as_of).days, 1) / 365.0
        bs_gammas = out.loc[mask, "strike"].apply(
            lambda k: _bs_gamma(spot, k, risk_free, out.loc[out["strike"] == k, "impliedVolatility"].iloc[0], T)
        )
        out.loc[mask, "gamma"] = bs_gammas.values
        out.loc[mask, "gamma_source"] = "bs"

    # Filter out zero OI rows to keep the DataFrame lean
    out = out[out["openInterest"] > 0].copy()
    return out


def _bs_gamma(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Black-Scholes gamma for a European option.

    Gamma = N'(d1) / (S * sigma * sqrt(T))

    Args:
        S: Spot price
        K: Strike price
        r: Risk-free rate (decimal, annualised)
        sigma: Implied volatility (decimal, annualised)
        T: Time to expiration in years

    Returns:
        Gamma value (float). Returns 0.0 on numerical errors.
    """
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        return float(norm.pdf(d1) / (S * sigma * math.sqrt(T)))
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0.0
