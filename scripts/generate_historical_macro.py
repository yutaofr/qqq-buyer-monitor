"""Dev-only v12 historical macro fixture builder for local smoke tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.research.data_contracts import (
    REQUIRED_HISTORICAL_MACRO_COLUMNS,
    validate_historical_macro_frame,
)

BUILD_VERSION = "dev-fixture"
SOURCE_TAG = "synthetic_fixture"
DEFAULT_OUTPUT_PATH = Path("data/dev/macro_historical_fixture.csv")


def _build_dev_fixture_frame() -> pd.DataFrame:
    dates = pd.date_range(start="1999-01-01", end="2026-03-22", freq="B")
    frame = pd.DataFrame({"observation_date": dates})

    frame["credit_spread_bps"] = 350.0
    frame["real_yield_10y_pct"] = 0.015
    frame["net_liquidity_usd_bn"] = 250.0
    frame["treasury_vol_21d"] = 0.006
    frame["copper_gold_ratio"] = 0.18
    frame["breakeven_10y"] = 0.022
    frame["core_capex_mm"] = 12.0
    frame["usdjpy"] = 110.0
    frame["erp_ttm_pct"] = 0.027

    regimes = [
        ("2000-03-10", "2003-12-31", 1000.0, 0.005, 120.0, 0.012, 0.013, 180.0, 0.14, 1),
        ("2008-09-01", "2009-06-01", 2000.0, 0.010, 95.0, 0.060, 0.008, 120.0, 0.11, 1),
        ("2020-02-15", "2020-05-01", 800.0, 0.012, 103.0, 0.052, 0.010, 90.0, 0.15, 1),
        ("2021-06-01", "2021-11-01", 200.0, -0.010, 112.0, 0.018, 0.026, 270.0, 0.21, 0),
        ("2022-01-01", "2022-12-31", 500.0, 0.020, 135.0, 0.040, 0.018, 150.0, 0.17, 0),
    ]
    for start, end, spread_bps, real_yield, usdjpy, erp_ttm, treasury_vol, liquidity_bn, cg_ratio, stressed in regimes:
        mask = (frame["observation_date"] >= start) & (frame["observation_date"] <= end)
        frame.loc[mask, "credit_spread_bps"] = spread_bps
        frame.loc[mask, "real_yield_10y_pct"] = real_yield
        frame.loc[mask, "usdjpy"] = usdjpy
        frame.loc[mask, "erp_ttm_pct"] = erp_ttm
        frame.loc[mask, "treasury_vol_21d"] = treasury_vol
        frame.loc[mask, "net_liquidity_usd_bn"] = liquidity_bn
        frame.loc[mask, "copper_gold_ratio"] = cg_ratio
        frame.loc[mask, "funding_stress_flag"] = stressed

    frame["breakeven_10y"] = 0.018 + np.sin(np.linspace(0.0, 40.0, len(frame))) * 0.004
    frame["core_capex_mm"] = np.repeat(np.linspace(8.0, 20.0, len(frame) // 21 + 2), 21)[: len(frame)]
    frame["effective_date"] = frame["observation_date"]
    frame["source_credit_spread"] = SOURCE_TAG
    frame["source_real_yield"] = SOURCE_TAG
    frame["source_net_liquidity"] = SOURCE_TAG
    frame["source_treasury_vol"] = SOURCE_TAG
    frame["source_copper_gold"] = SOURCE_TAG
    frame["source_breakeven"] = SOURCE_TAG
    frame["source_core_capex"] = SOURCE_TAG
    frame["source_usdjpy"] = SOURCE_TAG
    frame["source_erp_ttm"] = SOURCE_TAG
    frame["build_version"] = BUILD_VERSION

    frame = frame.loc[:, REQUIRED_HISTORICAL_MACRO_COLUMNS].copy()
    validate_historical_macro_frame(frame)
    return frame


def build_dev_fixture_historical_macro_dataset(output_path: str | Path = DEFAULT_OUTPUT_PATH) -> pd.DataFrame:
    """Build the canonical CSV used for local smoke testing only."""
    frame = _build_dev_fixture_frame()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    print(f"Wrote dev-only historical macro fixture to {output_path}")
    return frame


def main() -> None:
    build_dev_fixture_historical_macro_dataset()


if __name__ == "__main__":
    main()
