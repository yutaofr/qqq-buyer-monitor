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


def _is_degraded_source(source: str | None) -> bool:
    source_str = str(source or "")
    return source_str.startswith(("proxy:", "fallback:", "synthetic:", "default:", "unavailable:"))


def _compose_derived_source(metric_name: str, *upstream_sources: str | None) -> str:
    normalized = [str(source or "unavailable:unknown") for source in upstream_sources]
    if any(source.startswith("unavailable:") for source in normalized):
        return f"unavailable:{metric_name}"
    if any(_is_degraded_source(source) for source in normalized):
        return f"proxy:derived:{metric_name}[{'|'.join(normalized)}]"
    return f"derived:{metric_name}[{'|'.join(normalized)}]"


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
        f"v12.0 Orthogonal Bayesian Conductor: beta={runtime_result['target_beta']:.2f}x | "
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
            "engine_version": "v12.0",
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


def _build_v12_live_macro_row(
    *,
    observation_date: pd.Timestamp,
    effective_date: pd.Timestamp | None = None,
    build_version: str,
    credit_spread: float,
    credit_spread_source: str = "direct",
    real_yield_pct_points: float | None,
    real_yield_source: str = "direct",
    net_liquidity: float | None,
    net_liquidity_source: str = "direct",
    treasury_vol: float | None,
    treasury_vol_source: str = "direct",
    copper_gold_ratio: float | None,
    copper_gold_source: str = "direct",
    breakeven_pct_points: float | None,
    breakeven_source: str = "direct",
    core_capex: float | None,
    core_capex_source: str = "direct",
    usdjpy: float | None,
    usdjpy_source: str = "direct",
    erp_ttm_pct_points: float | None,
    erp_ttm_source: str = "direct",
    reference_capital: float,
    current_nav: float,
) -> pd.DataFrame:
    observation_ts = pd.Timestamp(observation_date).normalize()
    effective_ts = pd.Timestamp(effective_date or observation_ts).normalize()
    return pd.DataFrame(
        [
            {
                "observation_date": observation_ts,
                "effective_date": effective_ts,
                "build_version": str(build_version),
                "credit_spread_bps": float(credit_spread),
                "source_credit_spread": str(credit_spread_source),
                "real_yield_10y_pct": (float(real_yield_pct_points) / 100.0) if real_yield_pct_points is not None else None,
                "source_real_yield": str(real_yield_source),
                "net_liquidity_usd_bn": float(net_liquidity) if net_liquidity is not None else None,
                "source_net_liquidity": str(net_liquidity_source),
                "treasury_vol_21d": float(treasury_vol) if treasury_vol is not None else None,
                "source_treasury_vol": str(treasury_vol_source),
                "copper_gold_ratio": float(copper_gold_ratio) if copper_gold_ratio is not None else None,
                "source_copper_gold": str(copper_gold_source),
                "breakeven_10y": (float(breakeven_pct_points) / 100.0) if breakeven_pct_points is not None else None,
                "source_breakeven": str(breakeven_source),
                "core_capex_mm": float(core_capex) if core_capex is not None else None,
                "source_core_capex": str(core_capex_source),
                "usdjpy": float(usdjpy) if usdjpy is not None else None,
                "source_usdjpy": str(usdjpy_source),
                "erp_ttm_pct": (float(erp_ttm_pct_points) / 100.0) if erp_ttm_pct_points is not None else None,
                "source_erp_ttm": str(erp_ttm_source),
                "forward_pe": None,
                "erp_pct": None,
                "source_forward_pe": "deprecated:v12",
                "source_erp": "deprecated:v12",
                "funding_stress_flag": int(float(credit_spread) >= 500.0),
                "reference_capital": float(reference_capital),
                "current_nav": float(current_nav),
            }
        ]
    )


def _build_v11_live_macro_row(**kwargs) -> pd.DataFrame:
    return _build_v12_live_macro_row(**kwargs)


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
    new_row["build_version"] = str(new_row.get("build_version", "v12_live_feedback"))

    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(path, index=False)


def run_v11_pipeline(args: argparse.Namespace) -> None:
    """Execute the v11 Bayesian runtime pipeline."""
    from src.collector.global_macro import (
        fetch_breakeven_inflation,
        fetch_copper_gold_ratio,
        fetch_core_capex_momentum,
        fetch_shiller_ttm_eps,
        fetch_treasury_realized_vol,
        fetch_usdjpy_snapshot,
    )
    from src.collector.macro import fetch_credit_spread_snapshot
    from src.collector.macro_v3 import fetch_net_liquidity_snapshot, fetch_real_yield_snapshot
    from src.collector.price import fetch_price_data
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
        real_yield_snapshot = fetch_real_yield_snapshot()
        real_yield_pct = real_yield_snapshot.get("value")
        real_yield_source = str(real_yield_snapshot.get("source", "unavailable:real_yield"))
    except Exception as exc:
        logger.warning("Real Yield fetch failed: %s", exc)
        real_yield_pct = None
        real_yield_source = "unavailable:real_yield"

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
        net_liquidity_snapshot = fetch_net_liquidity_snapshot()
        net_liq = net_liquidity_snapshot.get("value")
        net_liquidity_source = str(net_liquidity_snapshot.get("source", "unavailable:net_liquidity"))
    except Exception as exc:
        logger.warning("Net-liquidity fetch failed: %s", exc)
        net_liq = None
        net_liquidity_source = "unavailable:net_liquidity"

    try:
        treasury_vol_snapshot = fetch_treasury_realized_vol()
        treasury_vol = treasury_vol_snapshot.get("value")
        treasury_vol_source = str(treasury_vol_snapshot.get("source", "unavailable:treasury_vol"))
    except Exception as exc:
        logger.warning("Treasury vol fetch failed: %s", exc)
        treasury_vol = None
        treasury_vol_source = "unavailable:treasury_vol"

    try:
        copper_gold_snapshot = fetch_copper_gold_ratio()
        copper_gold_ratio = copper_gold_snapshot.get("ratio")
        copper_gold_source = str(copper_gold_snapshot.get("source", "unavailable:copper_gold"))
    except Exception as exc:
        logger.warning("Copper/gold fetch failed: %s", exc)
        copper_gold_ratio = None
        copper_gold_source = "unavailable:copper_gold"

    try:
        breakeven_snapshot = fetch_breakeven_inflation()
        breakeven = breakeven_snapshot.get("value")
        breakeven_source = str(breakeven_snapshot.get("source", "unavailable:breakeven"))
    except Exception as exc:
        logger.warning("Breakeven fetch failed: %s", exc)
        breakeven = None
        breakeven_source = "unavailable:breakeven"

    try:
        capex_snapshot = fetch_core_capex_momentum()
        core_capex = capex_snapshot.get("delta")
        core_capex_source = str(capex_snapshot.get("source", "unavailable:core_capex"))
    except Exception as exc:
        logger.warning("Core capex fetch failed: %s", exc)
        core_capex = None
        core_capex_source = "unavailable:core_capex"

    try:
        usdjpy_snapshot = fetch_usdjpy_snapshot()
        usdjpy = usdjpy_snapshot.get("value")
        usdjpy_source = str(usdjpy_snapshot.get("source", "unavailable:usdjpy"))
    except Exception as exc:
        logger.warning("USDJPY fetch failed: %s", exc)
        usdjpy = None
        usdjpy_source = "unavailable:usdjpy"

    try:
        erp_snapshot = fetch_shiller_ttm_eps()
        erp_ttm = erp_snapshot.get("erp")
        erp_ttm_source = str(erp_snapshot.get("source", "unavailable:erp_ttm"))
    except Exception as exc:
        logger.warning("Shiller ERP fetch failed: %s", exc)
        erp_ttm = None
        erp_ttm_source = "unavailable:erp_ttm"

    reference_capital = float(os.environ.get("V11_REFERENCE_CAPITAL", "100000"))
    current_nav = float(os.environ.get("V11_CURRENT_NAV", str(reference_capital)))

    raw_row = _build_v12_live_macro_row(
        observation_date=pd.Timestamp(price_data["date"]),
        build_version="v12_live_feedback",
        credit_spread=float(credit_spread),
        credit_spread_source=credit_spread_source,
        real_yield_pct_points=real_yield_pct,
        real_yield_source=real_yield_source,
        net_liquidity=net_liq,
        net_liquidity_source=net_liquidity_source,
        treasury_vol=treasury_vol,
        treasury_vol_source=treasury_vol_source,
        copper_gold_ratio=copper_gold_ratio,
        copper_gold_source=copper_gold_source,
        breakeven_pct_points=(float(breakeven) * 100.0) if breakeven is not None else None,
        breakeven_source=breakeven_source,
        core_capex=core_capex,
        core_capex_source=core_capex_source,
        usdjpy=usdjpy,
        usdjpy_source=usdjpy_source,
        erp_ttm_pct_points=(float(erp_ttm) * 100.0) if erp_ttm is not None else None,
        erp_ttm_source=erp_ttm_source,
        reference_capital=reference_capital,
        current_nav=current_nav,
    )

    # v12.1: Attach history for Sentinel
    raw_row.attrs["history"] = price_data["history"]

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
