"""Web exporter for the v11.5 Bayesian probabilistic monitor."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import pytz

from src.models import SignalResult
from src.store.cloud_manager import CloudPersistenceBridge

try:
    import pandas_market_calendars as mcal
except ModuleNotFoundError:
    mcal = None

logger = logging.getLogger(__name__)
EASTERN = pytz.timezone("US/Eastern")

REGIME_MAP = {
    "MID_CYCLE": {"label": "中期平稳 (MID_CYCLE)", "desc": "周期中性平稳期，穿越波动的基准轨道。"},
    "BUST": {"label": "休克 (BUST)", "desc": "信贷断裂引发流动性休克，强制避险。"},
    "CAPITULATION": {"label": "投降 (CAPITULATION)", "desc": "绝望式抛售触及极值，高赔率反弹窗口。"},
    "RECOVERY": {"label": "修复 (RECOVERY)", "desc": "最差阶段已过，动能开始共振回归。"},
    "LATE_CYCLE": {"label": "末端 (LATE_CYCLE)", "desc": "周期动能衰减，结构性风险增加，审慎缩减。"},
}


def _discretize_allocation(beta: float) -> str:
    """Maps precise beta/allocation to 10% bands."""
    if beta <= 0.05: return "0-5% (极轻仓/现金)"
    if beta <= 0.25: return "10-20% (防御性)"
    if beta <= 0.45: return "30-40% (保守)"
    if beta <= 0.65: return "50-60% (稳健)"
    if beta <= 0.85: return "70-80% (积极)"
    if beta <= 1.05: return "90-100% (满仓)"
    return "110-120% (进攻/杠杆)"


class MarketCursor:
    """Handles market calendar aware calculations."""
    def __init__(self, calendar_name: str = "NYSE"):
        if mcal:
            self.cal = mcal.get_calendar(calendar_name)
        else:
            self.cal = None

    def get_market_state(self, now: datetime) -> str:
        if not self.cal: return "UNKNOWN"
        now_utc = now.astimezone(UTC)
        schedule = self.cal.schedule(start_date=now.date(), end_date=now.date())
        if schedule.empty: return "FROZEN"
        return "ACTIVE" if (schedule.iloc[0].market_open <= pd.Timestamp(now_utc) <= schedule.iloc[0].market_close) else "FROZEN"

    def get_expires_at_utc(self, now: datetime, jitter_hours: int = 4) -> datetime:
        if not self.cal: return (now + timedelta(hours=24)).astimezone(UTC)
        now_est = now.astimezone(EASTERN)
        schedule = self.cal.schedule(start_date=now_est.date(), end_date=(now_est + timedelta(days=7)).date())
        # Simplification: next day open + jitter
        next_open = schedule.iloc[1].market_open if now.astimezone(UTC) > schedule.iloc[0].market_close else schedule.iloc[0].market_open
        return (next_open + timedelta(hours=jitter_hours)).to_pydatetime().astimezone(UTC)


def export_web_snapshot(result: SignalResult, output_path: str | Path | None = None) -> bool:
    """Export a v11.5 compliant web snapshot."""
    try:
        now_utc = datetime.now(UTC)
        cursor = MarketCursor()
        
        regime_info = REGIME_MAP.get(result.stable_regime, {"label": result.stable_regime, "desc": "Unknown"})
        metadata = result.metadata or {}
        
        payload = {
            "meta": {
                "version": "v11.5",
                "calculated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires_at_utc": cursor.get_expires_at_utc(now_utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "market_state": cursor.get_market_state(now_utc),
            },
            "signal": {
                "regime": regime_info["label"],
                "regime_desc": regime_info["desc"],
                "target_beta": result.target_beta,
                "entropy": result.entropy,
                "exposure_band": _discretize_allocation(result.target_beta),
                "probabilities": result.probabilities,
                "reference_path": {
                    "qqq_pct": result.target_allocation.target_qqq_pct,
                    "qld_pct": result.target_allocation.target_qld_pct,
                    "cash_pct": result.target_allocation.target_cash_pct,
                },
            },
            "evidence": {
                "logic_trace": result.logic_trace,
                "feature_values": metadata.get("feature_values", {}),
            }
        }

        path = Path(output_path) if output_path else Path("src/web/public/status.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return True
    except Exception as exc:
        logger.error("Web export failed: %s", exc)
        return False


def export_feature_library_to_blob(library_path: str | Path = "data/v11_feature_library.csv") -> bool:
    """Sync V11 feature library to cloud."""
    cloud = CloudPersistenceBridge()
    if not cloud.is_ci or not cloud.token: return False
    lib_path = Path(library_path)
    if not lib_path.exists(): return False
    try:
        with open(lib_path, "rb") as f:
            return cloud.push_payload(f.read(), "v11_feature_library.csv", is_binary=True)
    except Exception:
        return False
