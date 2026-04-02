import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class SovereignMemoryBooster:
    """
    V11 DNA: The bootstrap guardian.
    Provides synthetic high-fidelity historical memory to seed the Bayesian engine.
    """

    def __init__(
        self,
        macro_path: str = "data/macro_historical_dump.csv",
        regime_path: str = "data/v11_poc_phase1_results.csv",
    ):
        self.macro_path = Path(macro_path)
        self.regime_path = Path(regime_path)

    def ensure_baseline(self, force: bool = False) -> bool:
        """Checks if files exist and are non-empty. Bootstrap if needed."""
        if not force and self.macro_path.exists() and self.regime_path.exists():
            # Basic sanity check
            try:
                m = pd.read_csv(self.macro_path)
                r = pd.read_csv(self.regime_path)
                if len(m) > 100 and len(r) > 100:
                    return False  # Already healthy
            except Exception:
                pass

        logger.warning("V11 DNA: Sovereign Memory baseline missing or corrupt. Bootstrapping...")
        self.generate_synthetic_baseline()
        return True

    def generate_synthetic_baseline(self, start_year: int = 2010, seed: int = 115):
        """
        Generates 10+ years of synthetic macro data with distinct regime fingerprints.
        Calibration adjusted for Late Cycle sensitivity (v11.25 DNA edit).
        """
        # Ensure Deterministic System & Engineering Integrity (v12.01)
        np.random.seed(seed)

        end_date = datetime.now()
        dates = pd.date_range(start=f"{start_year}-01-01", end=end_date, freq="D")

        data = []
        for d in dates:
            year = d.year
            # Macro-Cyclic Logic (Approximate history)
            if year == 2020:
                if d.month <= 2:
                    regime = "MID_CYCLE"
                elif d.month == 3:
                    regime = "BUST" if d.day <= 23 else "RECOVERY"
                else:
                    regime = "RECOVERY"
            elif year == 2022:
                regime = "LATE_CYCLE" if d.month <= 9 else "BUST"
            elif year == 2024:
                regime = "MID_CYCLE" if d.month <= 6 else "LATE_CYCLE"
            elif year < 2020:
                cycle_phase = year % 4
                if cycle_phase == 0:
                    regime = "RECOVERY"
                elif cycle_phase == 1:
                    regime = "MID_CYCLE"
                elif cycle_phase == 2:
                    regime = "LATE_CYCLE"
                else:
                    regime = "BUST"
            else:
                regime = "MID_CYCLE"

            if regime == "MID_CYCLE":
                erp = 0.045 + np.random.normal(0, 0.005)  # Relaxed variance
                yield_10y = 0.015 + np.random.normal(0, 0.003)
                spread = 280 + np.random.normal(0, 20)
                liq = 6100 + np.random.normal(0, 50)
            elif regime == "LATE_CYCLE":
                erp = 0.020 + np.random.normal(0, 0.005)  # Target: 2.0%
                yield_10y = 0.035 + np.random.normal(0, 0.005)  # Target: 3.5% (Realistic Late Stage)
                spread = 350 + np.random.normal(0, 20)  # Target: 350bps
                liq = 5800 + np.random.normal(0, 60)
            elif regime == "RECOVERY":
                erp = 0.060 + np.random.normal(0, 0.01)
                yield_10y = 0.012 + np.random.normal(0, 0.003)
                spread = 410 + np.random.normal(0, 50)
                liq = 6600 + np.random.normal(0, 100)
            elif regime == "BUST":
                erp = 0.08 + np.random.normal(0, 0.01)
                yield_10y = 0.005 + np.random.normal(0, 0.001)
                spread = 750 + np.random.normal(0, 80)
                liq = 5400 + np.random.normal(0, 150)
            else:  # CAPITULATION (Rare extreme)
                erp = 0.10 + np.random.normal(0, 0.02)
                yield_10y = 0.002 + np.random.normal(0, 0.001)
                spread = 950 + np.random.normal(0, 120)
                liq = 4800 + np.random.normal(0, 200)

            data.append(
                {
                    "observation_date": d,
                    "effective_date": d,  # Legacy alignment
                    "regime": regime,
                    "erp_pct": erp,
                    "real_yield_10y_pct": yield_10y,
                    "credit_spread_bps": spread,
                    "net_liquidity_usd_bn": liq,
                    # Legacy contract artifacts (v9 compatibility)
                    "credit_acceleration_pct_10d": 0.0,
                    "forward_pe": (
                        100.0 / (erp + yield_10y + 0.05) if erp + yield_10y + 0.05 > 0 else 20.0
                    ),
                    "liquidity_roc_pct_4w": 0.0,
                    "funding_stress_flag": False,
                    "source_credit_spread": "synthetic_dna",
                    "source_forward_pe": "synthetic_dna",
                    "source_erp": "synthetic_dna",
                    "source_real_yield": "synthetic_dna",
                    "source_net_liquidity": "synthetic_dna",
                    "source_funding_stress": "synthetic_dna",
                    "build_version": "v11.x-dna-bootstrap",
                }
            )

        df = pd.DataFrame(data)
        self.macro_path.parent.mkdir(parents=True, exist_ok=True)

        # Save split datasets
        # Ensure macro dump has all columns for research contracts
        macro_cols = list(df.columns)
        macro_cols.remove("regime")
        regime_cols = ["observation_date", "regime"]

        df[macro_cols].to_csv(self.macro_path, index=False)
        df[regime_cols].to_csv(self.regime_path, index=False)
        logger.info(f"V11 DNA: Sovereign Memory reseeded with {len(df)} points.")
