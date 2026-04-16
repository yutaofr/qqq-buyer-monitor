"""Configuration loader for the ED+BOCPD liquidity warning system.

Loads parameters from bocpd_params.json, which serves as the single source
of truth for all numerical constants across the engine, control chain, and
backtest harness.
"""

import json
from pathlib import Path


def load_config() -> dict:
    """Load and return the complete parameter registry.

    Returns:
        dict with top-level keys: hazard, nig_priors, aema, deadband,
        hold_period, mapping, execution, price_loader, ed_signal, proxy_universe,
        macro_hazard, overdrive, forgetting, regime_severity.
    """
    path = Path(__file__).parent / "resources" / "bocpd_params.json"
    with open(path) as f:
        return json.load(f)
