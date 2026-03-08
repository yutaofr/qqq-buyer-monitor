"""
QQQ Monitor — main entry point.

Usage:
    python -m src.main                  # run full pipeline
    python -m src.main --json           # output JSON report
    python -m src.main --history 30     # print last 30 records
    python -m src.main --no-save        # run without writing to DB
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger("qqq_monitor")


def _run(args: argparse.Namespace) -> None:
    """Execute the full signal pipeline."""
    from src.collector.price import fetch_price_data
    from src.collector.vix import fetch_vix
    from src.collector.fear_greed import fetch_fear_greed
    from src.collector.options import fetch_options_chain
    from src.collector.breadth import fetch_breadth
    from src.models import MarketData
    from src.engine.tier1 import calculate_tier1
    from src.engine.tier2 import calculate_tier2
    from src.engine.aggregator import aggregate
    from src.output.cli import print_signal
    from src.output.report import to_json
    from src.store.db import save_signal

    logger.info("Fetching market data…")

    errors: list[str] = []

    # Price
    try:
        price_data = fetch_price_data()
    except Exception as exc:  # noqa: BLE001
        logger.error("Price fetch failed: %s", exc)
        sys.exit(1)

    # VIX
    try:
        vix = fetch_vix()
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX fetch failed, using neutral value 20.0: %s", exc)
        errors.append(f"VIX: {exc}")
        vix = 20.0

    # Fear & Greed
    try:
        fg = fetch_fear_greed()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fear & Greed fetch failed, using neutral value 50: %s", exc)
        errors.append(f"F&G: {exc}")
        fg = 50

    # Options
    try:
        options_df = fetch_options_chain()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Options fetch failed, Tier-2 will be neutral: %s", exc)
        errors.append(f"Options: {exc}")
        options_df = None

    # Breadth
    try:
        breadth = fetch_breadth()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Breadth fetch failed, using neutral values: %s", exc)
        errors.append(f"Breadth: {exc}")
        breadth = {"adv_dec_ratio": 0.6, "pct_above_50d": 0.40}

    if errors:
        logger.warning("Some data sources failed (degraded mode): %s", errors)

    # Build MarketData
    market_data = MarketData(
        date=price_data["date"],
        price=price_data["price"],
        ma200=price_data["ma200"],
        high_52w=price_data["high_52w"],
        vix=vix,
        fear_greed=fg,
        adv_dec_ratio=breadth["adv_dec_ratio"],
        pct_above_50d=breadth["pct_above_50d"],
        options_df=options_df,
    )

    logger.info("Running signal engines…")
    tier1 = calculate_tier1(market_data)
    tier2 = calculate_tier2(market_data.price, market_data.options_df)
    result = aggregate(market_data.date, market_data.price, tier1, tier2)

    # Output
    if args.json:
        print(to_json(result))
    else:
        print_signal(result)

    # Persist
    if not args.no_save:
        save_signal(result)
        logger.info("Signal saved to DB.")


def _history(args: argparse.Namespace) -> None:
    """Print the last N signal records from DB."""
    from src.store.db import load_history
    records = load_history(n=args.history)
    if not records:
        print("No history records found.")
        return
    for rec in records:
        print(
            f"{rec['date']}  {rec['signal']:12s}  score={rec['final_score']:3d}"
            f"  price=${rec['price']:.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QQQ Buy-Signal Monitor with Options Wall Confirmation"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--no-save", action="store_true", help="Skip saving to DB")
    parser.add_argument(
        "--history", type=int, metavar="N",
        help="Print last N signal records and exit"
    )
    args = parser.parse_args()

    if args.history:
        _history(args)
    else:
        _run(args)


if __name__ == "__main__":
    main()
