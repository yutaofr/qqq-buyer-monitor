import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Very rough static thresholds for QQQ PE if history is not deep enough to calculate a Z-Score
# QQQ Forward PE > 32 is historically very expensive, < 22 is cheap
CHEAP_PE_THRESHOLD = 22.0
EXPENSIVE_PE_THRESHOLD = 32.0


def calculate_pe_zscore(current_pe: float | None, hist_pe_series: pd.Series | None) -> float | None:
    """
    Calculate the Z-Score of the current Forward PE against its historical window.
    """
    if current_pe is None:
        return None

    if hist_pe_series is None or len(hist_pe_series.dropna()) < 10:
        # Not enough history to calculate Z-Score
        return None

    mean_pe = hist_pe_series.mean()
    std_pe = hist_pe_series.std()

    if std_pe == 0:
        return 0.0

    z_score = (current_pe - mean_pe) / std_pe
    return z_score


def calculate_valuation_weight(current_pe: float | None, hist_pe_series: pd.Series | None) -> int:
    """
    Calculate a base-score modifier (-10 to +10) for Tier 1 based on Forward PE valuation.
    """
    if current_pe is None:
        return 0

    # Try mapping by Z-score first
    z_score = calculate_pe_zscore(current_pe, hist_pe_series)

    if z_score is not None:
        if z_score <= -1.0: # 1 SD below mean -> cheap
            logger.info("Valuation: Forward PE is heavily undervalued (Z: %.2f). Granting bonus.", z_score)
            return 10
        elif z_score >= 2.0: # 2 SD above mean -> expensive
            logger.warning("Valuation: Forward PE is in bubble territory (Z: %.2f). Applying penalty.", z_score)
            return -10
        elif z_score >= 1.5:
            return -5
        elif z_score <= -0.5:
            return 5
        else:
            return 0

    # Fallback to absolute thresholds if history is small
    if current_pe <= CHEAP_PE_THRESHOLD:
        logger.info("Valuation: Absolute PE (%.1f) is low. Granting bonus.", current_pe)
        return 10
    elif current_pe >= EXPENSIVE_PE_THRESHOLD:
        logger.warning("Valuation: Absolute PE (%.1f) is high. Applying penalty.", current_pe)
        return -10

    return 0

def calculate_fcf_bonus(fcf_yield: float | None) -> int:
    """
    Calculate a bonus score for Tier 1 based on absolute FCF Yield.
    If FCF Yield > 4.5%, return +15.
    """
    if fcf_yield is None:
        return 0

    if fcf_yield > 4.5:
        logger.info("💰 FCF VALUATION BASELINE: Asset is extremely cheap (FCF Yield = %.2f%%). Granting +15 bonus.", fcf_yield)
        return 15

    return 0
