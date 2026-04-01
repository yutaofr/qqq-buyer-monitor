"""
QQQ Monitor Main Entry Point (v11 Bayesian Convergence).

Only the v11 probabilistic engine is supported. All v10 and legacy logic
has been removed for architecture sanity.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import pandas as pd

from src.models import SignalResult, TargetAllocationState
from src.store.cloud_manager import CloudPersistenceBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger("qqq_monitor")


def _build_v11_signal_result(runtime_result: dict, *, price: float) -> SignalResult:
    """Map conductor runtime output to the unified v11 SignalResult model."""
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

    ordered_probs = sorted(
        runtime_result["probabilities"].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    stable_regime = runtime_result.get("stable_regime", ordered_probs[0][0])
    raw_regime = runtime_result.get("raw_regime", ordered_probs[0][0])
    deployment = runtime_result.get("deployment", {})
    deployment_state = str(deployment.get("deployment_state", "DEPLOY_BASE"))
    deployment_state_key = deployment_state.replace("DEPLOY_", "")
    execution_bucket = str(runtime_result.get("signal", {}).get("target_bucket", "QQQ"))

    explanation = (
        f"v11.5 Bayesian Conductor: beta={runtime_result['target_beta']:.2f}x | "
        f"entropy={runtime_result.get('entropy', 0.0):.3f} | "
        f"stable={stable_regime} | raw={raw_regime} ({ordered_probs[0][1]:.1%}) | "
        f"deploy={deployment_state_key}"
    )

    return SignalResult(
        date=pd.Timestamp(runtime_result["date"]).date(),
        price=float(price),
        target_beta=float(runtime_result["target_beta"]),
        probabilities={k: float(v) for k, v in runtime_result["probabilities"].items()},
        priors={k: float(v) for k, v in runtime_result.get("priors", {}).items()},
        entropy=float(runtime_result.get("entropy", 0.0)),
        stable_regime=str(stable_regime),
        target_allocation=target_allocation,
        logic_trace=[
            {"step": "probabilistic_inference", "result": runtime_result["probabilities"]},
            {"step": "entropy_haircut", "result": {"entropy": runtime_result.get("entropy", 0.0)}},
            {"step": "position_sizing", "result": runtime_result["target_allocation"]},
            {"step": "deployment_policy", "result": deployment},
            {"step": "behavioral_guard", "result": runtime_result["signal"]},
        ],
        explanation=explanation,
        metadata={
            "engine_version": "v11.5",
            "quality_audit": runtime_result.get("quality_audit", {}),
            "feature_values": runtime_result.get("feature_values", {}),
            "prior_details": runtime_result.get("prior_details", {}),
            "deployment_readiness": float(runtime_result.get("deployment_readiness", 0.0)),
            "raw_target_beta": float(runtime_result.get("raw_target_beta", runtime_result["target_beta"])),
            "raw_regime": raw_regime,
            "deployment_state": deployment_state,
            "deployment_state_key": deployment_state_key,
            "execution_bucket": execution_bucket,
            "beta_ceiling": 1.2,
        }
    )


def _build_v11_live_macro_row(
    *,
    observation_date: pd.Timestamp,
    credit_spread: float,
    credit_spread_source: str = "direct",
    net_liquidity: float | None,
    liquidity_roc: float,
    vix: float,
    vix3m: float | None,
    price: float,
    drawdown_pct: float,
    breadth_proxy: float,
    breadth_source: str = "direct",
    breadth_quality_score: float = 1.0,
    fear_greed: float,
    erp_pct_points: float | None,
    real_yield_pct_points: float | None,
    reference_capital: float,
    current_nav: float,
) -> pd.DataFrame:
    observation_ts = pd.Timestamp(observation_date).normalize()
    return pd.DataFrame(
        [
            {
                "observation_date": observation_ts,
                "credit_spread_bps": float(credit_spread),
                "source_credit_spread": str(credit_spread_source),
                "net_liquidity_usd_bn": float(net_liquidity) if net_liquidity is not None else None,
                "liquidity_roc_pct_4w": float(liquidity_roc or 0.0),
                "vix": float(vix),
                "vix3m": None if vix3m is None else float(vix3m),
                "qqq_close": float(price),
                "drawdown_pct": float(drawdown_pct),
                "breadth_proxy": float(breadth_proxy),
                "source_breadth": str(breadth_source),
                "breadth_quality_score": float(breadth_quality_score),
                "fear_greed": float(fear_greed),
                "erp_pct": (float(erp_pct_points) / 100.0) if erp_pct_points is not None else None,
                "real_yield_10y_pct": (float(real_yield_pct_points) / 100.0) if real_yield_pct_points is not None else None,
                "reference_capital": float(reference_capital),
                "current_nav": float(current_nav),
            }
        ]
    )


def _upsert_v11_macro_feedback(raw_row: pd.DataFrame, macro_csv_path: str) -> None:
    """Persist the current v11 macro row into the canonical CSV dataset."""
    path = Path(macro_csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Standardize input row to clean strings for dates
    row = raw_row.iloc[-1].to_dict()
    obs_dt = pd.to_datetime(row["observation_date"]).date().isoformat()
    eff_dt = pd.to_datetime(row.get("effective_date", obs_dt)).date().isoformat()

    if path.exists():
        existing = pd.read_csv(path)
        # Ensure we filter using string comparison on standardized dates
        if "observation_date" in existing.columns:
            existing["observation_date"] = pd.to_datetime(existing["observation_date"]).dt.date.astype(str)
            existing = existing[existing["observation_date"] != obs_dt]
    else:
        existing = pd.DataFrame()

    new_row = row.copy()
    new_row["observation_date"] = obs_dt
    new_row["effective_date"] = eff_dt
    new_row["build_version"] = "v11_live_feedback"

    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(path, index=False)


def run_v11_pipeline(args: argparse.Namespace) -> None:
    """Execute the v11 Bayesian runtime pipeline."""
    from src.collector.breadth import fetch_breadth
    from src.collector.fear_greed import fetch_fear_greed
    from src.collector.fundamentals import fetch_forward_pe
    from src.collector.macro import fetch_credit_spread_snapshot
    from src.collector.macro_v3 import fetch_net_liquidity, fetch_real_yield
    from src.collector.price import fetch_price_data
    from src.collector.vix import fetch_vix_term_structure
    from src.engine.v11.conductor import V11Conductor
    from src.output.cli import print_signal
    from src.output.report import to_json

    cloud = CloudPersistenceBridge()
    sync_files = [
        "data/signals.db",
        "data/macro_historical_dump.csv",
        "data/v11_prior_state.json",
    ]
    if not cloud.pull_state(sync_files):
        raise RuntimeError("Cloud state pull failed; refusing to continue with potentially stale runtime memory.")

    logger.info("Fetching market data…")
    price_data = fetch_price_data()

    try:
        vix_term = fetch_vix_term_structure()
    except Exception as exc:
        logger.warning("VIX fetch failed: %s", exc)
        vix_term = {"vix": 20.0, "vix3m": None}

    try:
        fg = fetch_fear_greed()
    except Exception as exc:
        logger.warning("Fear & Greed fetch failed: %s", exc)
        fg = 50

    try:
        pe_dict = fetch_forward_pe()
        forward_pe = pe_dict.get("forward_pe")
    except Exception as exc:
        logger.warning("Forward PE fetch failed: %s", exc)
        forward_pe = None

    try:
        real_yield_pct = fetch_real_yield()
    except Exception as exc:
        logger.warning("Real Yield fetch failed: %s", exc)
        real_yield_pct = None

    erp_pct = None
    if forward_pe and real_yield_pct is not None:
        erp_pct = (100.0 / forward_pe) - float(real_yield_pct)

    try:
        breadth = fetch_breadth()
        pct_above_50d = float(breadth.get("pct_above_50d", 0.50))
        breadth_source = str(breadth.get("source", "direct"))
        breadth_quality_score = float(breadth.get("quality", 1.0))
    except Exception as exc:
        logger.warning("Breadth fetch failed: %s", exc)
        pct_above_50d = 0.50
        breadth_source = "unavailable:breadth"
        breadth_quality_score = 0.0

    try:
        credit_spread_snapshot = fetch_credit_spread_snapshot()
        credit_spread = credit_spread_snapshot.get("value")
        credit_spread_source = str(credit_spread_snapshot.get("source", "direct"))
        if credit_spread is None:
            credit_spread = 400.0
            credit_spread_source = "default:credit_spread"
    except Exception as exc:
        logger.warning("Credit-spread fetch failed: %s", exc)
        credit_spread = 400.0
        credit_spread_source = "default:credit_spread"

    try:
        net_liq, liq_roc = fetch_net_liquidity()
    except Exception as exc:
        logger.warning("Net-liquidity fetch failed: %s", exc)
        net_liq, liq_roc = None, 0.0

    reference_capital = float(os.environ.get("V11_REFERENCE_CAPITAL", "100000"))
    current_nav = float(os.environ.get("V11_CURRENT_NAV", str(reference_capital)))
    drawdown_pct = float(price_data["price"] / price_data["high_52w"] - 1.0) if price_data["high_52w"] else 0.0

    raw_row = _build_v11_live_macro_row(
        observation_date=pd.Timestamp(price_data["date"]),
        credit_spread=float(credit_spread),
        credit_spread_source=credit_spread_source,
        net_liquidity=net_liq,
        liquidity_roc=liq_roc,
        vix=float(vix_term["vix"]),
        vix3m=vix_term.get("vix3m"),
        price=float(price_data["price"]),
        drawdown_pct=drawdown_pct,
        breadth_proxy=pct_above_50d,
        breadth_source=breadth_source,
        breadth_quality_score=breadth_quality_score,
        fear_greed=float(fg),
        erp_pct_points=erp_pct,
        real_yield_pct_points=real_yield_pct,
        reference_capital=reference_capital,
        current_nav=current_nav,
    )

    runtime = V11Conductor().daily_run(raw_row)
    result = _build_v11_signal_result(runtime, price=float(price_data["price"]))

    # 1. Export Web Snapshot Locally (Production Baseline)
    from src.output.web_exporter import export_web_snapshot
    web_json_path = "src/web/public/status.json"
    export_web_snapshot(result, output_path=web_json_path)

    if args.json:
        print(to_json(result))
    else:
        print_signal(result, use_color=not args.no_color)

    # 2. Notify Discord if explicitly requested
    if args.notify_discord:
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("ALERT_WEBHOOK_URL not set; skipping Discord notification.")
        else:
            from src.output.discord_notifier import send_discord_signal
            ok = send_discord_signal(result, webhook_url)
            if ok:
                logger.info("Discord signal notification sent successfully.")
            else:
                logger.error("Failed to send Discord signal notification.")

    if not args.no_save:
        from src.store.db import save_signal
        save_signal(result)
        _upsert_v11_macro_feedback(raw_row, "data/macro_historical_dump.csv")

        # 3. Synchronize State & Distribution to Cloud
        if cloud.is_ci:
            # Sync core state files
            cloud.push_state(sync_files)
            # Sync Public status.json to the ROOT of the namespace (e.g. prod/status.json)
            with open(web_json_path, "rb") as f:
                cloud.push_payload(f.read(), "status.json", is_binary=True)

        logger.info("v11 signal persisted and cloud state synchronized.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QQQ Monitor Entry Point (v11 Bayesian Convergence)")
    # Deprecated engine param for CLI compatibility, but always forces v11
    parser.add_argument("--engine", choices=["v11"], default="v11", help="Always v11.")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--notify-discord", action="store_true", help="Send signal to Discord")
    parser.add_argument("--no-save", action="store_true", help="Skip saving to DB")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    args = parser.parse_args(argv)

    run_v11_pipeline(args)


if __name__ == "__main__":
    main()
