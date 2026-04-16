from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from src.liquidity.engine.bocpd import BOCPDEngine
from src.liquidity.control.allocator import Allocator


class StaleTickError(Exception):
    """Raised when an out-of-order tick attempts to penetrate the stateful buffers."""
    pass


class LiquidityPipeline:
    """State Machine Pipeline grouping Feature Extractor, BOCPD, and Allocator.
    
    Exposes a true streaming API `step(raw_obs)` which completely handles
    raw data ingestion, incremental PCA, indicator rolling, burn-in state tracking, 
    and outputs the final target QLD weight along with a structured diagnostic log.
    """

    def __init__(self, config: dict, burn_in: int = 252) -> None:
        from src.liquidity.engine.feature_extractor import StreamingFeatureExtractor
        self.extractor = StreamingFeatureExtractor(config)
        self._bocpd = BOCPDEngine(config)
        self._alloc = Allocator(config)
        self._burn_in_total = burn_in
        self._burn_in_count = 0
        self._last_timestamp: pd.Timestamp | None = None

    def dump_state(self) -> dict:
        """Serialize full pipeline state into a portable, Bit-identical friendly dict."""
        return {
            "extractor": self.extractor.dump_state(),
            "bocpd": self._bocpd.dump_state(),
            "allocator": self._alloc.dump_state(),
            "burn_in_count": self._burn_in_count,
            "last_timestamp_iso": self._last_timestamp.isoformat() if self._last_timestamp else None,
        }
        
    def load_state(self, state_dict: dict) -> None:
        """Restore mathematical continuity across a network process restart."""
        self.extractor.load_state(state_dict["extractor"])
        self._bocpd.load_state(state_dict["bocpd"])
        self._alloc.load_state(state_dict["allocator"])
        self._burn_in_count = state_dict["burn_in_count"]
        iso_str = state_dict.get("last_timestamp_iso")
        self._last_timestamp = pd.Timestamp(iso_str) if iso_str else None

    def step(self, timestamp: pd.Timestamp, raw_obs: dict) -> Tuple[float, dict]:
        """Process one tick of raw market observations with monotonicity guarantee."""
        if self._last_timestamp is not None and timestamp <= self._last_timestamp:
            raise StaleTickError(f"Monotonicity breach: {timestamp} <= {self._last_timestamp}")
        self._last_timestamp = timestamp
        
        x_t, lambda_macro = self.extractor.step(raw_obs)
        # BOCPD natively marginalizes NaN dimensions securely now.
        p_cp = self._bocpd.update(x_t, lambda_macro)
        regime_diag = self._bocpd.last_regime_diagnostics
        regime_severity = float(regime_diag["regime_severity"])

        # 2. Check burn-in
        if self._burn_in_count < self._burn_in_total:
            remaining = self._burn_in_total - self._burn_in_count - 1
            self._burn_in_count += 1
            return 0.0, {
                "state": "burn_in",
                "burn_in_remaining": remaining,
            }

        # 3. Process allocation output
        weight, alloc_log = self._alloc.step(
            p_cp,
            lambda_macro,
            regime_severity_raw=regime_severity,
            regime_sigma2_spread=regime_diag.get("regime_sigma2_spread"),
            qqq_price=raw_obs.get("qqq_price"),
            qqq_sma200=raw_obs.get("qqq_sma200"),
        )
        
        # 4. Amalgamate diagnostic log to match existing runner API verbatim
        log = {
            "state":           "active",
            "weight":          weight,
            "p_cp":            p_cp,
            "s_t":             alloc_log["s_t"],
            "s_cp_t":          alloc_log["s_cp_t"],
            "s_level_t":       alloc_log["s_level_t"],
            "regime_severity": regime_severity,
            "regime_severity_base": regime_diag["regime_severity_base"],
            "regime_resonance_pr": regime_diag["regime_resonance_pr"],
            "regime_resonance_multiplier": regime_diag["regime_resonance_multiplier"],
            "regime_severity_norm": alloc_log["regime_severity_norm"],
            "regime_severity_floor": alloc_log["regime_severity_floor"],
            "regime_severity_ceil": alloc_log["regime_severity_ceil"],
            "vol_guard_cap": alloc_log.get("vol_guard_cap", 1.0),
            "dominant_run_length": regime_diag["dominant_run_length"],
            "dominant_run_prob": regime_diag["dominant_run_prob"],
            "regime_sigma2_ed": regime_diag["regime_sigma2_ed"],
            "regime_sigma2_spread": regime_diag["regime_sigma2_spread"],
            "regime_sigma2_fisher": regime_diag["regime_sigma2_fisher"],
            "signal":          alloc_log["signal"],
            "days_held":       alloc_log["days_held"],
            "circuit_breaker": alloc_log["circuit_breaker"],
            "momentum_lockout": alloc_log.get("momentum_lockout", False),
            "l_target":        alloc_log["l_target"],
            "l_final":         alloc_log["l_final"],
            "qld":             alloc_log["qld"],
            "qqq":             alloc_log["qqq"],
            "cash":            alloc_log["cash"],
            "tau_t":           self._bocpd.last_tau,
            "lambda_macro":    lambda_macro,
            "ll_spread_actual": self._bocpd.last_LL_spread_actual,
            "ll_spread_base":  self._bocpd.last_LL_spread_base,
            "x_t":             x_t,
        }
        
        return weight, log
