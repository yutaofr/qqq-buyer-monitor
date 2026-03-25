"""
Tier-2 engine: options wall confirmation and soft overlay layer.

Computes:
  - put_wall: strike with highest put Open Interest
  - call_wall: strike with highest call Open Interest
  - gamma_flip: price level where dealer net gamma changes sign

Then applies confirmation / overlay rules per PRD section 4.2.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.models import OptionsOverlay, Tier2Result

logger = logging.getLogger(__name__)

# Rule thresholds (as fractions of spot price)
SUPPORT_ZONE_PCT = 0.03   # put wall is "confirmed" if price is within 3% above
UPSIDE_MIN_PCT = 0.05     # call wall gives "open upside" if >= 5% above price
BUFFER_PCT = 0.005        # 0.5% buffer zone to prevent signal flickering near walls

from src.utils.stats import calculate_volume_poc

# Scoring table
SCORE_SUPPORT_CONFIRMED = 15
SCORE_SUPPORT_BROKEN = -30
SCORE_UPSIDE_OPEN = 10
SCORE_GAMMA_POSITIVE = 5
SCORE_NEGATIVE_GAMMA_BROKEN = -10  # extra penalty: negative gamma AND support broken
SCORE_POC_SUPPORT = 10             # v6.0 POC support bonus

def calculate_tier2(
    price: float,
    options_df: pd.DataFrame | None,
    ohlcv_history: pd.DataFrame | None = None
) -> Tier2Result:
    """
    Calculate Tier-2 options wall score by fetching walls from options_df and
    evaluating rules.
    """
    if options_df is None or options_df.empty:
        logger.warning("Options data fetch failed or empty; returning neutral results.")
        # Even if options fail, we might still have POC from history
        return _evaluate_poc_only(price, ohlcv_history)

    gamma_source = _dominant_gamma_source(options_df)
    put_wall = _find_wall(options_df, "put")
    call_wall = _find_wall(options_df, "call")
    gamma_flip = _find_gamma_flip(options_df, price)

    result = evaluate_tier2_rules(
        price, put_wall, call_wall, gamma_flip,
        options_df=options_df,
        gamma_source=gamma_source,
        ohlcv_history=ohlcv_history
    )
    return result


def evaluate_tier2_rules(
    price: float,
    put_wall: float | None,
    call_wall: float | None,
    gamma_flip: float | None,
    options_df: pd.DataFrame | None = None,
    gamma_source: str = "unknown",
    ohlcv_history: pd.DataFrame | None = None
) -> Tier2Result:
    """
    Unified decision engine for Tier-2 rules. 
    Can be used by both live monitor and backtest.
    """
    support_confirmed = False
    support_broken = False
    upside_open = False
    gamma_positive = False

    put_wall_distance_pct = None
    call_wall_distance_pct = None
    next_put_wall = None
    next_put_wall_distance_pct = None

    if put_wall is not None:
        put_wall_distance_pct = (price - put_wall) / price
        if put_wall_distance_pct < -BUFFER_PCT:
            support_broken = True
            if options_df is not None:
                next_put_wall = _find_next_wall(options_df, "put", price)
            if next_put_wall is not None:
                next_put_wall_distance_pct = (price - next_put_wall) / price
        elif put_wall_distance_pct <= SUPPORT_ZONE_PCT:
            support_confirmed = True

    if call_wall is not None:
        if call_wall <= price:
            alt_call_wall = None
            if options_df is not None:
                alt_call_wall = _find_next_wall_above(options_df, "call", price)

            if alt_call_wall is not None:
                dist = (alt_call_wall - price) / price
                if dist >= UPSIDE_MIN_PCT:
                    upside_open = True
                call_wall_distance_pct = dist
            else:
                upside_open = True
                call_wall_distance_pct = 0.99
        else:
            call_wall_distance_pct = (call_wall - price) / price
            if call_wall_distance_pct >= UPSIDE_MIN_PCT:
                upside_open = True

    if gamma_flip is not None:
        gamma_positive = price > gamma_flip

    # ── Compute adjustment ────────────────────────────────────────────────────
    adjustment = 0
    if support_confirmed:
        adjustment += SCORE_SUPPORT_CONFIRMED
    if support_broken:
        adjustment += SCORE_SUPPORT_BROKEN
    if upside_open:
        adjustment += SCORE_UPSIDE_OPEN
    if gamma_positive:
        adjustment += SCORE_GAMMA_POSITIVE
    if not gamma_positive and support_broken:
        adjustment += SCORE_NEGATIVE_GAMMA_BROKEN

    # v6.0 Volume POC Confirmation
    poc_val = None
    if ohlcv_history is not None and not ohlcv_history.empty:
        # Use past 252 trading days for Volume Profile
        vp_hist = ohlcv_history.tail(252)
        poc_val = calculate_volume_poc(vp_hist)
        if poc_val > 0:
            dist_to_poc = abs(price - poc_val) / price
            # POC is a confirmed support if within 2% AND support not already broken
            if dist_to_poc <= 0.02 and not support_broken:
                logger.info("v6.0 POC SUPPORT: Price is within 2%% of Volume POC ($%.2f)", poc_val)
                adjustment += SCORE_POC_SUPPORT
                support_confirmed = True

    overlay = _build_options_overlay(
        support_confirmed=support_confirmed,
        support_broken=support_broken,
        upside_open=upside_open,
        gamma_positive=gamma_positive,
    )

    return Tier2Result(
        adjustment=adjustment,
        put_wall=put_wall,
        call_wall=call_wall,
        gamma_flip=gamma_flip,
        poc=poc_val,
        support_confirmed=support_confirmed,

        support_broken=support_broken,
        upside_open=upside_open,
        gamma_positive=gamma_positive,
        gamma_source=gamma_source,
        put_wall_distance_pct=round(put_wall_distance_pct, 4) if put_wall_distance_pct is not None else None,
        call_wall_distance_pct=round(call_wall_distance_pct, 4) if call_wall_distance_pct is not None else None,
        next_put_wall=next_put_wall,
        next_put_wall_distance_pct=round(next_put_wall_distance_pct, 4) if next_put_wall_distance_pct is not None else None,
        overlay=overlay,
    )

def _find_wall(df: pd.DataFrame, option_type: str) -> float | None:
    """Return the strike with the highest Open Interest for the given side."""
    side = df[df["option_type"] == option_type]
    if side.empty:
        return None
    agg = side.groupby("strike")["openInterest"].sum()
    if agg.empty:
        return None
    return float(agg.idxmax())


def _find_next_wall(df: pd.DataFrame, option_type: str, current_price: float) -> float | None:
    """Return the strike with the highest OI for the given side that is strictly below current_price."""
    side = df[(df["option_type"] == option_type) & (df["strike"] < current_price)]
    if side.empty:
        return None
    agg = side.groupby("strike")["openInterest"].sum()
    if agg.empty:
        return None
    return float(agg.idxmax())


def _find_next_wall_above(df: pd.DataFrame, option_type: str, current_price: float) -> float | None:
    """Return the strike with the highest OI for the given side that is strictly above current_price."""
    side = df[(df["option_type"] == option_type) & (df["strike"] > current_price)]
    if side.empty:
        return None
    agg = side.groupby("strike")["openInterest"].sum()
    if agg.empty:
        return None
    return float(agg.idxmax())


def _find_gamma_flip(df: pd.DataFrame, price: float) -> float | None:
    """
    Find the gamma flip level: the strike where dealer net gamma changes sign.

    Net gamma per strike = (call_gamma × call_OI) - (put_gamma × put_OI)

    Dealers are long gamma when net > 0 (stabilising), short gamma when net < 0
    (destabilising). The gamma flip is where this sum crosses zero.

    We search for the zero-crossing nearest to the current spot price.
    """
    calls = df[df["option_type"] == "call"].groupby("strike").apply(
        lambda g: (g["gamma"] * g["openInterest"]).sum()
    )
    puts = df[df["option_type"] == "put"].groupby("strike").apply(
        lambda g: (g["gamma"] * g["openInterest"]).sum()
    )

    strikes = sorted(set(calls.index) | set(puts.index))
    if not strikes:
        return None

    net = {
        k: calls.get(k, 0.0) - puts.get(k, 0.0)
        for k in strikes
    }

    # Find zero-crossing: look for adjacent strikes where net changes sign
    strike_list = sorted(net.keys())
    flip_candidates: list[float] = []
    for i in range(len(strike_list) - 1):
        k1, k2 = strike_list[i], strike_list[i + 1]
        n1, n2 = net[k1], net[k2]
        if n1 * n2 < 0:  # sign change
            # Linear interpolation to find crossing
            flip = k1 + (k2 - k1) * (-n1 / (n2 - n1))
            flip_candidates.append(flip)

    if not flip_candidates:
        # No zero crossing; return strike with net closest to zero
        return min(strikes, key=lambda k: abs(net[k]))

    # Return the flip level nearest to current spot price
    return min(flip_candidates, key=lambda f: abs(f - price))


def _dominant_gamma_source(df: pd.DataFrame) -> str:
    """Return 'yfinance' if most rows used native gamma, else 'bs'."""
    if "gamma_source" not in df.columns:
        return "unknown"
    counts = df["gamma_source"].value_counts()
    return str(counts.idxmax())


def _build_options_overlay(
    *,
    support_confirmed: bool,
    support_broken: bool,
    upside_open: bool,
    gamma_positive: bool,
) -> OptionsOverlay:
    """Translate raw options structure into a non-upgrading overlay."""
    if support_broken:
        return OptionsOverlay(
            can_reduce_tranche=True,
            tranche_multiplier=0.5,
            confidence="low",
            delay_days=1,
        )

    # Support-confirmed / upside-open / positive gamma is useful context, but
    # it does not upgrade structural state by itself.
    return OptionsOverlay(
        can_reduce_tranche=False,
        tranche_multiplier=1.0,
        confidence="medium",
        delay_days=0,
    )


def _evaluate_poc_only(price: float, ohlcv_history: pd.DataFrame | None) -> Tier2Result:
    """Fall-back to Volume POC support if options data is missing."""
    adjustment = 0
    support_confirmed = False
    poc_val = None

    if ohlcv_history is not None and not ohlcv_history.empty:
        vp_hist = ohlcv_history.tail(252)
        poc_val = calculate_volume_poc(vp_hist)
        if poc_val > 0:
            dist_to_poc = abs(price - poc_val) / price
            if dist_to_poc <= 0.02:
                logger.info("v6.0 FALLBACK POC SUPPORT: Price within 2%% of POC ($%.2f)", poc_val)
                adjustment += SCORE_POC_SUPPORT
                support_confirmed = True

    result = _neutral_result()
    result.adjustment = adjustment
    result.support_confirmed = support_confirmed
    result.poc = poc_val
    return result


def _neutral_result() -> Tier2Result:
    result = Tier2Result(
        adjustment=0,
        put_wall=None,
        call_wall=None,
        gamma_flip=None,
        poc=None,
        support_confirmed=False,
        support_broken=False,
        upside_open=False,
        gamma_positive=False,
        gamma_source="none",
        put_wall_distance_pct=None,
        call_wall_distance_pct=None,
        next_put_wall=None,
        next_put_wall_distance_pct=None,
        overlay=OptionsOverlay(),
    )
    return result
