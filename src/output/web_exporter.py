"""Web exporter for the v11.5 Bayesian probabilistic monitor."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz

from src.regime_topology import (
    ACTIVE_REGIME_ORDER,
    REGIME_DISPLAY_MAP,
    canonicalize_regime_name,
    merge_regime_weights,
)
from src.models import SignalResult

try:
    import pandas_market_calendars as mcal
except ModuleNotFoundError:
    mcal = None

logger = logging.getLogger(__name__)
EASTERN = pytz.timezone("US/Eastern")

REGIME_MAP = REGIME_DISPLAY_MAP


def _discretize_allocation(beta: float) -> str:
    """Maps precise beta/allocation to 10% bands."""
    if beta <= 0.05:
        return "0-5% (极轻仓/现金)"
    if beta <= 0.25:
        return "10-20% (防御性)"
    if beta <= 0.45:
        return "30-40% (保守)"
    if beta <= 0.65:
        return "50-60% (稳健)"
    if beta <= 0.85:
        return "70-80% (积极)"
    if beta <= 1.05:
        return "90-100% (满仓)"
    return "110-120% (进攻/杠杆)"


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
    """Export a v11.5 compliant high-fidelity web snapshot."""
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
        regime_info = REGIME_MAP.get(
            stable_regime, {"label": stable_regime, "desc": "Unknown"}
        )
        metadata = result.metadata or {}

        # Extract lock state from logic trace
        lock_active = False
        execution_bucket = str(metadata.get("execution_bucket", "CASH"))
        for trace in result.logic_trace:
            if trace.get("step") == "behavioral_guard":
                guard_res = trace.get("result", {})
                lock_active = guard_res.get("lock_active", False)
                execution_bucket = str(guard_res.get("target_bucket", execution_bucket))

        raw_regime = canonicalize_regime_name(metadata.get("raw_regime", stable_regime)) or stable_regime
        deployment_state = str(metadata.get("deployment_state", "DEPLOY_BASE"))
        deployment_state_key = str(
            metadata.get("deployment_state_key", deployment_state.replace("DEPLOY_", ""))
        )

        payload = {
            "meta": {
                "version": "v11.5",
                "calculated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "observation_date": result.date.isoformat(),
                "expires_at_utc": cursor.get_expires_at_utc(now_utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "market_state": cursor.get_market_state(now_utc),
            },
            "signal": {
                "regime": regime_info["label"],
                "regime_desc": regime_info["desc"],
                "stable_regime": stable_regime,
                "raw_regime": raw_regime,
                "target_beta": result.target_beta,
                "raw_target_beta": metadata.get("raw_target_beta", result.target_beta),
                "beta_ceiling": metadata.get("beta_ceiling", 1.20),
                "entropy": result.entropy,
                "lock_active": lock_active,
                "exposure_band": _discretize_allocation(result.target_beta),
                "probabilities": probabilities,
                "priors": priors,
                "prior_breakdown": metadata.get("prior_details", {}),
                "deployment_readiness": metadata.get("deployment_readiness", 0.0),
                "deployment_state": deployment_state,
                "deployment_state_key": deployment_state_key,
                "execution_bucket": execution_bucket,
                "reference_path": {
                    "qqq_pct": result.target_allocation.target_qqq_pct,
                    "qld_pct": result.target_allocation.target_qld_pct,
                    "cash_pct": result.target_allocation.target_cash_pct,
                },
            },
            "evidence": {
                "logic_trace": result.logic_trace,
                "feature_values": metadata.get("feature_values", {}),
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
