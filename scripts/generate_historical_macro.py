"""Dev-only historical macro fixture builder for local smoke tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research.data_contracts import REQUIRED_HISTORICAL_MACRO_COLUMNS, validate_historical_macro_frame

BUILD_VERSION = "dev-fixture"
SOURCE_TAG = "synthetic_fixture"
DEFAULT_OUTPUT_PATH = Path("data/dev/macro_historical_fixture.csv")


def _build_dev_fixture_frame() -> pd.DataFrame:
    dates = pd.date_range(start="1999-01-01", end="2026-03-22", freq="B")
    frame = pd.DataFrame({"observation_date": dates})

    frame["credit_spread_bps"] = 350.0
    frame["real_yield_10y_pct"] = 1.5
    frame["net_liquidity_usd_bn"] = 250.0
    frame["funding_stress_flag"] = 0

    regimes = [
        ("2000-03-10", "2003-12-31", 1000.0, 0.5, 180.0, 1),
        ("2008-09-01", "2009-06-01", 2000.0, 1.0, 120.0, 1),
        ("2020-02-15", "2020-05-01", 800.0, 0.8, 90.0, 1),
        ("2021-06-01", "2021-11-01", 200.0, -1.0, 270.0, 0),
        ("2022-01-01", "2022-12-31", 500.0, 2.0, 150.0, 0),
    ]
    for start, end, spread_bps, real_yield, liquidity_bn, stressed in regimes:
        mask = (frame["observation_date"] >= start) & (frame["observation_date"] <= end)
        frame.loc[mask, "credit_spread_bps"] = spread_bps
        frame.loc[mask, "real_yield_10y_pct"] = real_yield
        frame.loc[mask, "net_liquidity_usd_bn"] = liquidity_bn
        frame.loc[mask, "funding_stress_flag"] = stressed

    frame["credit_acceleration_pct_10d"] = frame["credit_spread_bps"].pct_change(periods=10).mul(100.0).fillna(0.0)
    frame["liquidity_roc_pct_4w"] = frame["net_liquidity_usd_bn"].pct_change(periods=20).mul(100.0).fillna(0.0)
    frame["effective_date"] = frame["observation_date"] + pd.offsets.BDay(1)
    frame["source_credit_spread"] = SOURCE_TAG
    frame["source_real_yield"] = SOURCE_TAG
    frame["source_net_liquidity"] = SOURCE_TAG
    frame["source_funding_stress"] = SOURCE_TAG
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
