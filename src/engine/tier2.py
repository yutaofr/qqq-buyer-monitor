"""
Tier-2 engine: options wall confirmation and veto layer.

Computes:
  - put_wall: strike with highest put Open Interest
  - call_wall: strike with highest call Open Interest
  - gamma_flip: price level where dealer net gamma changes sign

Then applies confirmation / veto rules per PRD section 4.2.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.models import Tier2Result

logger = logging.getLogger(__name__)

# Rule thresholds (as fractions of spot price)
SUPPORT_ZONE_PCT = 0.03   # put wall is "confirmed" if price is within 3% above
UPSIDE_MIN_PCT = 0.05     # call wall gives "open upside" if >= 5% above price

# Scoring table
SCORE_SUPPORT_CONFIRMED = 15
SCORE_SUPPORT_BROKEN = -30
SCORE_UPSIDE_OPEN = 10
SCORE_GAMMA_POSITIVE = 5
SCORE_NEGATIVE_GAMMA_BROKEN = -10  # extra penalty: negative gamma AND support broken


def calculate_tier2(price: float, options_df: pd.DataFrame | None) -> Tier2Result:
    """
    Calculate Tier-2 options wall score.

    Args:
        price: Current QQQ spot price.
        options_df: DataFrame from fetch_options_chain(). If None, returns
                    neutral result (adjustment=0, no flags set).

    Returns:
        Tier2Result with adjustment score and explanatory flags.
    """
    if options_df is None or options_df.empty:
        logger.warning("No options data; Tier-2 returning neutral result.")
        return _neutral_result()

    gamma_source = _dominant_gamma_source(options_df)

    put_wall = _find_wall(options_df, "put")
    call_wall = _find_wall(options_df, "call")
    gamma_flip = _find_gamma_flip(options_df, price)

    # ── Evaluate rules ────────────────────────────────────────────────────────
    support_confirmed = False
    support_broken = False
    upside_open = False
    gamma_positive = False

    put_wall_distance_pct = None
    call_wall_distance_pct = None

    if put_wall is not None:
        put_wall_distance_pct = (price - put_wall) / price
        if put_wall_distance_pct < 0:
            # Price is below put wall
            support_broken = True
        elif put_wall_distance_pct <= SUPPORT_ZONE_PCT:
            # Price is just above put wall → support confirmed
            support_confirmed = True

    if call_wall is not None:
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

    logger.debug(
        "Tier2: put_wall=%.1f call_wall=%.1f gamma_flip=%s adj=%d",
        put_wall or 0, call_wall or 0,
        f"{gamma_flip:.1f}" if gamma_flip else "N/A",
        adjustment,
    )

    return Tier2Result(
        adjustment=adjustment,
        put_wall=put_wall,
        call_wall=call_wall,
        gamma_flip=gamma_flip,
        support_confirmed=support_confirmed,
        support_broken=support_broken,
        upside_open=upside_open,
        gamma_positive=gamma_positive,
        gamma_source=gamma_source,
        put_wall_distance_pct=round(put_wall_distance_pct, 4) if put_wall_distance_pct is not None else None,
        call_wall_distance_pct=round(call_wall_distance_pct, 4) if call_wall_distance_pct is not None else None,
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


def _neutral_result() -> Tier2Result:
    return Tier2Result(
        adjustment=0,
        put_wall=None,
        call_wall=None,
        gamma_flip=None,
        support_confirmed=False,
        support_broken=False,
        upside_open=False,
        gamma_positive=False,
        gamma_source="none",
        put_wall_distance_pct=None,
        call_wall_distance_pct=None,
    )
