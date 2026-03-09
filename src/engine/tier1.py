"""
Tier-1 signal engine: 5 market signals with gradient scoring (0/10/20).

Each signal scores independently; total Tier-1 score ranges 0-100.
All thresholds are defined as module-level constants for easy M4 tuning.
"""
from __future__ import annotations

from src.models import MarketData, SignalDetail, Tier1Result
from src.engine.divergence import check_divergences
from src.engine.fundamentals import calculate_valuation_weight, calculate_fcf_bonus

# ── Gradient thresholds (low, high) ──────────────────────────────────────────
# Signal 1: 52-week high drawdown  (higher = more bullish)
DRAWDOWN_THRESHOLDS = (0.05, 0.10)      # <5%=0, 5-10%=10, >=10%=20

# Signal 2: MA200 deviation  (more negative = more bullish)
MA200_THRESHOLDS = (-0.03, -0.07)       # >-3%=0, -3~-7%=10, <=-7%=20

# Signal 3: VIX level  (higher = more bullish for contrarian)
VIX_THRESHOLDS = (22.0, 30.0)           # <22=0, 22-30=10, >30=20

# Signal 4: Fear & Greed (lower = more bullish)
FG_THRESHOLDS = (30, 20)                # >30=0, 20-30=10, <=20=20

# Signal 5: Market breadth (lower = more bullish / capitulation)
BREADTH_RATIO_T = (0.7, 0.4)            # advance/decline ratio
BREADTH_PCT50_T = (0.40, 0.25)          # pct of stocks above 50-day MA


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
    # Signal 1: 52-week drawdown
    drawdown = (data.high_52w - data.price) / data.high_52w
    s1_pts, s1_half, s1_full = _score_higher_better(drawdown, *DRAWDOWN_THRESHOLDS)
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

    # Signal 5: Market breadth (composite of adv_dec_ratio and pct_above_50d)
    # Both metrics: lower = more bullish → lower_better
    ratio_pts, ratio_half, ratio_full = _score_lower_better(
        data.adv_dec_ratio, BREADTH_RATIO_T[0], BREADTH_RATIO_T[1]
    )
    pct_pts, pct_half, pct_full = _score_lower_better(
        data.pct_above_50d, BREADTH_PCT50_T[0], BREADTH_PCT50_T[1]
    )
    # Breadth score: max of the two sub-signals (either indicator capitulating is informative)
    s5_pts = max(ratio_pts, pct_pts)
    # "half" if either triggered half; "full" only if BOTH are at full level
    s5_half = ratio_half or pct_half
    s5_full = ratio_full and pct_full
    s5 = SignalDetail(
        name="breadth",
        value=round(data.adv_dec_ratio, 3),
        points=s5_pts,
        thresholds=(BREADTH_RATIO_T, BREADTH_PCT50_T),
        triggered_half=s5_half,
        triggered_full=s5_full,
    )

    total = s1_pts + s2_pts + s3_pts + s4_pts + s5_pts

    # v2.0 Calculate Divergence Bonus
    divergence_bonus = 0
    divergence_flags = {}
    if getattr(data, 'history_window', None) is not None and not data.history_window.empty:
        div_res = check_divergences(
            data.price, 
            data.vix, 
            float(data.pct_above_50d), 
            data.history_window,
            getattr(data, 'earnings_revisions_breadth', None)
        )
        divergence_bonus = div_res.get("bonus_score", 0)
        total += divergence_bonus
        divergence_flags = {
            "price_breadth": div_res.get("price_breadth", False),
            "price_vix": div_res.get("price_vix", False),
            "price_rsi": div_res.get("price_rsi", False),
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

    return Tier1Result(
        score=total,
        drawdown_52w=s1,
        ma200_deviation=s2,
        vix=s3,
        fear_greed=s4,
        breadth=s5,
        valuation_bonus=valuation_bonus,
        fcf_bonus=fcf_bonus,
        trailing_pe=getattr(data, 'trailing_pe', None),
        forward_pe=getattr(data, 'forward_pe', None),
        fcf_yield=getattr(data, 'fcf_yield', None),
        us10y=getattr(data, 'us10y', None),
        divergence_bonus=divergence_bonus,
        divergence_flags=divergence_flags,
    )
