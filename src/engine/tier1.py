"""
Tier-1 signal engine: 5 market signals with gradient scoring (0/10/20).

Each signal scores independently; total Tier-1 score ranges 0-100.
All thresholds are defined as module-level constants for easy M4 tuning.
"""
from __future__ import annotations

import logging

from src.engine.divergence import check_divergences
from src.engine.fundamentals import calculate_fcf_bonus, calculate_valuation_weight
from src.models import MarketData, SignalDetail, Tier1Result
from src.utils.stats import (
    calculate_mean_reversion_score,
    calculate_sma_deviation_zscore,
)

logger = logging.getLogger(__name__)

# ── Gradient thresholds (low, high) ──────────────────────────────────────────
# Signal 1: 52-week high drawdown  (higher = more bullish)
DRAWDOWN_THRESHOLDS = (0.05, 0.10)      # Absolute: <5%=0, 5-10%=10, >=10%=20
DRAWDOWN_Z_THRESHOLDS = (1.2, 2.0)      # Relative: Z > 1.2 = 10 pts, Z > 2.0 = 20 pts

# Signal 2: MA200 deviation  (more negative = more bullish)
MA200_THRESHOLDS = (-0.03, -0.07)       # >-3%=0, -3~-7%=10, <=-7%=20
MA200_Z_THRESHOLDS = (-1.5, -2.5)       # Z < -1.5 = 10 pts, Z < -2.5 = 20 pts

# Signal 3: VIX level (contrarian)
VIX_THRESHOLDS = (22.0, 30.0)           # Absolute: <22=0, 22-30=10, >30=20
VIX_Z_THRESHOLDS = (1.5, 2.5)           # Relative: Z > 1.5 StdDev = 10, Z > 2.5 = 20

# Signal 4: Fear & Greed (lower = more bullish)
FG_THRESHOLDS = (30, 20)                # >30=0, 20-30=10, <=20=20

# Signal 5: Market breadth (lower = more bullish / capitulation)
BREADTH_RATIO_T = (0.7, 0.4)            # advance/decline ratio


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _score_higher_better(value: float, low_t: float, high_t: float) -> tuple[int, bool, bool]:
    """Return score for a metric where higher values are more 'bullish'."""
    if value >= high_t:
        return 20, True, True
    elif value >= low_t:
        return 10, True, False
    else:
        return 0, False, False


def _score_lower_better(value: float, low_t: float, high_t: float) -> tuple[int, bool, bool]:
    """Return score for a metric where lower values are more 'bullish'."""
    if value <= high_t:
        return 20, True, True
    elif value <= low_t:
        return 10, True, False
    else:
        return 0, False, False


# ── Main engine ───────────────────────────────────────────────────────────────

def calculate_tier1(data: MarketData) -> Tier1Result:
    """
    Calculate Tier-1 score from market data.

    Returns Tier1Result with total score (0-100) and per-signal breakdown.
    """
    regime = identify_regime(data.vix_zscore)
    descent_v, days_to_dd = calculate_descent_velocity(data)
    logger.info("Current Market Regime: %s (VIX Z=%.2f, Descent: %s [%d days])",
                regime, data.vix_zscore, descent_v, days_to_dd)
    # Signal 1: 52-week drawdown
    drawdown = (data.high_52w - data.price) / data.high_52w
    s1_pts, s1_half, s1_full = _score_higher_better(drawdown, *DRAWDOWN_THRESHOLDS)

    # v4.0 Adaptive Boost: if volatility is low, Z-score might trigger even if absolute is low
    if data.drawdown_zscore >= DRAWDOWN_Z_THRESHOLDS[1]:
        s1_pts = max(s1_pts, 20)
        s1_half, s1_full = True, True
    elif data.drawdown_zscore >= DRAWDOWN_Z_THRESHOLDS[0]:
        s1_pts = max(s1_pts, 10)
        s1_half = True

    s1 = SignalDetail(
        name="52w_drawdown",
        value=round(drawdown, 4),
        points=s1_pts,
        thresholds=DRAWDOWN_THRESHOLDS,
        triggered_half=s1_half,
        triggered_full=s1_full,
    )

    # Signal 2: MA200 deviation
    ma200_dev = (data.price - data.ma200) / data.ma200
    # Deviation is negative for "more bullish"; flip sign for lower_better logic
    s2_pts, s2_half, s2_full = _score_lower_better(ma200_dev, *MA200_THRESHOLDS)

    # v6.0 Adaptive Boost for MA200 deviation
    ma200_z = 0.0
    if data.ohlcv_history is not None:
        ma200_z = calculate_sma_deviation_zscore(data.ohlcv_history['Close'])
        if ma200_z <= MA200_Z_THRESHOLDS[1]:
            s2_pts = max(s2_pts, 20)
            s2_half, s2_full = True, True
        elif ma200_z <= MA200_Z_THRESHOLDS[0]:
            s2_pts = max(s2_pts, 10)
            s2_half = True

    s2 = SignalDetail(
        name="ma200_deviation",
        value=round(ma200_dev, 4),
        points=s2_pts,
        thresholds=MA200_THRESHOLDS,
        triggered_half=s2_half,
        triggered_full=s2_full,
    )

    # Signal 3: VIX
    s3_pts, s3_half, s3_full = _score_higher_better(data.vix, *VIX_THRESHOLDS)

    # v4.0 Adaptive Boost for VIX
    if data.vix_zscore >= VIX_Z_THRESHOLDS[1]:
        s3_pts = max(s3_pts, 20)
        s3_half, s3_full = True, True
    elif data.vix_zscore >= VIX_Z_THRESHOLDS[0]:
        s3_pts = max(s3_pts, 10)
        s3_half = True

    s3 = SignalDetail(
        name="vix",
        value=round(data.vix, 2),
        points=s3_pts,
        thresholds=VIX_THRESHOLDS,
        triggered_half=s3_half,
        triggered_full=s3_full,
    )

    # Signal 4: Fear & Greed
    s4_pts, s4_half, s4_full = _score_lower_better(
        float(data.fear_greed), float(FG_THRESHOLDS[0]), float(FG_THRESHOLDS[1])
    )
    s4 = SignalDetail(
        name="fear_greed",
        value=float(data.fear_greed),
        points=s4_pts,
        thresholds=FG_THRESHOLDS,
        triggered_half=s4_half,
        triggered_full=s4_full,
    )

    # Signal 5: Market breadth uses a single auditable definition so live and
    # historical divergence checks compare the same concept.
    s5_pts, s5_half, s5_full = _score_lower_better(
        data.adv_dec_ratio, BREADTH_RATIO_T[0], BREADTH_RATIO_T[1]
    )

    # v4.2 QUIET Regime Boost: In low-vol environments, breadth is the most reliable filter
    if regime == "QUIET":
        if s5_pts > 0:
            logger.info("Regime BOOST: Increasing Breadth weight in QUIET environment.")
            s5_pts = min(s5_pts + 10, 20)

        # Also boost Fear & Greed if it's showing some fear in a quiet market
        if s4_pts > 0:
            s4_pts = min(s4_pts + 10, 20)

    s5 = SignalDetail(
        name="breadth",
        value=round(data.adv_dec_ratio, 3),
        points=s5_pts,
        thresholds=BREADTH_RATIO_T,
        triggered_half=s5_half,
        triggered_full=s5_full,
    )

    stress_score = s1_pts + s3_pts
    capitulation_score = s4_pts + s5_pts
    persistence_score = s2_pts

    total = stress_score + capitulation_score + persistence_score

    # v2.0 Calculate Divergence Bonus
    divergence_bonus = 0
    divergence_flags = {}
    if getattr(data, 'history_window', None) is not None and not data.history_window.empty:
        div_res = check_divergences(
            data.price,
            data.vix,
            float(data.adv_dec_ratio),
            data.history_window,
            getattr(data, 'earnings_revisions_breadth', None),
            getattr(data, 'ohlcv_history', None)
        )
        divergence_bonus = div_res.get("bonus_score", 0)
        total += divergence_bonus
        divergence_flags = {
            "price_breadth": div_res.get("price_breadth", False),
            "price_vix": div_res.get("price_vix", False),
            "price_rsi": div_res.get("price_rsi", False),
            "price_mfi": div_res.get("price_mfi", False),
            "price_revision": div_res.get("price_revision", False),
        }

    # v3.0 Calculate Valuation Bonus
    valuation_bonus = 0
    if getattr(data, 'forward_pe', None) is not None:
        # If we had a deep history of PE, we'd pass it here. For MVP, we use static thresholds in fundamentals.py
        valuation_bonus = calculate_valuation_weight(data.forward_pe, None)
        total += valuation_bonus

    fcf_bonus = 0
    if getattr(data, 'fcf_yield', None) is not None:
        fcf_bonus = calculate_fcf_bonus(data.fcf_yield)
        total += fcf_bonus

    # v3.0 Calculate NDX Concentration Penalty
    concentration_penalty = 0
    ndx_concentration = getattr(data, 'ndx_concentration', 0.0)
    if ndx_concentration > 0.03:  # If Cap-weighted outperforms equal-weighted by > 3% on 50d MA
        concentration_penalty = -20
        total += concentration_penalty

    # v4.0 Phase 2: Liquidity Divergence
    liquidity_bonus = 0
    if data.liquidity_roc is not None and data.liquidity_roc > 0.5:
        # If QQQ is in a drawdown (>5%) or at least not at new highs, and liquidity is growing
        if drawdown > 0.05:
            liquidity_bonus = 10
            divergence_flags["liquidity_divergence"] = True

    total += liquidity_bonus
    divergence_bonus += liquidity_bonus

    # v4.0 Phase 2: Bond Volatility (MOVE) Bonus
    # High bond vol (>110) during an equity drawdown often signals capitulation
    move_bonus = 0
    if data.move_index is not None and data.move_index > 110:
        if drawdown > 0.05:
            move_bonus = 10
            divergence_flags["bond_vol_spike"] = True

    total += move_bonus
    divergence_bonus += move_bonus

    # v4.0 Phase 3: Sector Rotation Bonus
    rotation_bonus = 0
    if data.sector_rotation is not None and data.sector_rotation < -2.0:
        # XLP/QQQ ratio dropping > 2% over 20 days suggests rotation back to growth
        rotation_bonus = 10
        divergence_flags["growth_rotation"] = True
    total += rotation_bonus
    divergence_bonus += rotation_bonus

    # v5.0 Institutional Short Flow Confirmation
    short_flow_bonus = 0
    if data.short_vol_ratio is not None and data.short_vol_ratio > 0.60:
        # Extreme shorting into a drawdown often marks a local capitulation/squeeze point
        if drawdown > 0.05:
            short_flow_bonus = 10
            divergence_flags["short_squeeze_potential"] = True
    total += short_flow_bonus

    # v6.0 Mean Reversion Regime Bonus
    mr_bonus = 0
    mr_score = 0.0
    if data.ohlcv_history is not None:
        mr_score = calculate_mean_reversion_score(data.ohlcv_history['Close'])
        if mr_score < -2.0: # Significant downside deviation (mean reversion likely)
            mr_bonus = 10
            divergence_flags["mean_reversion_regime"] = True

    total += mr_bonus
    divergence_bonus += mr_bonus

    return Tier1Result(
        score=total,
        drawdown_52w=s1,
        ma200_deviation=s2,
        vix=s3,
        fear_greed=s4,
        breadth=s5,
        stress_score=stress_score,
        capitulation_score=capitulation_score,
        persistence_score=persistence_score,
        valuation_bonus=valuation_bonus,
        fcf_bonus=fcf_bonus,
        short_flow_bonus=short_flow_bonus,
        trailing_pe=getattr(data, 'trailing_pe', None),
        forward_pe=getattr(data, 'forward_pe', None),
        fcf_yield=getattr(data, 'fcf_yield', None),
        real_yield=getattr(data, 'real_yield', None),
        pe_source=getattr(data, 'pe_source', 'yfinance'),
        divergence_bonus=divergence_bonus,
        divergence_flags=divergence_flags,
        ndx_concentration=ndx_concentration,
        concentration_penalty=concentration_penalty,
        vix_zscore=data.vix_zscore,
        drawdown_zscore=data.drawdown_zscore,
        net_liquidity=data.net_liquidity,
        liquidity_roc=data.liquidity_roc,
        move_index=data.move_index,
        market_regime=regime,
        sector_rotation=data.sector_rotation,
        descent_velocity=descent_v,
    )

def identify_regime(vix_zscore: float) -> str:
    """Identify market regime based on VIX Z-Score (v4.2)."""
    if vix_zscore > 1.5:
        return "STORM"
    elif vix_zscore < -0.5:
        return "QUIET"
    else:
        return "NORMAL"

def calculate_descent_velocity(data: MarketData) -> tuple[str, int]:
    """
    v5.0: Calculate speed of descent to distinguish Panic vs Grind.
    Returns (Category, DaysSincePeak).
    """
    if data.days_since_52w_high is None:
        return "NORMAL", 0

    days = data.days_since_52w_high
    drawdown = (data.high_52w - data.price) / data.high_52w

    if drawdown < 0.05:
        return "NORMAL", days

    # PANIC: 10% drop in < 15 days, or 5% in < 7 days
    if (drawdown >= 0.10 and days < 15) or (drawdown >= 0.05 and days < 7):
        return "PANIC", days

    # GRIND: 10% drop that took more than 45 days
    if drawdown >= 0.10 and days > 45:
        return "GRIND", days

    return "NORMAL", days
