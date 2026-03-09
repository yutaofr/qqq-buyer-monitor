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

def check_erp_regime(forward_pe: float | None, us10y: float | None) -> str:
    """
    Calculate Equity Risk Premium (ERP = 1/Forward PE - US10Y).
    Returns 'Defense' if ERP < 1%, 'Aggressive' if ERP > 5%, Default is 'Normal'.
    """
    if forward_pe is None or us10y is None or forward_pe <= 0:
        return "Normal"
        
    # Note: US10Y is in percentage (e.g. 4.25 for 4.25%)
    earnings_yield = (1.0 / forward_pe) * 100.0
    erp = earnings_yield - us10y
    
    if erp < 1.0:
        logger.warning("🛡️ TIER-0 ERP REGIME: Defense mode active (ERP = %.2f%%). Risk premium too low.", erp)
        return "Defense"
    elif erp > 5.0:
        logger.info("💎 TIER-0 ERP REGIME: Aggressive mode active (ERP = %.2f%%). Outstanding historical value.", erp)
        return "Aggressive"
        
    return "Normal"
