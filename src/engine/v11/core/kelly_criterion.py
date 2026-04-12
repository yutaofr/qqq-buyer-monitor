"""
True Kelly Criterion implementation math core (v1.0)
Strictly adheres to Orthogonal Logic.
"""
from typing import Dict

def compute_regime_expected_sharpe(
    posteriors: Dict[str, float],
    regime_sharpes: Dict[str, float]
) -> float:
    """E[Sharpe] = Σ P(regime_i) × Sharpe_i. Skips unknown regimes."""
    expected = 0.0
    for regime, prob in posteriors.items():
        if regime in regime_sharpes:
            expected += prob * regime_sharpes[regime]
    return expected

def compute_regime_sharpe_variance(
    posteriors: Dict[str, float],
    regime_sharpes: Dict[str, float],
    expected_sharpe: float
) -> float:
    """Var[Sharpe] = Σ P(regime_i) × (Sharpe_i - E[Sharpe])², min 1e-6"""
    var = 0.0
    for regime, prob in posteriors.items():
        if regime in regime_sharpes:
            var += prob * ((regime_sharpes[regime] - expected_sharpe) ** 2)
    return max(var, 1e-6)

def compute_kelly_fraction(
    *,
    posteriors: Dict[str, float],
    regime_sharpes: Dict[str, float],
    entropy: float,
    erp_percentile: float,
    kelly_scale: float = 0.5,
    erp_weight: float = 0.4
) -> float:
    """Computes bounded continuous Kelly fraction with ERP and entropy adjustments."""
    entropy_clipped = max(0.0, min(1.0, entropy))
    erp_clipped = max(0.0, min(1.0, erp_percentile))
    
    edge = compute_regime_expected_sharpe(posteriors, regime_sharpes)
    base_var = compute_regime_sharpe_variance(posteriors, regime_sharpes, edge)
    
    variance = base_var + (entropy_clipped ** 2)
    variance = max(variance, 1e-6)
    
    tilt = 1.0 + (erp_clipped - 0.5) * erp_weight
    
    raw_kelly = (edge * tilt) / variance
    fraction = raw_kelly * kelly_scale
    
    # Clip between -1.0 and 1.0
    return max(-1.0, min(1.0, fraction))

def kelly_fraction_to_deployment_state(kelly_fraction: float) -> str:
    """Maps [-1, 1] kelly fraction to categorical deployment states."""
    if kelly_fraction <= 0.0:
        return "DEPLOY_PAUSE"
    elif kelly_fraction <= 0.25:
        return "DEPLOY_SLOW"
    elif kelly_fraction <= 0.6:
        return "DEPLOY_BASE"
    else:
        return "DEPLOY_FAST"

def kelly_fraction_to_deployment_multiplier(kelly_fraction: float) -> float:
    """Maps [-1, 1] kelly fraction directly to deployment pacing multiplier."""
    from src.models.deployment import deployment_multiplier_for_state
    state = kelly_fraction_to_deployment_state(kelly_fraction)
    return deployment_multiplier_for_state(state)
