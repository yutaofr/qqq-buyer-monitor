"""
QQQ Monitor Main Entry Point (v11 Bayesian Convergence).

Only the v11 probabilistic engine is supported. All v10 and legacy logic
has been removed for architecture sanity.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from pathlib import Path

import pandas as pd

from src.constants import ENGINE_VERSION
from src.models import SignalResult, TargetAllocationState
from src.store.cloud_manager import CloudPersistenceBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
logger = logging.getLogger("qqq_monitor")

CANONICAL_PRIOR_SEED_PATH = Path("src/engine/v11/resources/v13_6_cold_start_seed.json")
RECOVERY_HMM_SHADOW_SUMMARY_PATH = Path("artifacts/recovery_hmm_shadow/mainline/summary.json")
RECOVERY_HMM_SHADOW_COMPARISON_PATH = Path("artifacts/recovery_hmm_shadow/mainline/comparison.json")
RECOVERY_HMM_SHADOW_LINEAGE_PATH = Path(
    "artifacts/recovery_hmm_shadow/mainline/source_lineage.json"
)


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


def _materialize_prior_state(
    prior_state_path: str | Path,
    seed_path: str | Path = CANONICAL_PRIOR_SEED_PATH,
) -> str:
    """
    Ensure production has a mutable prior state file without replaying history.

    Returns the origin used:
    - ``existing_state`` when the runtime state already exists
    - ``canonical_seed`` when a checked-in hydrated seed was copied into place
    """
    runtime_path = Path(prior_state_path)
    if runtime_path.exists():
        return "existing_state"

    canonical_seed = Path(seed_path)
    if not canonical_seed.exists():
        raise FileNotFoundError(
            f"Production cold start requires a canonical hydrated prior seed at {canonical_seed}."
        )

    payload = json.loads(canonical_seed.read_text(encoding="utf-8"))
    required_fields = {"regimes", "counts", "execution_state", "bootstrap_fingerprint"}
    missing_fields = sorted(required_fields - set(payload))
    if missing_fields:
        raise ValueError(
            "Canonical hydrated prior seed is incomplete: missing " + ", ".join(missing_fields)
        )

    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(canonical_seed, runtime_path)
    return "canonical_seed"


def _load_recovery_hmm_shadow_diagnostics() -> dict[str, object]:
    summary_path = RECOVERY_HMM_SHADOW_SUMMARY_PATH
    if not summary_path.exists():
        return {}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    out: dict[str, object] = {
        "decision_gate": summary.get("decision_gate", "UNKNOWN"),
        "acceptance": summary.get("acceptance", {}),
        "component_count": summary.get("component_count"),
        "explained_variance_ratio_sum": summary.get("explained_variance_ratio_sum"),
        "trace_path": summary.get("trace_path"),
    }
    if RECOVERY_HMM_SHADOW_COMPARISON_PATH.exists():
        out["comparison"] = json.loads(
            RECOVERY_HMM_SHADOW_COMPARISON_PATH.read_text(encoding="utf-8")
        )
    if RECOVERY_HMM_SHADOW_LINEAGE_PATH.exists():
        lineage = json.loads(RECOVERY_HMM_SHADOW_LINEAGE_PATH.read_text(encoding="utf-8"))
        out["source_notes"] = lineage.get("source_notes", {})
        out["coverage"] = lineage.get("coverage", {})
    return out


def _refresh_price_cache_from_live_data(
    price_cache_path: str | Path,
    *,
    fetcher,
) -> bool:
    """
    Refresh the local QQQ price cache from the live fetcher before bootstrap audit.

    This keeps the production baseline usable on T+0 when the checked-in cache is
    one business day behind, without weakening other artifact integrity checks.
    """
    live_payload = fetcher()
    history = live_payload.get("history")
    if not isinstance(history, pd.DataFrame) or history.empty:
        raise RuntimeError("Live price refresh returned no history for cache repair.")

    refreshed = history.reset_index()
    date_column = refreshed.columns[0]
    refreshed = refreshed.rename(columns={date_column: "Date"})

    cache_path = Path(price_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    refreshed.to_csv(cache_path, index=False)
    logger.info(
        "Refreshed price cache from live data before bootstrap audit: %s",
        pd.Timestamp(live_payload["date"]).date().isoformat(),
    )
    return True


def _build_v11_signal_result(runtime_result: dict, *, price: float) -> SignalResult:
    """Map conductor runtime output to the unified v11 SignalResult model."""
    allocation = runtime_result["target_allocation"]
    nav = max(
        1.0,
        float(
            allocation["qqq_dollars"]
            + allocation["qld_notional_dollars"]
            + allocation["cash_dollars"]
        ),
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
    posterior_regime = ordered_probs[0][0]
    execution_regime = runtime_result.get("stable_regime", posterior_regime)
    raw_regime = runtime_result.get("raw_regime", posterior_regime)
    deployment = runtime_result.get("deployment", {})
    deployment_state = str(deployment.get("deployment_state", "DEPLOY_BASE"))
    deployment_state_key = deployment_state.replace("DEPLOY_", "")
    execution_bucket = str(runtime_result.get("signal", {}).get("target_bucket", "QQQ"))
    quality_audit = runtime_result.get("quality_audit", {})
    posterior_entropy = float(
        quality_audit.get("posterior_entropy", runtime_result.get("entropy", 0.0))
    )
    effective_entropy = float(
        quality_audit.get("effective_entropy", runtime_result.get("entropy", 0.0))
    )

    explanation = (
        f"{ENGINE_VERSION} Orthogonal Bayesian Conductor: beta={runtime_result['target_beta']:.2f}x | "
        f"entropy={posterior_entropy:.3f} | "
        f"posterior={posterior_regime} ({ordered_probs[0][1]:.1%}) | "
        f"execution={execution_regime} | raw={raw_regime} | "
        f"deploy={deployment_state_key}"
    )

    return SignalResult(
        date=pd.Timestamp(runtime_result["date"]).date(),
        price=float(price),
        target_beta=float(runtime_result["target_beta"]),
        probabilities={k: float(v) for k, v in runtime_result["probabilities"].items()},
        priors={k: float(v) for k, v in runtime_result.get("priors", {}).items()},
        entropy=posterior_entropy,
        stable_regime=str(posterior_regime),
        target_allocation=target_allocation,
        logic_trace=[
            {"step": "probabilistic_inference", "result": runtime_result["probabilities"]},
            {"step": "price_topology", "result": runtime_result.get("price_topology", {})},
            {"step": "bayesian_diagnostics", "result": runtime_result.get("v13_4_diagnostics", {})},
            {
                "step": "entropy_haircut",
                "result": {
                    "posterior_entropy": posterior_entropy,
                    "effective_entropy": effective_entropy,
                },
            },
            {"step": "execution_overlay", "result": runtime_result.get("overlay", {})},
            {"step": "position_sizing", "result": runtime_result["target_allocation"]},
            {"step": "deployment_policy", "result": deployment},
            {"step": "behavioral_guard", "result": runtime_result["signal"]},
        ],
        explanation=explanation,
        metadata={
            "engine_version": ENGINE_VERSION,
            "posterior_regime": str(posterior_regime),
            "execution_regime": str(execution_regime),
            "quality_audit": quality_audit,
            "effective_entropy": effective_entropy,
            "feature_values": runtime_result.get("feature_values", {}),
            "prior_details": runtime_result.get("prior_details", {}),
            "deployment_readiness": float(runtime_result.get("deployment_readiness", 0.0)),
            "deployment_readiness_overlay": float(
                runtime_result.get(
                    "deployment_readiness_overlay", runtime_result.get("deployment_readiness", 0.0)
                )
            ),
            "raw_target_beta": float(
                runtime_result.get("raw_target_beta", runtime_result["target_beta"])
            ),
            "protected_beta": float(
                runtime_result.get(
                    "protected_beta",
                    runtime_result.get("raw_target_beta", runtime_result["target_beta"]),
                )
            ),
            "raw_target_beta_pre_floor": float(
                runtime_result.get("raw_target_beta_pre_floor", runtime_result["target_beta"])
            ),
            "is_floor_active": bool(runtime_result.get("is_floor_active", False)),
            "hydration_anchor": str(
                runtime_result.get("signal", {}).get("hydration_anchor", "2018-01-01")
            ),
            "v13_4_diagnostics": runtime_result.get("v13_4_diagnostics", {}),
            "overlay_beta": float(
                runtime_result.get("overlay_beta", runtime_result["target_beta"])
            ),
            "overlay_mode": str(runtime_result.get("overlay", {}).get("overlay_mode", "FULL")),
            "beta_overlay_multiplier": float(
                runtime_result.get("overlay", {}).get("beta_overlay_multiplier", 1.0)
            ),
            "deployment_overlay_multiplier": float(
                runtime_result.get("overlay", {}).get("deployment_overlay_multiplier", 1.0)
            ),
            "overlay_state": str(runtime_result.get("overlay", {}).get("overlay_state", "NEUTRAL")),
            "overlay_summary": str(
                runtime_result.get("overlay", {}).get("overlay_summary", "NEUTRAL")
            ),
            "execution_overlay": runtime_result.get("overlay", {}),
            "probability_dynamics": runtime_result.get("probability_dynamics", {}),
            "price_topology": runtime_result.get("price_topology", {}),
            "raw_regime": raw_regime,
            "deployment_state": deployment_state,
            "deployment_state_key": deployment_state_key,
            "execution_bucket": execution_bucket,
            "beta_ceiling": 1.2,
            "forensic_snapshot_path": runtime_result.get("forensic_snapshot_path"),
            "signal": runtime_result.get("signal", {}),
        },
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
    qqq_close: float | None = None,
    qqq_close_source: str = "unavailable:qqq_close",
    qqq_close_quality_score: float | None = None,
    qqq_volume: float | None = None,
    qqq_volume_source: str = "unavailable:qqq_volume",
    qqq_volume_quality_score: float | None = None,
    adv_dec_ratio: float | None = None,
    breadth_source: str = "unavailable:breadth",
    breadth_quality_score: float | None = None,
    ndx_concentration: float | None = None,
    ndx_concentration_source: str = "unavailable:ndx_concentration",
    ndx_concentration_quality_score: float | None = None,
    vix_1m: float | None = None,
    vix_3m: float | None = None,
    reference_capital: float = 100000.0,
    current_nav: float = 100000.0,
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
                "real_yield_10y_pct": (float(real_yield_pct_points) / 100.0)
                if real_yield_pct_points is not None
                else None,
                "source_real_yield": str(real_yield_source),
                "net_liquidity_usd_bn": float(net_liquidity) if net_liquidity is not None else None,
                "source_net_liquidity": str(net_liquidity_source),
                "treasury_vol_21d": float(treasury_vol) if treasury_vol is not None else None,
                "source_treasury_vol": str(treasury_vol_source),
                "copper_gold_ratio": float(copper_gold_ratio)
                if copper_gold_ratio is not None
                else None,
                "stress_vix": float(vix_1m) if vix_1m is not None else None,
                "stress_vix3m": float(vix_3m) if vix_3m is not None else None,
                "source_copper_gold": str(copper_gold_source),
                "breakeven_10y": (float(breakeven_pct_points) / 100.0)
                if breakeven_pct_points is not None
                else None,
                "source_breakeven": str(breakeven_source),
                "core_capex_mm": float(core_capex) if core_capex is not None else None,
                "source_core_capex": str(core_capex_source),
                "usdjpy": float(usdjpy) if usdjpy is not None else None,
                "source_usdjpy": str(usdjpy_source),
                "erp_ttm_pct": (float(erp_ttm_pct_points) / 100.0)
                if erp_ttm_pct_points is not None
                else None,
                "source_erp_ttm": str(erp_ttm_source),
                "qqq_close": float(qqq_close) if qqq_close is not None else None,
                "source_qqq_close": str(qqq_close_source),
                "qqq_close_quality_score": float(qqq_close_quality_score)
                if qqq_close_quality_score is not None
                else None,
                "qqq_volume": float(qqq_volume) if qqq_volume is not None else None,
                "source_qqq_volume": str(qqq_volume_source),
                "qqq_volume_quality_score": float(qqq_volume_quality_score)
                if qqq_volume_quality_score is not None
                else None,
                "adv_dec_ratio": float(adv_dec_ratio) if adv_dec_ratio is not None else None,
                "source_breadth_proxy": str(breadth_source),
                "breadth_quality_score": float(breadth_quality_score)
                if breadth_quality_score is not None
                else None,
                "ndx_concentration": float(ndx_concentration)
                if ndx_concentration is not None
                else None,
                "source_ndx_concentration": str(ndx_concentration_source),
                "ndx_concentration_quality_score": float(ndx_concentration_quality_score)
                if ndx_concentration_quality_score is not None
                else None,
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


def _persist_and_export_web_artifacts(
    *,
    result: SignalResult,
    raw_row: pd.DataFrame,
    cloud: CloudPersistenceBridge,
    sync_files: list[str],
    web_json_path: str,
    history_json_path: str,
) -> None:
    from src.output.web_exporter import export_history_json, export_web_snapshot
    from src.store.db import save_signal

    save_signal(result)
    _upsert_v11_macro_feedback(raw_row, "data/macro_historical_dump.csv")

    status_ok = export_web_snapshot(result, output_path=web_json_path)
    history_ok = export_history_json(output_path=history_json_path)

    if not status_ok:
        raise RuntimeError("Web snapshot export failed")
    if not history_ok:
        Path(history_json_path).unlink(missing_ok=True)
        raise RuntimeError("History export failed")

    if cloud.is_ci:
        cloud.push_state(sync_files)
        with open(web_json_path, "rb") as f:
            cloud.push_payload(f.read(), "status.json", is_binary=True)
        if Path(history_json_path).exists():
            with open(history_json_path, "rb") as f:
                cloud.push_payload(f.read(), "history.json", is_binary=True)


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
            existing["observation_date"] = pd.to_datetime(
                existing["observation_date"]
            ).dt.date.astype(str)
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
    from src.collector.breadth import fetch_breadth
    from src.collector.global_macro import (
        fetch_breakeven_inflation,
        fetch_copper_gold_ratio,
        fetch_core_capex_momentum,
        fetch_shiller_ttm_eps,
        fetch_treasury_realized_vol,
        fetch_usdjpy_snapshot,
        fetch_vix_term_structure_snapshot,
    )
    from src.collector.macro import fetch_credit_spread_snapshot
    from src.collector.macro_v3 import fetch_net_liquidity_snapshot, fetch_real_yield_snapshot
    from src.collector.price import fetch_price_data
    from src.engine.aggregator import FullPanoramaAggregator
    from src.engine.baseline.execution import run_baseline_inference
    from src.engine.v11.conductor import V11Conductor
    from src.output.cli import print_signal
    from src.output.report import to_json

    cloud = CloudPersistenceBridge()

    prior_file_path = os.environ.get("PRIOR_STATE_PATH", "data/v13_6_ex_hydrated_prior.json")
    prior_seed_path = os.environ.get("PRIOR_SEED_PATH", str(CANONICAL_PRIOR_SEED_PATH))
    sync_files = [
        "data/signals.db",
        "data/macro_historical_dump.csv",
        "data/qqq_history_cache.csv",
        prior_file_path,
    ]
    if not cloud.pull_state(sync_files):
        raise RuntimeError(
            "Cloud state pull failed; refusing to continue with potentially stale runtime memory."
        )

    prior_origin = _materialize_prior_state(prior_file_path, prior_seed_path)
    if prior_origin == "canonical_seed":
        logger.info(
            "Prior state %s was missing after cloud pull. Restored mutable runtime state from canonical seed %s.",
            prior_file_path,
            prior_seed_path,
        )

    # ── V14.9 Bootstrap Guardian ──────────────────────────
    from src.engine.v11.utils.bootstrap_guardian import BootstrapGuardian

    guardian = BootstrapGuardian(
        macro_csv_path="data/macro_historical_dump.csv",
        price_cache_path="data/qqq_history_cache.csv",
        cold_start_seed_path=prior_seed_path,
    )
    audit_report = guardian.audit()
    if (
        not audit_report.is_healthy
        and not getattr(audit_report, "macro_gaps", [])
        and getattr(audit_report, "price_cache_staleness", None) is not None
        and getattr(audit_report.price_cache_staleness, "days_stale", 0) > 0
    ):
        from src.collector.price import fetch_price_data

        _refresh_price_cache_from_live_data(
            "data/qqq_history_cache.csv",
            fetcher=fetch_price_data,
        )
        audit_report = guardian.audit()
    if not audit_report.is_healthy:
        raise RuntimeError(
            "Bootstrap Guardian unhealthy; refusing to continue with a non-artifact cold start."
        )
    # ── END Guardian ──────────────────────────────────────

    logger.info("Fetching market data...")
    price_data = fetch_price_data()
    price_history = price_data.get("history")
    qqq_close = float(price_data["price"])
    qqq_volume = None
    qqq_volume_source = "unavailable:qqq_volume"
    qqq_volume_quality = 0.0
    if (
        isinstance(price_history, pd.DataFrame)
        and not price_history.empty
        and "Volume" in price_history.columns
    ):
        latest_volume = pd.to_numeric(price_history["Volume"].iloc[-1], errors="coerce")
        if pd.notna(latest_volume):
            qqq_volume = float(latest_volume)
            qqq_volume_source = "direct:yfinance"
            qqq_volume_quality = 1.0

    try:
        breadth_snapshot = fetch_breadth(as_of=price_data["date"])
        adv_dec_ratio = breadth_snapshot.get("adv_dec_ratio")
        breadth_source = str(breadth_snapshot.get("source", "unavailable:breadth"))
        breadth_quality = float(breadth_snapshot.get("quality", 0.0) or 0.0)
        ndx_concentration = breadth_snapshot.get("ndx_concentration")
        ndx_concentration_source = str(
            breadth_snapshot.get("ndx_concentration_source", "unavailable:ndx_concentration")
        )
        ndx_concentration_quality = float(
            breadth_snapshot.get("ndx_concentration_quality", 0.0) or 0.0
        )
    except Exception as exc:
        logger.warning("Breadth fetch failed: %s", exc)
        adv_dec_ratio = None
        breadth_source = "unavailable:breadth"
        breadth_quality = 0.0
        ndx_concentration = None
        ndx_concentration_source = "unavailable:ndx_concentration"
        ndx_concentration_quality = 0.0

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
        net_liquidity_source = str(
            net_liquidity_snapshot.get("source", "unavailable:net_liquidity")
        )
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

    try:
        vix_snapshot = fetch_vix_term_structure_snapshot()
        vix_1m = vix_snapshot.get("vix")
        vix_3m = vix_snapshot.get("vxv")
    except Exception as exc:
        logger.warning("VIX term structure fetch failed: %s", exc)
        vix_1m = None
        vix_3m = None

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
        qqq_close=qqq_close,
        qqq_close_source="direct:yfinance",
        qqq_close_quality_score=1.0,
        qqq_volume=qqq_volume,
        qqq_volume_source=qqq_volume_source,
        qqq_volume_quality_score=qqq_volume_quality,
        adv_dec_ratio=adv_dec_ratio,
        breadth_source=breadth_source,
        breadth_quality_score=breadth_quality,
        ndx_concentration=ndx_concentration,
        ndx_concentration_source=ndx_concentration_source,
        ndx_concentration_quality_score=ndx_concentration_quality,
        vix_1m=vix_1m,
        vix_3m=vix_3m,
        reference_capital=reference_capital,
        current_nav=current_nav,
    )

    # 3. Running Mud Tractor (V_Baseline) Shadow Model
    # Reordered to provide baseline_result to conductor (v14.5)
    baseline_result = run_baseline_inference(price_history=price_history["Close"])

    # 4. Bayesian Execution (v11)
    runtime = V11Conductor(prior_state_path=prior_file_path).daily_run(
        raw_row, baseline_result=baseline_result
    )

    # 4. Shadow Mode Diagnostics (Reference Only)
    # Both Tractor and Sidecar results will be stored in metadata.
    # PROHIBITION: No modification of runtime['target_beta'] as per v14.3 role.
    runtime["mud_tractor_diagnostics"] = baseline_result

    # 5. Full Panorama Aggregator (v14.8) - Ensemble Coordination
    # Synthesizes all 4 pipelines for user implementation options
    ensemble = FullPanoramaAggregator.aggregate(runtime, baseline_result)

    result = _build_v11_signal_result(runtime, price=float(price_data["price"]))

    # Add baseline metadata to SignalResult for diagnostic reference
    result.metadata["v14_baseline_prob"] = float(
        baseline_result.get("tractor", {}).get("prob", 0.0)
    )
    result.metadata["v14_sidecar_prob"] = float(baseline_result.get("sidecar", {}).get("prob", 0.0))
    result.metadata["v14_baseline_status"] = str(
        baseline_result.get("tractor", {}).get("status", "unknown")
    )
    result.metadata["v14_sidecar_status"] = str(
        baseline_result.get("sidecar", {}).get("status", "unknown")
    )
    result.metadata["v14_baseline_active"] = False  # Shadow Mode remains

    # Inject Ensemble Suggestions
    result.metadata["v14_ensemble_verdict"] = ensemble["ensemble_verdict"]
    result.metadata["v14_ensemble_verdict_label"] = ensemble["ensemble_verdict_label"]
    result.metadata["v14_s4_protective_beta"] = ensemble["s4_protective_beta"]
    result.metadata["v14_s5_aggressive_beta"] = ensemble["s5_aggressive_beta"]
    result.metadata["v14_standard_beta"] = ensemble["standard_beta"]
    result.metadata["v14_tractor_valid"] = bool(ensemble["tractor_valid"])
    result.metadata["v14_sidecar_valid"] = bool(ensemble["sidecar_valid"])
    result.metadata["v14_calm_eligible"] = bool(ensemble["calm_eligible"])
    result.metadata["v14_shadow_mode"] = True
    result.metadata["recovery_hmm_shadow"] = _load_recovery_hmm_shadow_diagnostics()

    web_json_path = "src/web/public/status.json"
    history_json_path = "src/web/public/history.json"

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
        _persist_and_export_web_artifacts(
            result=result,
            raw_row=raw_row,
            cloud=cloud,
            sync_files=sync_files,
            web_json_path=web_json_path,
            history_json_path=history_json_path,
        )
        logger.info("v11 signal persisted and cloud state synchronized.")
    else:
        from src.output.web_exporter import export_history_json, export_web_snapshot

        export_web_snapshot(result, output_path=web_json_path)
        export_history_json(output_path=history_json_path)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="QQQ Monitor Entry Point (v11 Bayesian Convergence)"
    )
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
