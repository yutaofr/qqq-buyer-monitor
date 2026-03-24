import logging
from enum import Enum

logger = logging.getLogger(__name__)

# If credit spread (bps) is above this threshold, trigger macroeconomic meltdown veto
CREDIT_SPREAD_CRISIS_THRESHOLD = 500.0
CREDIT_SPREAD_TRANSITION_STRESS_THRESHOLD = 400.0
CREDIT_SPREAD_TRANSITION_STRESS_CROSSOVER = 350.0
CREDIT_SPREAD_RICH_TIGHTENING_THRESHOLD = 300.0
EUPHORIC_CREDIT_SPREAD_THRESHOLD = 250.0
CRISIS_ERP_THRESHOLD = 1.0
RICH_TIGHTENING_ERP_THRESHOLD = 2.5
EUPHORIC_ERP_THRESHOLD = 5.0


class StructuralRegime(str, Enum):
    EUPHORIC = "EUPHORIC"
    RICH_TIGHTENING = "RICH_TIGHTENING"
    NEUTRAL = "NEUTRAL"
    TRANSITION_STRESS = "TRANSITION_STRESS"
    CRISIS = "CRISIS"


class ErpRegime(str, Enum):
    NORMAL = "Normal"
    DEFENSE = "Defense"
    AGGRESSIVE = "Aggressive"


def assess_structural_regime(
    credit_spread: float | None,
    erp: float | None,
) -> str:
    """
    Classify the structural macro regime using credit spread and ERP.

    The ladder is ordered from best to worst:
    EUPHORIC -> RICH_TIGHTENING -> NEUTRAL -> TRANSITION_STRESS -> CRISIS
    """
    if credit_spread is None and erp is None:
        return StructuralRegime.NEUTRAL.value

    if (
        (credit_spread is not None and credit_spread >= CREDIT_SPREAD_CRISIS_THRESHOLD)
        or (erp is not None and erp < CRISIS_ERP_THRESHOLD)
    ):
        logger.warning(
            "🚨 TIER-0 STRUCTURAL REGIME: CRISIS (spread=%s, erp=%s).",
            credit_spread,
            erp,
        )
        return StructuralRegime.CRISIS.value

    if (
        (credit_spread is not None and credit_spread < EUPHORIC_CREDIT_SPREAD_THRESHOLD)
        and (erp is not None and erp >= EUPHORIC_ERP_THRESHOLD)
    ):
        logger.info(
            "💎 TIER-0 STRUCTURAL REGIME: EUPHORIC (spread=%s, erp=%s).",
            credit_spread,
            erp,
        )
        return StructuralRegime.EUPHORIC.value

    if (
        (credit_spread is not None and credit_spread >= CREDIT_SPREAD_TRANSITION_STRESS_THRESHOLD)
        or (
            credit_spread is not None
            and credit_spread >= CREDIT_SPREAD_TRANSITION_STRESS_CROSSOVER
            and erp is not None
            and erp < RICH_TIGHTENING_ERP_THRESHOLD
        )
    ):
        logger.warning(
            "🧯 TIER-0 STRUCTURAL REGIME: TRANSITION_STRESS (spread=%s, erp=%s).",
            credit_spread,
            erp,
        )
        return StructuralRegime.TRANSITION_STRESS.value

    if (
        (credit_spread is not None and credit_spread >= CREDIT_SPREAD_RICH_TIGHTENING_THRESHOLD)
        or (erp is not None and erp < RICH_TIGHTENING_ERP_THRESHOLD)
    ):
        logger.warning(
            "🛡️ TIER-0 STRUCTURAL REGIME: RICH_TIGHTENING (spread=%s, erp=%s).",
            credit_spread,
            erp,
        )
        return StructuralRegime.RICH_TIGHTENING.value

    return StructuralRegime.NEUTRAL.value

def check_macro_regime(credit_spread: float | None, erp: float | None = None) -> bool:
    """
    Check if the macroeconomic environment is in a severe crisis (e.g. liquidity dry-up).
    Returns True if we are in a crisis/blowout regime, False otherwise.
    """
    if erp is None:
        if credit_spread is None:
            return False

        if credit_spread >= CREDIT_SPREAD_CRISIS_THRESHOLD:
            logger.warning(
                "🚨 TIER-0 MACRO MELTDOWN: Credit spread is %s bps (>= %s). Vetoing all buys.",
                credit_spread,
                CREDIT_SPREAD_CRISIS_THRESHOLD,
            )
            return True

        return False

    return assess_structural_regime(credit_spread, erp) == StructuralRegime.CRISIS.value

def check_erp_regime(forward_pe: float | None, real_yield: float | None) -> str:
    """
    Calculate Equity Risk Premium using Real Yield (ERP = 1/Forward PE - Real Yield).
    Returns 'Defense' if Real ERP < 2.5%, 'Aggressive' if Real ERP > 6.5%, Default is 'Normal'.
    """
    if forward_pe is None or real_yield is None or forward_pe <= 0:
        return ErpRegime.NORMAL.value

    # Note: Real Yield is in percentage (e.g. 2.25 for 2.25%)
    earnings_yield = (1.0 / forward_pe) * 100.0
    erp = earnings_yield - real_yield

    if erp < 2.5:
        logger.warning("🛡️ TIER-0 ERP REGIME: Defense mode active (Real ERP = %.2f%%). Risk premium too low.", erp)
        return ErpRegime.DEFENSE.value
    elif erp > 6.5:
        logger.info("💎 TIER-0 ERP REGIME: Aggressive mode active (Real ERP = %.2f%%). Outstanding historical value.", erp)
        return ErpRegime.AGGRESSIVE.value

    return ErpRegime.NORMAL.value
