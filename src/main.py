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
    from src.collector.macro import fetch_credit_spread
    from src.collector.macro_v3 import (
        fetch_real_yield, 
        fetch_fcf_yield, 
        fetch_earnings_revisions_breadth,
        fetch_net_liquidity,
        fetch_move_index
    )
    from src.collector.fundamentals import fetch_forward_pe
    from src.models import MarketData, Signal
    from src.engine.tier1 import calculate_tier1
    from src.engine.tier2 import calculate_tier2
    from src.engine.aggregator import aggregate
    from src.output.cli import print_signal
    from src.output.report import to_json
    from src.utils.stats import calculate_zscore
    from src.store.db import save_signal, get_historical_series, load_latest_macro_state, save_macro_state

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

    # Macro & Fundamentals (v2.0 & v3.0)
    logger.info("Fetching macro & fundamental data…")
    credit_spread = None
    forward_pe = None
    trailing_pe = None
    real_yield = None
    fcf_yield = None
    earnings_revisions_breadth = None
    macro_state = load_latest_macro_state()
    
    try:
        credit_spread = fetch_credit_spread()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Credit spread fetch failed: %s", exc)
        errors.append(f"Macro: {exc}")
        
    try:
        pe_dict = fetch_forward_pe()
        forward_pe = pe_dict.get("forward_pe")
        trailing_pe = pe_dict.get("trailing_pe")
        pe_source = pe_dict.get("source", "yfinance")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fundamentals fetch failed: %s", exc)
        errors.append(f"Fundamentals: {exc}")
        
    try:
        real_yield = fetch_real_yield()
        fcf_yield = fetch_fcf_yield()
        earnings_revisions_breadth = fetch_earnings_revisions_breadth()
    except Exception as exc:  # noqa: BLE001
        logger.warning("v3.0 Macro fetch failed: %s", exc)
        errors.append(f"Macro_v3: {exc}")
        
    # Use cached state if all fetch attempts failed (FRED, yf fallback, etc.)
    if credit_spread is None and macro_state:
        credit_spread = macro_state.get("credit_spread")
        if credit_spread is not None:
            logger.info("Using cached Credit Spread from DB: %.0f bps", credit_spread)
            
    if forward_pe is None and macro_state:
        forward_pe = macro_state.get("trailing_pe")
        if forward_pe is not None:
            logger.info("Using cached Forward PE from DB: %.1f", forward_pe)
            
    if real_yield is None and macro_state:
        real_yield = macro_state.get("real_yield")
        if real_yield is not None:
            logger.info("Using cached Real Yield from DB: %.2f%%", real_yield)
            
    if fcf_yield is None and macro_state:
        fcf_yield = macro_state.get("fcf_yield")
        if fcf_yield is not None:
            logger.info("Using cached FCF Yield from DB: %.2f%%", fcf_yield)
            
    if earnings_revisions_breadth is None and macro_state:
        earnings_revisions_breadth = macro_state.get("earnings_revisions_breadth")
        if earnings_revisions_breadth is not None:
            logger.info("Using cached Earnings Revisions from DB: %.2f%%", earnings_revisions_breadth)
        
    # Phase 2: Net Liquidity & MOVE Index
    net_liq, liq_roc = fetch_net_liquidity()
    move_index = fetch_move_index()
    # History Window (Epic 2) - Increased to 120d for v4.0 Z-scores
    history_window = None
    vix_zscore = 0.0
    dd_zscore = 0.0
    try:
        history_window = get_historical_series(days=120)
        if history_window is not None and not history_window.empty:
            # 1. VIX Z-Score
            vix_zscore = calculate_zscore(vix, history_window["vix"].dropna())
            
            # 2. Drawdown Z-Score
            # Pre-calculate rolling drawdowns in history
            hist_prices = history_window["price"]
            # We need a longer window for historical drawdowns to be meaningful, 
            # but we can use the current high_52w for the latest point.
            # For the historical series, we'll approximate using the window's own peak
            hist_peaks = hist_prices.expanding().max()
            hist_drawdowns = (hist_peaks - hist_prices) / hist_peaks
            current_dd = (price_data["high_52w"] - price_data["price"]) / price_data["high_52w"]
            dd_zscore = calculate_zscore(current_dd, hist_drawdowns)
            
            logger.info("Adaptive Stats: VIX Z-Score = %.2f, DD Z-Score = %.2f", vix_zscore, dd_zscore)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history window for adaptive stats: %s", exc)

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
        ndx_concentration=breadth.get("ndx_concentration", 0.0),
        options_df=options_df,
        credit_spread=credit_spread,
        trailing_pe=trailing_pe,
        forward_pe=forward_pe,
        real_yield=real_yield,
        fcf_yield=fcf_yield,
        earnings_revisions_breadth=earnings_revisions_breadth,
        pe_source=pe_source,
        history_window=history_window,
        vix_zscore=vix_zscore,
        drawdown_zscore=dd_zscore,
        net_liquidity=net_liq,
        liquidity_roc=liq_roc,
        move_index=move_index,
    )

    logger.info("Running signal engines…")
    
    # ── Hysteresis & Notification Muting ─────────────────────────────────────
    from src.store.db import load_history
    try:
        history = load_history(n=5)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history for hysteresis: %s", exc)
        history = []
        
    prev_signal = None
    if history:
        try:
            prev_signal = Signal(history[0]["signal"])
        except ValueError:
            pass

    tier1 = calculate_tier1(market_data)
    tier2 = calculate_tier2(market_data.price, market_data.options_df)
    result = aggregate(
        market_data.date, 
        market_data.price, 
        tier1, 
        tier2, 
        prev_signal=prev_signal,
        credit_spread=market_data.credit_spread,
        forward_pe=market_data.forward_pe,
        real_yield=market_data.real_yield
    )

    consecutive_days = 1
    if history and result.signal.value == history[0]["signal"]:
        for rec in history:
            if rec["signal"] == result.signal.value:
                consecutive_days += 1
            else:
                break
                
    compact_mode = False
    if result.signal == Signal.NO_SIGNAL and consecutive_days >= 3:
        compact_mode = True
    elif result.signal in (Signal.WATCH, Signal.TRIGGERED) and consecutive_days >= 4:
        compact_mode = True

    # Output
    if args.json:
        print(to_json(result))
    else:
        print_signal(
            result, 
            use_color=not args.no_color, 
            compact=compact_mode, 
            consecutive_days=consecutive_days
        )

    # Persist
    if not args.no_save:
        save_signal(result)
        # Update macro state cache
        if market_data.credit_spread is not None or market_data.forward_pe is not None:
            save_macro_state(
                record_date=market_data.date,
                credit_spread=market_data.credit_spread,
                trailing_pe=market_data.forward_pe, # We store it in trailing_pe column since that's what we got
            )
        logger.info("Signal and macro states saved to DB.")


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
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output (useful for Discord/logs)")
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
