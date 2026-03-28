#!/usr/bin/env python3
"""Build the canonical v7.0 historical macro dataset."""
from __future__ import annotations

import argparse

from src.research.historical_macro_builder import build_and_summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the v7.0 canonical historical macro dataset")
    parser.add_argument(
        "--output",
        default="data/macro_historical_dump.csv",
        help="Output CSV path (default: data/macro_historical_dump.csv)",
    )
    args = parser.parse_args(argv)

    df, summary = build_and_summarize(output_path=args.output)
    print(f"Built {summary['rows']} rows")
    print(f"First observation date: {summary['first_observation_date']}")
    print(f"Last observation date: {summary['last_observation_date']}")
    print("Coverage:")
    for key in (
        "credit_spread_bps",
        "credit_acceleration_pct_10d",
        "forward_pe",
        "erp_pct",
        "real_yield_10y_pct",
        "net_liquidity_usd_bn",
        "liquidity_roc_pct_4w",
        "funding_stress_flag",
    ):
        print(f"  {key}: {summary['coverage'][key]:.3f}")

    return 0 if not df.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
