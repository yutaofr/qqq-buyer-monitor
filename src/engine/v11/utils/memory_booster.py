import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── V12+ Regime-Conditioned Parameter Table ──────────────────────────────
# Each regime has physically-realistic mean values for all 17 orthogonal
# factors consumed by the Conductor feature seeder.
_REGIME_PARAMS: dict[str, dict[str, float]] = {
    "MID_CYCLE": {
        "erp_pct": 0.045,
        "erp_ttm_pct": 0.045,
        "real_yield_10y_pct": 0.015,
        "credit_spread_bps": 280.0,
        "net_liquidity_usd_bn": 6100.0,
        "treasury_vol_21d": 0.0008,
        "copper_gold_ratio": 0.0015,
        "breakeven_10y": 0.025,
        "core_capex_mm": 3000.0,
        "usdjpy": 130.0,
        "qqq_close": 400.0,
        "qqq_volume": 50_000_000.0,
        "pmi_proxy_manemp": 12800.0,
        "unemployment_rate": 3.8,
        "job_openings": 9500.0,
        "stress_vix": 15.0,
        "stress_vix3m": 17.0,
    },
    "LATE_CYCLE": {
        "erp_pct": 0.020,
        "erp_ttm_pct": 0.020,
        "real_yield_10y_pct": 0.035,
        "credit_spread_bps": 350.0,
        "net_liquidity_usd_bn": 5800.0,
        "treasury_vol_21d": 0.0012,
        "copper_gold_ratio": 0.0013,
        "breakeven_10y": 0.023,
        "core_capex_mm": 2800.0,
        "usdjpy": 145.0,
        "qqq_close": 380.0,
        "qqq_volume": 60_000_000.0,
        "pmi_proxy_manemp": 12600.0,
        "unemployment_rate": 4.2,
        "job_openings": 8500.0,
        "stress_vix": 22.0,
        "stress_vix3m": 24.0,
    },
    "BUST": {
        "erp_pct": 0.08,
        "erp_ttm_pct": 0.08,
        "real_yield_10y_pct": 0.005,
        "credit_spread_bps": 750.0,
        "net_liquidity_usd_bn": 5400.0,
        "treasury_vol_21d": 0.0020,
        "copper_gold_ratio": 0.0010,
        "breakeven_10y": 0.018,
        "core_capex_mm": 2400.0,
        "usdjpy": 105.0,
        "qqq_close": 280.0,
        "qqq_volume": 90_000_000.0,
        "pmi_proxy_manemp": 12200.0,
        "unemployment_rate": 5.5,
        "job_openings": 6500.0,
        "stress_vix": 35.0,
        "stress_vix3m": 32.0,
    },
    "RECOVERY": {
        "erp_pct": 0.060,
        "erp_ttm_pct": 0.060,
        "real_yield_10y_pct": 0.012,
        "credit_spread_bps": 410.0,
        "net_liquidity_usd_bn": 6600.0,
        "treasury_vol_21d": 0.0010,
        "copper_gold_ratio": 0.0016,
        "breakeven_10y": 0.022,
        "core_capex_mm": 2600.0,
        "usdjpy": 115.0,
        "qqq_close": 320.0,
        "qqq_volume": 70_000_000.0,
        "pmi_proxy_manemp": 12400.0,
        "unemployment_rate": 4.8,
        "job_openings": 7500.0,
        "stress_vix": 25.0,
        "stress_vix3m": 26.0,
    },
}

# Noise standard deviations (fraction of mean, capped at reasonable levels)
_NOISE_STD: dict[str, float] = {
    "erp_pct": 0.005,
    "erp_ttm_pct": 0.005,
    "real_yield_10y_pct": 0.003,
    "credit_spread_bps": 20.0,
    "net_liquidity_usd_bn": 50.0,
    "treasury_vol_21d": 0.0003,
    "copper_gold_ratio": 0.0002,
    "breakeven_10y": 0.002,
    "core_capex_mm": 200.0,
    "usdjpy": 5.0,
    "qqq_close": 20.0,
    "qqq_volume": 10_000_000.0,
    "pmi_proxy_manemp": 50.0,
    "unemployment_rate": 0.2,
    "job_openings": 400.0,
    "stress_vix": 3.0,
    "stress_vix3m": 3.0,
}


def _assign_regime(d: pd.Timestamp) -> str:
    """Historically-approximate regime assignment for synthetic data."""
    year, month, day = d.year, d.month, d.day
    if year == 2020:
        if month <= 2:
            return "MID_CYCLE"
        elif month == 3:
            return "BUST" if day <= 23 else "RECOVERY"
        else:
            return "RECOVERY"
    elif year == 2022:
        return "LATE_CYCLE" if month <= 9 else "BUST"
    elif year == 2024:
        return "MID_CYCLE" if month <= 6 else "LATE_CYCLE"
    elif year < 2020:
        cycle_phase = year % 4
        if cycle_phase == 0:
            return "RECOVERY"
        elif cycle_phase == 1:
            return "MID_CYCLE"
        elif cycle_phase == 2:
            return "LATE_CYCLE"
        else:
            return "BUST"
    return "MID_CYCLE"


class SovereignMemoryBooster:
    """
    V12+ DNA: The bootstrap guardian.
    Generates synthetic high-fidelity historical memory covering ALL 51 columns
    required by the V12 orthogonal conductor and the baseline (Mud Tractor / Sidecar)
    subsystems.
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
            try:
                m = pd.read_csv(self.macro_path)
                r = pd.read_csv(self.regime_path)
                if len(m) > 100 and len(r) > 100:
                    return False  # Already healthy
            except Exception:
                pass

        logger.warning("V12 DNA: Sovereign Memory baseline missing or corrupt. Bootstrapping...")
        self.generate_synthetic_baseline()
        return True

    def generate_synthetic_baseline(self, start_year: int = 2010, seed: int = 115) -> None:
        """
        Generates 10+ years of synthetic macro data with regime-conditioned
        distributions covering all 51 columns required by the V12+ conductor.
        """
        np.random.seed(seed)

        end_date = datetime.now()
        dates = pd.date_range(start=f"{start_year}-01-01", end=end_date, freq="D")

        data: list[dict] = []
        for d in dates:
            regime = _assign_regime(d)
            params = _REGIME_PARAMS[regime]

            row: dict = {
                "observation_date": d,
                "effective_date": d,
                "build_version": "v12.0-dna-bootstrap",
                "regime": regime,
            }

            # Generate all V12+ factor values with regime-specific noise
            for field, mean_val in params.items():
                noise_std = _NOISE_STD.get(field, abs(mean_val) * 0.05)
                row[field] = mean_val + np.random.normal(0, noise_std)

            # Derived fields
            erp = row["erp_pct"]
            yield_10y = row["real_yield_10y_pct"]
            spread = row["credit_spread_bps"]

            row["forward_pe"] = (
                100.0 / (erp + yield_10y + 0.05) if erp + yield_10y + 0.05 > 0 else 20.0
            )
            row["credit_acceleration_pct_10d"] = np.random.normal(0, 0.5)
            row["liquidity_roc_pct_4w"] = np.random.normal(0, 1.0)
            row["funding_stress_flag"] = int(spread >= 500.0)
            row["reference_capital"] = 100_000.0
            row["current_nav"] = 100_000.0

            # Breadth / NDX concentration (unavailable in bootstrap)
            row["adv_dec_ratio"] = np.nan
            row["ndx_concentration"] = np.nan

            # Quality scores
            row["qqq_close_quality_score"] = 1.0
            row["qqq_volume_quality_score"] = 1.0
            row["breadth_quality_score"] = 0.0
            row["ndx_concentration_quality_score"] = 0.0

            # Source tags for every factor
            row["source_credit_spread"] = "synthetic_dna"
            row["source_real_yield"] = "synthetic_dna"
            row["source_net_liquidity"] = "synthetic_dna"
            row["source_treasury_vol"] = "synthetic_dna"
            row["source_copper_gold"] = "synthetic_dna"
            row["source_breakeven"] = "synthetic_dna"
            row["source_core_capex"] = "synthetic_dna"
            row["source_usdjpy"] = "synthetic_dna"
            row["source_erp_ttm"] = "synthetic_dna"
            row["source_qqq_close"] = "synthetic_dna"
            row["source_qqq_volume"] = "synthetic_dna"
            row["source_forward_pe"] = "synthetic_dna"
            row["source_erp"] = "synthetic_dna"
            row["source_funding_stress"] = "synthetic_dna"
            row["source_breadth_proxy"] = "unavailable:breadth"
            row["source_ndx_concentration"] = "unavailable:ndx_concentration"
            row["source_pmi_proxy"] = "synthetic_dna"
            row["source_unemployment"] = "synthetic_dna"
            row["source_job_openings"] = "synthetic_dna"

            data.append(row)

        df = pd.DataFrame(data)
        self.macro_path.parent.mkdir(parents=True, exist_ok=True)

        # Save split datasets
        regime_cols = ["observation_date", "regime"]
        macro_cols = [c for c in df.columns if c != "regime"]

        df[macro_cols].to_csv(self.macro_path, index=False)
        df[regime_cols].to_csv(self.regime_path, index=False)
        logger.info(
            "V12 DNA: Sovereign Memory reseeded with %d points covering all 51 columns.", len(df)
        )
