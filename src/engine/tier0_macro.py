import logging

logger = logging.getLogger(__name__)

# If credit spread (bps) is above this threshold, trigger macroeconomic meltdown veto
CREDIT_SPREAD_CRISIS_THRESHOLD = 500.0

def check_macro_regime(credit_spread: float | None) -> bool:
    """
    Check if the macroeconomic environment is in a severe crisis (e.g. liquidity dry-up).
    Returns True if we are in a crisis/blowout regime, False otherwise.
    """
    if credit_spread is None:
        return False
        
    if credit_spread >= CREDIT_SPREAD_CRISIS_THRESHOLD:
        logger.warning(
            "🚨 TIER-0 MACRO MELTDOWN: Credit spread is %s bps (>= %s). Vetoing all buys.",
            credit_spread, CREDIT_SPREAD_CRISIS_THRESHOLD
        )
        return True
        
    return False
