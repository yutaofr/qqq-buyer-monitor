"""
QQQ Monitor main entry point.

Usage:
    python -m src.main --engine v10
    python -m src.main --engine v11
    python -m src.main --engine v11 --json
    python -m src.main --history 30
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.models import SignalDetail, SignalResult, Tier1Result, Tier2Result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger("qqq_monitor")


def _neutral_signal_detail(name: str, value: float = 0.0) -> SignalDetail:
    from src.models import SignalDetail

    return SignalDetail(
        name=name,
        value=float(value),
        points=0,
        thresholds=(0.0, 0.0),
        triggered_half=False,
        triggered_full=False,
    )


def _build_neutral_v11_surface() -> tuple[Tier1Result, Tier2Result]:
    from src.models import OptionsOverlay, Tier1Result, Tier2Result

    detail = _neutral_signal_detail
    tier1 = Tier1Result(
        score=0,
        drawdown_52w=detail("drawdown_52w"),
        ma200_deviation=detail("ma200_deviation"),
        vix=detail("vix"),
        fear_greed=detail("fear_greed"),
        breadth=detail("breadth"),
    )
    tier2 = Tier2Result(
        adjustment=0,
        put_wall=None,
        call_wall=None,
        gamma_flip=None,
        support_confirmed=False,
        support_broken=False,
        upside_open=False,
        gamma_positive=False,
        gamma_source="v11",
        put_wall_distance_pct=None,
        call_wall_distance_pct=None,
        overlay=OptionsOverlay(),
    )
    return tier1, tier2


def _build_v11_signal_result(runtime_result: dict, *, price: float) -> SignalResult:
    from src.models import AllocationState, Signal, SignalResult, TargetAllocationState

    tier1, tier2 = _build_neutral_v11_surface()

    bucket = runtime_result["signal"].get("target_bucket", "QQQ")
    signal_map = {
        "QLD": Signal.TRIGGERED,
        "QQQ": Signal.WATCH,
        "CASH": Signal.NO_SIGNAL,
    }
    allocation_map = {
        "QLD": AllocationState.FAST_ACCUMULATE,
        "QQQ": AllocationState.BASE_DCA,
        "CASH": AllocationState.RISK_CONTAINMENT,
    }

    allocation = runtime_result["target_allocation"]
    nav = max(
        1.0,
        float(allocation["qqq_dollars"] + allocation["qld_notional_dollars"] + allocation["cash_dollars"]),
    )
    target_allocation = TargetAllocationState(
        target_cash_pct=float(allocation["cash_dollars"] / nav),
        target_qqq_pct=float(allocation["qqq_dollars"] / nav),
        target_qld_pct=float(allocation["qld_notional_dollars"] / nav),
        target_beta=float(runtime_result["target_beta"]),
    )
    quality_audit = runtime_result.get("quality_audit", {})
    data_quality = quality_audit.get("field_status", {})
    ordered_probs = sorted(
        runtime_result["probabilities"].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    explanation = (
        f"v11 probabilistic runtime：target_beta={runtime_result['target_beta']:.2f}x | "
        f"entropy={runtime_result.get('entropy', 0.0):.3f} | "
        f"execution={runtime_result['signal'].get('target_bucket', 'n/a')} | "
        f"top_posterior={ordered_probs[0][0]}={ordered_probs[0][1]:.2%}"
    )

    top_regime = ordered_probs[0][0]

    return SignalResult(
        date=runtime_result["date"],
        price=float(price),
        signal=signal_map.get(bucket, Signal.WATCH),
        final_score=int(round(float(runtime_result["target_beta"]) * 100)),
        tier1=tier1,
        tier2=tier2,
        explanation=explanation,
        allocation_state=allocation_map.get(bucket, AllocationState.BASE_DCA),
        data_quality=data_quality,
        logic_trace=[
            {"step": "degradation", "decision": quality_audit},
            {"step": "posterior", "decision": runtime_result["probabilities"]},
            {
                "step": "position_sizer",
                "decision": {
                    **runtime_result["target_allocation"],
                    "target_beta": runtime_result["target_beta"],
                    "raw_target_beta": runtime_result["raw_target_beta"],
                },
            },
            {"step": "behavior_guard", "decision": runtime_result["signal"]},
        ],
        target_allocation=target_allocation,
        raw_target_beta=float(runtime_result["raw_target_beta"]),
        target_beta=float(runtime_result["target_beta"]),
        should_adjust=bool(runtime_result["signal"].get("action_required", False)),
        rebalance_action=dict(runtime_result["signal"]),
        tier0_regime=top_regime,
        cycle_regime=top_regime,
        engine_version="v11",
        v11_probabilities={k: float(v) for k, v in runtime_result["probabilities"].items()},
        v11_entropy=float(runtime_result.get("entropy", 0.0)),
        v11_execution=dict(runtime_result["signal"]),
        v11_quality_audit=quality_audit,
        feature_values=dict(runtime_result.get("feature_values", {})),
    )


def run_v11_pipeline(args: argparse.Namespace) -> None:
    """Execute the v11 probabilistic runtime pipeline."""
    import os

    from src.collector.breadth import fetch_breadth
    from src.collector.fear_greed import fetch_fear_greed
    from src.collector.fundamentals import fetch_forward_pe
    from src.collector.macro import fetch_credit_spread
    from src.collector.macro_v3 import fetch_net_liquidity, fetch_real_yield
    from src.collector.price import fetch_price_data
    from src.collector.vix import fetch_vix_term_structure
    from src.engine.v11.conductor import V11Conductor
    from src.output.cli import print_signal
    from src.output.report import to_json
    from src.store.db import save_signal

    logger.info("Fetching v11 market data…")
    price_data = fetch_price_data()

    try:
        vix_term = fetch_vix_term_structure()
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX term-structure fetch failed: %s", exc)
        vix_term = {"vix": 20.0, "vix3m": None}

    try:
        fg = fetch_fear_greed()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fear & Greed fetch failed for v11: %s", exc)
        fg = 50

    try:
        pe_dict = fetch_forward_pe()
        forward_pe = pe_dict.get("forward_pe")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Forward PE fetch failed for v11: %s", exc)
        forward_pe = None

    try:
        real_yield = fetch_real_yield()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Real Yield fetch failed for v11: %s", exc)
        real_yield = None

    erp = None
    if forward_pe and real_yield:
        erp = (100.0 / forward_pe) - real_yield

    try:
        breadth = fetch_breadth()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Breadth fetch failed for v11: %s", exc)
        breadth = {"pct_above_50d": 0.50}

    try:
        credit_spread = fetch_credit_spread()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Credit-spread fetch failed for v11: %s", exc)
        credit_spread = 400.0

    try:
        net_liq, liquidity_roc = fetch_net_liquidity()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Net-liquidity fetch failed for v11: %s", exc)
        net_liq, liquidity_roc = None, 0.0

    reference_capital = float(os.environ.get("V11_REFERENCE_CAPITAL", "100000"))
    current_nav = float(os.environ.get("V11_CURRENT_NAV", str(reference_capital)))
    drawdown_pct = float(price_data["price"] / price_data["high_52w"] - 1.0) if price_data["high_52w"] else 0.0

    raw_row = pd.DataFrame(
        [
            {
                "observation_date": pd.Timestamp(price_data["date"]),
                "credit_spread_bps": float(credit_spread),
                "net_liquidity": float(net_liq) if net_liq is not None else None,
                "liquidity_roc_pct_4w": float(liquidity_roc or 0.0),
                "vix": float(vix_term["vix"]),
                "vix3m": None if vix_term.get("vix3m") is None else float(vix_term["vix3m"]),
                "qqq_close": float(price_data["price"]),
                "drawdown_pct": drawdown_pct,
                "breadth_proxy": float(breadth.get("pct_above_50d", 0.50)),
                "fear_greed": float(fg),
                "erp": float(erp) if erp is not None else None,
                "reference_capital": reference_capital,
                "current_nav": current_nav,
            }
        ]
    )

    runtime = V11Conductor().daily_run(raw_row)
    result = _build_v11_signal_result(runtime, price=float(price_data["price"]))

    if args.json:
        print(to_json(result))
    else:
        print_signal(result, use_color=not args.no_color)

    # ── Export & Notify (Atomic) ──────────────────────────────────────────────
    if getattr(args, "export_web", False) or os.environ.get("EXPORT_WEB") == "1":
        from src.output.web_exporter import export_feature_library_to_blob, export_web_snapshot
        logger.info("Exporting v11 web snapshot and syncing feature library to cloud...")
        export_web_snapshot(result)
        # Persistent cloud sync for V11 memory parity across CI runs
        export_feature_library_to_blob()

    if getattr(args, "notify_discord", False):
        from src.output.discord_notifier import send_discord_signal
        webhook_url = getattr(args, "discord_webhook", None) or os.environ.get("ALERT_WEBHOOK_URL")
        if webhook_url:
            logger.info("Sending v11 Discord notification...")
            send_discord_signal(result, webhook_url)

    if not args.no_save:
        save_signal(result)
        logger.info("v11 signal successfully persisted to local DB.")


def _history(args: argparse.Namespace) -> None:
    """Print the last N historical signal records."""
    from src.models import AllocationState
    from src.output.cli import _allocation_label
    from src.store.db import load_history

    n = args.history or 10
    history = load_history(n=n)

    if not history:
        print("No historical records found.")
        return

    print(f"Showing last {len(history)} records:")
    for rec in history:
        date_str = rec.get("date", "unknown")
        price = rec.get("price", 0.0)
        state_val = rec.get("allocation_state", "BASE_DCA")
        score = rec.get("final_score", 0)

        try:
            state = AllocationState(state_val)
            action = _allocation_label(state)
        except ValueError:
            action = "未知状态"

        print(f"[{date_str}] price=${price:,.2f} score={score} allocation={state_val} action={action}")


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the full signal pipeline."""
    from src.collector.breadth import fetch_breadth
    from src.collector.fear_greed import fetch_fear_greed
    from src.collector.fundamentals import fetch_forward_pe
    from src.collector.macro import fetch_credit_spread
    from src.collector.macro_v3 import (
        fetch_credit_acceleration,
        fetch_earnings_revisions_breadth,
        fetch_fcf_yield,
        fetch_funding_stress,
        fetch_move_index,
        fetch_net_liquidity,
        fetch_real_yield,
        fetch_sector_rotation,
        fetch_short_volume_proxy,
    )
    from src.collector.options import fetch_options_chain
    from src.collector.price import fetch_price_data
    from src.collector.vix import fetch_vix
    from src.engine.aggregator import aggregate
    from src.engine.data_quality import build_data_quality
    from src.engine.tier1 import calculate_tier1
    from src.engine.tier2 import calculate_tier2
    from src.models import MarketData, Signal
    from src.output.cli import (
        build_runtime_logic_trace,
        build_v8_explanation,
        is_v8_runtime_result,
        print_signal,
    )
    from src.output.interpreter import NarrativeEngine
    from src.output.report import to_json
    from src.store.db import (
        get_historical_series,
        load_latest_macro_state,
        save_macro_state,
        save_signal,
    )
    from src.utils.stats import calculate_zscore

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
        options_df = fetch_options_chain(spot_price=price_data["price"])
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
    pe_source = "unknown"
    macro_state = load_latest_macro_state()
    data_quality_meta: dict[str, dict[str, int | str]] = {}

    cache_stale_days = 0
    if macro_state and macro_state.get("date"):
        try:
            cache_stale_days = max(
                (price_data["date"] - date.fromisoformat(str(macro_state["date"]))).days,
                0,
            )
        except (TypeError, ValueError):
            cache_stale_days = 0

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

    # Use cached state if all fetch attempts failed
    if credit_spread is None and macro_state and macro_state.get("credit_spread") is not None:
        credit_spread = macro_state.get("credit_spread")
        data_quality_meta["credit_spread"] = {"source": "cache:macro_state", "stale_days": cache_stale_days}

    if forward_pe is None and macro_state and macro_state.get("forward_pe") is not None:
        forward_pe = macro_state.get("forward_pe")
        data_quality_meta["forward_pe"] = {"source": "cache:macro_state", "stale_days": cache_stale_days}

    if real_yield is None and macro_state and macro_state.get("real_yield") is not None:
        real_yield = macro_state.get("real_yield")
        data_quality_meta["real_yield"] = {"source": "cache:macro_state", "stale_days": cache_stale_days}

    if fcf_yield is None and macro_state and macro_state.get("fcf_yield") is not None:
        fcf_yield = macro_state.get("fcf_yield")
        data_quality_meta["fcf_yield"] = {"source": "cache:macro_state", "stale_days": cache_stale_days}

    if earnings_revisions_breadth is None and macro_state and macro_state.get("earnings_revisions_breadth") is not None:
        earnings_revisions_breadth = macro_state.get("earnings_revisions_breadth")
        data_quality_meta["earnings_revisions_breadth"] = {"source": "cache:macro_state", "stale_days": cache_stale_days}

    # Phase 2: Net Liquidity & MOVE Index
    net_liq, liq_roc = fetch_net_liquidity()
    move_index = fetch_move_index()

    # v6.2 Defensive Confirmation (New)
    credit_accel = fetch_credit_acceleration()
    funding_stress = fetch_funding_stress()

    # Phase 3: Sector Rotation
    sector_rotation = None
    try:
        sector_rotation = fetch_sector_rotation()
    except Exception as exc:
        logger.warning("Sector rotation fetch failed: %s", exc)

    # v5.0 Short Volume Proxy
    short_vol_ratio = None
    try:
        short_vol_ratio = fetch_short_volume_proxy()
    except Exception as exc:
        logger.warning("Short volume proxy fetch failed: %s", exc)

    # History Window (Epic 2)
    history_window = None
    vix_zscore = 0.0
    dd_zscore = 0.0
    try:
        history_window = get_historical_series(days=120)
        if history_window is not None and not history_window.empty:
            vix_zscore = calculate_zscore(vix, history_window["vix"].dropna())
            hist_prices = history_window["price"]
            hist_peaks = hist_prices.expanding().max()
            hist_drawdowns = (hist_peaks - hist_prices) / hist_peaks
            current_dd = (price_data["high_52w"] - price_data["price"]) / price_data["high_52w"]
            dd_zscore = calculate_zscore(current_dd, hist_drawdowns)
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
        ohlcv_history=price_data.get("history"),
        sector_rotation=sector_rotation,
        days_since_52w_high=price_data.get("days_since_high"),
        short_vol_ratio=short_vol_ratio
    )

    logger.info("Running signal engines…")

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
    tier2 = calculate_tier2(market_data.price, market_data.options_df, ohlcv_history=market_data.ohlcv_history)

    result = aggregate(
        market_data.date,
        market_data.price,
        tier1,
        tier2,
        prev_signal=prev_signal,
        credit_spread=market_data.credit_spread,
        forward_pe=market_data.forward_pe,
        real_yield=market_data.real_yield,
        ma50=getattr(market_data, 'history_window', pd.DataFrame()).get('ma50', pd.Series()).iloc[-1] if market_data.history_window is not None and 'ma50' in market_data.history_window else None,
        credit_accel=credit_accel,
        liquidity_roc=liq_roc,
        is_funding_stressed=funding_stress.get("is_stressed", False),
        historical_ohlcv=price_data.get("history")
    )
    result.data_quality = build_data_quality(market_data, feature_meta=data_quality_meta)

    # ── v9.0 target-beta-first pipeline ───────────────────────────────────────
    import os

    from src.engine.allocation_search import select_candidate_with_floor_fallback_v8
    from src.engine.candidate_registry import load_registry, select_runtime_candidates
    from src.engine.cycle_factor import decide_cycle_state
    from src.engine.deployment_controller import decide_deployment_state
    from src.engine.execution_policy import (
        beta_requires_qld_above_ceiling,
        build_advisory_rebalance_decision,
        build_advisory_state_from_history,
        build_beta_recommendation,
        target_allocation_from_beta,
    )
    from src.engine.feature_pipeline import build_feature_snapshot
    from src.engine.risk_controller import decide_risk_state
    from src.engine.runtime_selector import RuntimeSelection
    from src.engine.tier0_macro import assess_structural_regime
    from src.store.db import load_runtime_inputs, save_runtime_inputs

    v7_registry_path = os.environ.get("V7_REGISTRY_PATH", "data/candidate_registry_v7.json")
    runtime_inputs = load_runtime_inputs(record_date=market_data.date) or {}

    rolling_drawdown = None
    try:
        if runtime_inputs.get("rolling_drawdown") is not None:
            rolling_drawdown = float(runtime_inputs["rolling_drawdown"])
        elif os.environ.get("ROLLING_DRAWDOWN") is not None:
            rolling_drawdown = float(os.environ.get("ROLLING_DRAWDOWN"))
        elif os.environ.get("PORTFOLIO_ROLLING_DRAWDOWN") is not None:
            rolling_drawdown = float(os.environ.get("PORTFOLIO_ROLLING_DRAWDOWN"))
    except (TypeError, ValueError):
        pass

    try:
        if runtime_inputs.get("available_new_cash") is not None:
            available_new_cash = max(0.0, float(runtime_inputs["available_new_cash"]))
        else:
            available_new_cash = max(0.0, float(os.environ.get("AVAILABLE_NEW_CASH", "0.0")))
    except (TypeError, ValueError):
        available_new_cash = 0.0

    five_day_return = 0.0
    twenty_day_return = 0.0
    if market_data.ohlcv_history is not None and "Close" in market_data.ohlcv_history:
        close_history = market_data.ohlcv_history["Close"].dropna().astype(float)
        if not close_history.empty:
            five_day_return = float(close_history.pct_change(5).fillna(0.0).iloc[-1])
            twenty_day_return = float(close_history.pct_change(20).fillna(0.0).iloc[-1])
    near_volume_poc = False
    if tier2.poc is not None and market_data.price > 0:
        near_volume_poc = abs(market_data.price - tier2.poc) / market_data.price <= 0.02

    try:
        erp_value = None
        if (
            market_data.forward_pe
            and market_data.real_yield is not None
            and market_data.forward_pe > 0
        ):
            erp_value = (1.0 / market_data.forward_pe) * 100.0 - market_data.real_yield

        price_vs_ma200 = None
        if market_data.ma200:
            price_vs_ma200 = (market_data.price - market_data.ma200) / market_data.ma200

        # Build unified feature snapshot from collected data
        v7_snapshot = build_feature_snapshot(
            market_date=market_data.date,
            raw_values={
                "credit_spread": market_data.credit_spread,
                "credit_acceleration": credit_accel,
                "net_liquidity": market_data.net_liquidity,
                "liquidity_roc": market_data.liquidity_roc,
                "real_yield": market_data.real_yield,
                "erp": erp_value,
                "funding_stress": funding_stress.get("is_stressed", False) if isinstance(funding_stress, dict) else funding_stress,
                "close": market_data.price,
                "price_vs_ma200": price_vs_ma200,
                "vix": market_data.vix,
                "breadth": market_data.pct_above_50d,
                "fear_greed": market_data.fear_greed,
                "tactical_stress_score": tier1.stress_score,
                "capitulation_score": tier1.capitulation_score,
                "rolling_drawdown": rolling_drawdown,
                "five_day_return": five_day_return,
                "twenty_day_return": twenty_day_return,
                "persistence_score": tier1.persistence_score,
                "sector_rotation": market_data.sector_rotation,
                "price_vix_divergence": tier1.divergence_flags.get("price_vix", False),
                "price_mfi_divergence": tier1.divergence_flags.get("price_mfi", False),
                "short_squeeze_potential": tier1.divergence_flags.get("short_squeeze_potential", False),
                "bond_vol_spike": tier1.divergence_flags.get("bond_vol_spike", False),
                "near_volume_poc": near_volume_poc,
            },
            raw_quality=data_quality_meta,
        )

        tier0_regime = assess_structural_regime(
            credit_spread=market_data.credit_spread,
            erp=erp_value,
        )
        cycle_decision = decide_cycle_state(v7_snapshot)

        v7_risk = decide_risk_state(
            v7_snapshot,
            rolling_drawdown=rolling_drawdown,
            tier0_regime=tier0_regime,
            cycle_decision=cycle_decision,
            drawdown_budget=0.30,
        )

        # Deployment Controller (Class B + Tier-0 soft ceiling)
        v7_deploy = decide_deployment_state(
            v7_snapshot,
            v7_risk,
            tier0_regime=tier0_regime,
            available_new_cash=available_new_cash,
        )

        # Load the certified candidate registry
        registry = load_registry(v7_registry_path)
        candidates = select_runtime_candidates(registry, v7_risk.risk_state)

        # Previous risk state from DB history for state-change trigger
        prev_risk_str = history[0].get("risk_state") if history else None
        from src.models.risk import RiskState as _RS

        prev_risk = _RS(prev_risk_str) if prev_risk_str else None

        result.risk_state = v7_risk.risk_state
        result.deployment_state = v7_deploy.deployment_state
        result.cycle_regime = cycle_decision.cycle_regime.value
        result.registry_version = registry.registry_version
        result.tier0_regime = tier0_regime
        result.tier0_applied = v7_risk.tier0_applied
        result.target_exposure_ceiling = v7_risk.target_exposure_ceiling
        result.target_cash_floor = v7_risk.target_cash_floor
        result.qld_share_ceiling = v7_risk.qld_share_ceiling

        # Runtime evidence tracing for the v9.0 surface
        result.cycle_reasons = list(cycle_decision.reasons)
        result.risk_reasons = list(v7_risk.reasons)
        result.deployment_reasons = list(v7_deploy.reasons)
        result.feature_values = {**v7_snapshot.values}
        if erp_value is not None:
            result.feature_values["erp"] = float(erp_value)

        selected_candidate, used_floor_fallback = select_candidate_with_floor_fallback_v8(
            scoped_candidates=candidates,
            registry_candidates=list(registry.candidates),
            max_beta_ceiling=v7_risk.target_exposure_ceiling,
            qld_share_ceiling=v7_risk.qld_share_ceiling,
            max_drawdown_budget=registry.drawdown_budget,
        )

        audit: list[dict] = []
        for candidate in candidates:
            if candidate.target_effective_exposure > v7_risk.target_exposure_ceiling + 1e-9:
                audit.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "exceeds_beta_ceiling",
                    "exposure": candidate.target_effective_exposure,
                    "ceiling": v7_risk.target_exposure_ceiling,
                })
            elif candidate.qld_pct > v7_risk.qld_share_ceiling + 1e-9:
                audit.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "exceeds_qld_share_ceiling",
                    "qld_pct": candidate.qld_pct,
                    "ceiling": v7_risk.qld_share_ceiling,
                })
            elif candidate.research_metrics.get("max_drawdown", 1.0) > registry.drawdown_budget:
                audit.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "exceeds_drawdown_budget",
                    "max_drawdown": candidate.research_metrics.get("max_drawdown"),
                    "budget": registry.drawdown_budget,
                })
            elif selected_candidate is not None and candidate.candidate_id != selected_candidate.candidate_id:
                audit.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "lower_rank",
                })

        if used_floor_fallback and selected_candidate is not None:
            audit.append({
                "candidate_id": selected_candidate.candidate_id,
                "reason": "global_beta_floor_fallback",
                "beta_floor": 0.50,
                "risk_state": v7_risk.risk_state.value,
            })

        if selected_candidate is not None:
            selection = RuntimeSelection(
                selected_candidate=selected_candidate,
                rejected_candidates=tuple(audit),
                selection_score=0.0,
            )
            beta_rec = build_beta_recommendation(
                selection=selection,
                risk_decision=v7_risk,
                previous_risk_state=prev_risk,
            )
            advisory_state = build_advisory_state_from_history(
                history=history,
                current_raw_target_beta=beta_rec.target_beta,
                fallback_beta=beta_rec.target_beta,
            )
            hard_constraint_override = (
                advisory_state.assumed_beta > v7_risk.target_exposure_ceiling + 1e-9
                or beta_requires_qld_above_ceiling(
                    advisory_state.assumed_beta,
                    qld_share_ceiling=v7_risk.qld_share_ceiling,
                )
            )
            emergency_override = tier0_regime == "CRISIS" or cycle_decision.cycle_regime.value == "CAPITULATION" or (
                rolling_drawdown is not None and rolling_drawdown >= 0.30
            ) or hard_constraint_override
            advisory_decision = build_advisory_rebalance_decision(
                raw_recommendation=beta_rec,
                advisory_state=advisory_state,
                as_of_date=market_data.date,
                emergency_override=emergency_override,
            )
            result.selected_candidate_id = selected_candidate.candidate_id
            result.raw_target_beta = beta_rec.target_beta
            result.target_beta = advisory_decision.advised_target_beta
            result.assumed_beta_before = advisory_decision.assumed_beta_before
            result.assumed_beta_after = advisory_decision.assumed_beta_after
            result.friction_blockers = list(advisory_decision.friction_blockers)
            result.estimated_turnover = advisory_decision.estimated_turnover
            result.estimated_cost_drag = advisory_decision.estimated_cost_drag
            result.should_adjust = advisory_decision.should_adjust
            result.target_allocation = target_allocation_from_beta(
                advisory_decision.advised_target_beta,
                qld_share_ceiling=v7_risk.qld_share_ceiling,
            )
            primary_reason = v7_deploy.reasons[0] if v7_deploy.reasons else {}
            blood_chip_reason = next(
                (
                    reason
                    for reason in v7_deploy.reasons
                    if reason.get("rule") == "blood_chip_crisis_override"
                ),
                primary_reason,
            )
            result.rebalance_action = {
                "should_adjust": advisory_decision.should_adjust,
                "should_rebalance": advisory_decision.should_adjust,
                "reason": advisory_decision.adjustment_reason,
                "raw_target_beta": advisory_decision.raw_target_beta,
                "advised_target_beta": advisory_decision.advised_target_beta,
                "assumed_beta_before": advisory_decision.assumed_beta_before,
                "assumed_beta_after": advisory_decision.assumed_beta_after,
                "friction_blockers": list(advisory_decision.friction_blockers),
            }
            result.deployment_action = {
                "deploy_mode": v7_deploy.deployment_state.value.replace("DEPLOY_", ""),
                "reason": primary_reason.get("rule", "controller_decision"),
                "blood_chip_override_active": blood_chip_reason.get("rule") == "blood_chip_crisis_override",
                "path": blood_chip_reason.get("path"),
            }
            result.logic_trace = build_runtime_logic_trace(result)
            logger.info(
                "v10.0 ▶ tier0=%s cycle=%s risk=%s deploy=%s candidate=%s raw_beta=%.2f advised_beta=%.2f adjust=%s",
                tier0_regime,
                cycle_decision.cycle_regime.value,
                v7_risk.risk_state.value,
                v7_deploy.deployment_state.value,
                selected_candidate.candidate_id,
                beta_rec.target_beta,
                advisory_decision.advised_target_beta,
                advisory_decision.should_adjust,
            )
        else:
            raise ValueError(
                "No compliant runtime candidate found and no global 0.5 beta floor candidate is available. "
                "Check candidate_registry_v7.json."
            )

        result.candidate_selection_audit = audit

    except FileNotFoundError:
        # Registry missing → explicit degraded mode, no silent fallback (SRD §5.3)
        result.logic_trace.append({"rule": "registry_missing", "v7_registry_path": v7_registry_path})
        logger.warning("v9.0 registry not found at '%s' — running in degraded mode (legacy allocation only)", v7_registry_path)
    except (ValueError, KeyError) as exc:
        result.logic_trace.append({"rule": "v7_pipeline_error", "error": str(exc)})
        logger.warning("v9.0 pipeline error (non-fatal, legacy allocation remains available): %s", exc)
    # ── end v9.0 ──────────────────────────────────────────────────────────────

    # v6.2 Narrative Guardrail for legacy output; v8 uses a dedicated recommendation-only summary.
    interpreter = NarrativeEngine()
    v8_runtime = is_v8_runtime_result(result)
    if v8_runtime:
        result.explanation = build_v8_explanation(result)
    else:
        result.explanation = interpreter.format_explanation(result.explanation, result.allocation_state)

    consecutive_days = 1
    current_allocation_state = result.allocation_state.value
    if history:
        def _record_allocation_state(record: dict) -> str | None:
            return record.get("allocation_state") or record.get("signal")

        if _record_allocation_state(history[0]) == current_allocation_state:
            for rec in history:
                if _record_allocation_state(rec) == current_allocation_state:
                    consecutive_days += 1
                else:
                    break

    compact_mode = False
    if result.allocation_state in (
        result.allocation_state.__class__.BASE_DCA,
        result.allocation_state.__class__.PAUSE_CHASING,
        result.allocation_state.__class__.RISK_CONTAINMENT,
        result.allocation_state.__class__.WATCH_DEFENSE,
    ) and consecutive_days >= 3:
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
        if not v8_runtime:
            try:
                interpreter.print_narrative(result.logic_trace)
                interpreter.print_decision_tree(result.logic_trace)
            except Exception as exc:
                logger.warning("Narrative interpreter failed: %s", exc)

    # Signal and macro persistence is now handled inside run_v11_pipeline
    # to avoid duplication and ensure cloud-sync parity.
    pass


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QQQ Buy-Signal Monitor (v11.0 probabilistic)")
    parser.add_argument(
        "--engine",
        choices=["v10", "v11"],
        default="v11",
        help="Runtime engine to execute (default: v11).",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--export-web", action="store_true", help="Export discretized snapshot for Web dashboard")
    parser.add_argument("--notify-discord", action="store_true", help="Send signal to Discord")
    parser.add_argument("--discord-webhook", type=str, help="Override Discord webhook URL")
    parser.add_argument("--no-save", action="store_true", help="Skip saving to DB")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("--history", type=int, metavar="N", help="Print last N signal records and exit")
    args = parser.parse_args(argv)

    if args.history:
        _history(args)
    elif args.engine == "v11":
        run_v11_pipeline(args)
    else:
        run_pipeline(args)


if __name__ == "__main__":
    main()
