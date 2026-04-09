"""Web exporter for the v13.0 Bayesian probabilistic monitor."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz

from src.constants import ENGINE_VERSION
from src.models import SignalResult
from src.regime_topology import (
    ACTIVE_REGIME_ORDER,
    REGIME_DISPLAY_MAP,
    canonicalize_regime_name,
    merge_regime_weights,
)

try:
    import pandas_market_calendars as mcal
except ModuleNotFoundError:
    mcal = None

logger = logging.getLogger(__name__)
EASTERN = pytz.timezone("US/Eastern")

REGIME_MAP = REGIME_DISPLAY_MAP


def _discretize_allocation(beta: float) -> str:
    """Maps precise beta/allocation to categorical bands."""
    if beta <= 0.05:
        return "Beta 0.00-0.05x (极轻仓/现金)"
    if beta <= 0.25:
        return "Beta 0.05-0.25x (防御性)"
    if beta <= 0.45:
        return "Beta 0.25-0.45x (保守)"
    if beta <= 0.65:
        return "Beta 0.45-0.65x (稳健)"
    if beta <= 0.85:
        return "Beta 0.65-0.85x (积极)"
    if beta <= 1.05:
        return "Beta 0.85-1.05x (满仓)"
    return "Beta >1.05x (进攻/杠杆)"


class MarketCursor:
    """Handles market calendar aware calculations."""

    def __init__(self, calendar_name: str = "NYSE"):
        if mcal:
            self.cal = mcal.get_calendar(calendar_name)
        else:
            self.cal = None

    def get_market_state(self, now: datetime) -> str:
        if not self.cal:
            return "UNKNOWN"
        now_utc = now.astimezone(UTC)
        schedule = self.cal.schedule(start_date=now.date(), end_date=now.date())
        if schedule.empty:
            return "FROZEN"
        return (
            "ACTIVE"
            if (
                schedule.iloc[0].market_open
                <= pd.Timestamp(now_utc)
                <= schedule.iloc[0].market_close
            )
            else "FROZEN"
        )

    def get_expires_at_utc(self, now: datetime, jitter_hours: int = 4) -> datetime:
        if not self.cal:
            return (now + timedelta(hours=24)).astimezone(UTC)
        now_est = now.astimezone(EASTERN)
        schedule = self.cal.schedule(
            start_date=now_est.date(), end_date=(now_est + timedelta(days=7)).date()
        )
        # Simplification: next day open + jitter
        next_open = (
            schedule.iloc[1].market_open
            if now.astimezone(UTC) > schedule.iloc[0].market_close
            else schedule.iloc[0].market_open
        )
        return (next_open + timedelta(hours=jitter_hours)).to_pydatetime().astimezone(UTC)


def export_web_snapshot(result: SignalResult, output_path: str | Path | None = None) -> bool:
    """Export a v13.0 compliant high-fidelity web snapshot."""
    try:
        now_utc = datetime.now(UTC)
        cursor = MarketCursor()

        stable_regime = canonicalize_regime_name(result.stable_regime) or result.stable_regime
        probabilities = merge_regime_weights(
            result.probabilities,
            regimes=ACTIVE_REGIME_ORDER,
            include_zeros=True,
        )
        priors = merge_regime_weights(
            result.priors,
            regimes=ACTIVE_REGIME_ORDER,
            include_zeros=True,
        )
        regime_info = REGIME_MAP.get(stable_regime, {"label": stable_regime, "desc": "Unknown"})
        metadata = result.metadata or {}
        execution_overlay = metadata.get("execution_overlay", {})

        # Extract lock state from logic trace
        lock_active = False
        execution_bucket = str(metadata.get("execution_bucket", "CASH"))
        for trace in result.logic_trace:
            if trace.get("step") == "behavioral_guard":
                guard_res = trace.get("result", {})
                lock_active = guard_res.get("lock_active", False)
                execution_bucket = str(guard_res.get("target_bucket", execution_bucket))

        raw_regime = (
            canonicalize_regime_name(metadata.get("raw_regime", stable_regime)) or stable_regime
        )
        deployment_state = str(metadata.get("deployment_state", "DEPLOY_BASE"))
        deployment_state_key = str(
            metadata.get("deployment_state_key", deployment_state.replace("DEPLOY_", ""))
        )

        payload = {
            "meta": {
                "version": ENGINE_VERSION,
                "calculated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "observation_date": result.date.isoformat(),
                "expires_at_utc": cursor.get_expires_at_utc(now_utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "market_state": cursor.get_market_state(now_utc),
            },
            "signal": {
                "regime": regime_info["label"],
                "regime_desc": regime_info["desc"],
                "stable_regime": stable_regime,
                "raw_regime": raw_regime,
                "target_beta": result.target_beta,
                "raw_target_beta": metadata.get("raw_target_beta", result.target_beta),
                "raw_target_beta_pre_floor": metadata.get(
                    "raw_target_beta_pre_floor",
                    metadata.get("raw_target_beta", result.target_beta),
                ),
                "protected_beta": metadata.get(
                    "protected_beta", metadata.get("raw_target_beta", result.target_beta)
                ),
                "is_floor_active": bool(metadata.get("is_floor_active", False)),
                "hydration_anchor": metadata.get("hydration_anchor", "2018-01-01"),
                "overlay_beta": metadata.get("overlay_beta", result.target_beta),
                "overlay_mode": metadata.get(
                    "overlay_mode", execution_overlay.get("overlay_mode", "FULL")
                ),
                "beta_overlay_multiplier": metadata.get("beta_overlay_multiplier", 1.0),
                "deployment_overlay_multiplier": metadata.get("deployment_overlay_multiplier", 1.0),
                "overlay_state": metadata.get("overlay_state", "NEUTRAL"),
                "overlay_summary": metadata.get("overlay_summary", "NEUTRAL"),
                "beta_ceiling": metadata.get("beta_ceiling", 1.20),
                "entropy": result.entropy,
                "lock_active": lock_active,
                "exposure_band": _discretize_allocation(result.target_beta),
                "probabilities": probabilities,
                "priors": priors,
                "prior_breakdown": metadata.get("prior_details", {}),
                "deployment_readiness": metadata.get("deployment_readiness", 0.0),
                "deployment_readiness_overlay": metadata.get(
                    "deployment_readiness_overlay",
                    metadata.get("deployment_readiness", 0.0),
                ),
                "deployment_state": deployment_state,
                "deployment_state_key": deployment_state_key,
                "execution_bucket": execution_bucket,
                "probability_dynamics": metadata.get("probability_dynamics", {}),
                "price_topology": metadata.get("price_topology", {}),
                "forensic_snapshot_path": metadata.get("forensic_snapshot_path"),
                "reference_path": {
                    "qqq_pct": result.target_allocation.target_qqq_pct,
                    "qld_pct": result.target_allocation.target_qld_pct,
                    "cash_pct": result.target_allocation.target_cash_pct,
                },
                "resonance": metadata.get("signal", {}).get("resonance", {
                    "action": "HOLD",
                    "confidence": 0.0,
                    "reason": "Resonance Engine Initializing"
                }),
            },
            "evidence": {
                "logic_trace": result.logic_trace,
                "feature_values": metadata.get("feature_values", {}),
                "execution_overlay": execution_overlay,
                "bayesian_diagnostics": metadata.get("v13_4_diagnostics", {}),
                "price_topology": metadata.get("price_topology", {}),
            },
            "diagnostics": {
                "tractor": {
                    "prob": metadata.get("v14_baseline_prob", 0.0),
                    "status": metadata.get("v14_baseline_status", "unknown"),
                    "valid": bool(metadata.get("v14_tractor_valid", False)),
                },
                "sidecar": {
                    "prob": metadata.get("v14_sidecar_prob", 0.0),
                    "status": metadata.get("v14_sidecar_status", "unknown"),
                    "valid": bool(metadata.get("v14_sidecar_valid", False)),
                },
                "ensemble_options": {
                    "verdict": metadata.get("v14_ensemble_verdict", "NEUTRAL"),
                    "verdict_label": metadata.get(
                        "v14_ensemble_verdict_label",
                        metadata.get("v14_ensemble_verdict", "NEUTRAL"),
                    ),
                    "standard_beta": metadata.get("v14_standard_beta", result.target_beta),
                    "protective_beta": metadata.get("v14_s4_protective_beta", 0.5),
                    "aggressive_beta": metadata.get("v14_s5_aggressive_beta", result.target_beta),
                    "system_floor": 0.5,
                    "calm_eligible": bool(metadata.get("v14_calm_eligible", False)),
                },
                "shadow_mode": bool(
                    metadata.get("v14_shadow_mode", not metadata.get("v14_baseline_active", False))
                ),
                "recovery_hmm_shadow": metadata.get("recovery_hmm_shadow", {}),
            },
        }
        path = Path(output_path) if output_path else Path("src/web/public/status.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return True
    except Exception as exc:
        logger.error("Web export failed: %s", exc)
        return False
