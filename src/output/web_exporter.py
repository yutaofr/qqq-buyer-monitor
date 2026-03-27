"""
Web Exporter (v8.2 Industrial Implementation).
Provides discretized data for the public dashboard and implements
timezone-aware market calendar leap logic.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pandas_market_calendars as mcal
import pytz

from src.models import SignalResult

logger = logging.getLogger("qqq_monitor.web_exporter")

EASTERN = pytz.timezone("US/Eastern")

class MarketCursor:
    """
    Handles market calendar aware calculations to prevent timezone drift
    and incorrect stale warnings during weekends/holidays.
    """
    def __init__(self, calendar_name: str = "NYSE"):
        self.cal = mcal.get_calendar(calendar_name)

    def _get_schedule(self, now: datetime, days: int = 10) -> pd.DataFrame:
        """Helper to get market schedule around a given time."""
        start_date = now.date()
        end_date = (now + timedelta(days=days)).date()
        return self.cal.schedule(start_date=start_date, end_date=end_date)

    def get_market_state(self, now: datetime) -> str:
        """Determines if the market is currently ACTIVE or FROZEN."""
        if now.tzinfo is None:
            raise ValueError("Must pass an aware datetime")
        
        now_utc = now.astimezone(timezone.utc)
        schedule = self._get_schedule(now.astimezone(EASTERN), days=1)
        
        try:
            is_open = self.cal.open_at_time(schedule, now_utc)
        except (ValueError, IndexError):
            is_open = False
            
        return "ACTIVE" if is_open else "FROZEN"

    def get_expires_at_utc(self, now: datetime, jitter_hours: int = 4) -> datetime:
        """
        Calculates the physical expiration time for the current signal.
        Leaps over weekends, holidays, and recognizes early closes.
        """
        if now.tzinfo is None:
            raise ValueError("Must pass an aware datetime")

        now_utc = now.astimezone(timezone.utc)
        now_est = now.astimezone(EASTERN)
        
        # Get NYSE schedule for today and next few days
        schedule = self._get_schedule(now_est, days=7)
        
        # Current day's close (UTC)
        today_close = schedule.iloc[0]['market_close'].to_pydatetime()
        
        if now_utc < today_close:
            # Market is open or hasn't closed yet today
            try:
                is_open = self.cal.open_at_time(schedule.iloc[[0]], now_utc)
            except (ValueError, IndexError):
                is_open = False

            if is_open:
                # ACTIVE: Expected next update is next hour on the hour
                next_expected = (now_est + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                # But not past today's close
                if next_expected.astimezone(timezone.utc) > today_close:
                    next_expected = today_close.astimezone(EASTERN)
            else:
                # Pre-market: Expected update at open
                next_expected = schedule.iloc[0]['market_open'].to_pydatetime().astimezone(EASTERN)
        else:
            # Market is closed for today, leap to next trading day's open
            next_expected = schedule.iloc[1]['market_open'].to_pydatetime().astimezone(EASTERN)

        # Add Jitter Buffer
        expires_at = next_expected + timedelta(hours=jitter_hours)
        return expires_at.astimezone(timezone.utc)

def _discretize_allocation(beta: float) -> str:
    """Maps precise beta/allocation to 10% bands to protect internal logic."""
    if beta <= 0.05: return "0-5% (极轻仓/现金)"
    if beta <= 0.25: return "10-20% (防御性)"
    if beta <= 0.45: return "30-40% (保守)"
    if beta <= 0.65: return "50-60% (稳健)"
    if beta <= 0.85: return "70-80% (积极)"
    return "90-100% (满仓/进攻)"

REGIME_MAP = {
    "CRISIS": {"label": "危机", "desc": "流动性枯竭，系统性风险爆发，首要任务是生存。"},
    "TRANSITION_STRESS": {"label": "压力过渡", "desc": "市场波动加剧，不确定性上升，建议缩减敞口。"},
    "RICH_TIGHTENING": {"label": "紧缩/高估", "desc": "估值性价比降低，政策环境收紧，审慎防御。"},
    "NEUTRAL": {"label": "中性", "desc": "估值与流动性处于平衡点，趋势不明，维持基准。"},
    "EUPHORIC": {"label": "狂热", "desc": "市场处于泡沫阶段，贪婪情绪过载，准备撤退。"}
}

DEPLOY_MAP = {
    "FAST": {"label": "快速入场", "desc": "机会窗口开启，增量资金应积极部署。"},
    "BASE": {"label": "常规入场", "desc": "遵循定投节奏，维持基准部署速率。"},
    "SLOW": {"label": "减速入场", "desc": "防御姿态，降低入场频率以规避波动。"},
    "PAUSE": {"label": "停止入场", "desc": "风险过载，增量资金持币观望，不接飞刀。"}
}

import requests

def export_web_snapshot(result: SignalResult, output_path: str | Path | None = None) -> bool:
    """
    Exports a discretized snapshot and uploads to Vercel Blob if in CI.
    Includes Chinese explanations for Regime and Deployment states.
    """
    try:
        now_utc = datetime.now(timezone.utc)
        cursor = MarketCursor()
        
        market_state = cursor.get_market_state(now_utc)
        expires_at_utc = cursor.get_expires_at_utc(now_utc, jitter_hours=4)
        
        from src.output.report import summarize_data_quality
        fidelity_summary = summarize_data_quality(result.data_quality)
        
        # Resolve mappings with fallbacks
        regime_key = str(result.tier0_regime)
        deploy_key = result.deployment_action.get("deploy_mode", "BASE")
        
        regime_info = REGIME_MAP.get(regime_key, {"label": regime_key, "desc": "未知宏观制度"})
        deploy_info = DEPLOY_MAP.get(deploy_key, {"label": deploy_key, "desc": "维持基准节奏"})

        payload = {
            "meta": {
                "version": "v8.2",
                "calculated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires_at_utc": expires_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "market_state": market_state
            },
            "signal": {
                "regime": regime_info["label"],
                "regime_desc": regime_info["desc"],
                "exposure_band": _discretize_allocation(result.target_beta),
                "exposure_desc": "存量资金目前的理想风险敞口上限。",
                "deploy_rhythm": deploy_info["label"],
                "deploy_desc": deploy_info["desc"],
                "fidelity": "高 (可靠)" if fidelity_summary.startswith("可用") or "6/6" in fidelity_summary else "降级 (参考)"
            }
        }

        # 1. Local Write (Always for debugging/local history)
        local_path = Path(output_path) if output_path else Path("src/web/public/status.json")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            
        # 2. Production Upload Gating (ADD v3.0 Hardened)
        blob_token = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
        is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
        
        if is_ci:
            if not blob_token:
                # FAIL FAST: In CI, missing credentials is a fatal error that must trigger OOB alerts.
                raise ValueError("CRITICAL FAILURE: VERCEL_BLOB_READ_WRITE_TOKEN is missing in CI environment. Pipeline halted to prevent stale state.")
            
            logger.info("CI Environment detected. Initiating production upload to Vercel Edge...")
            blob_url = "https://blob.vercel-storage.com/status.json"
            
            # VERCEL PROPRIETARY PROTOCOL (Final Surgical Alignment)
            headers = {
                "authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
                "content-type": "application/json; charset=utf-8",
                # MANDATORY: Prevent Vercel from appending random hashes to keep the URL stable
                "x-add-random-suffix": "false",
                # PROPRIETARY CACHE: Vercel REST API specific header for edge TTL
                "x-cache-control-max-age": "3600",
                # VISIBILITY: Explicitly declare the object as publicly accessible
                "x-access": "public"
            }
            
            import time
            start_io = time.time()
            
            # PHYSICAL ENCODING: Force UTF-8 bytes to prevent payload length/encoding mismatches
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            resp = requests.put(blob_url, data=payload_bytes, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                logger.error("Vercel Blob Rejection (%d): %s", resp.status_code, resp.text)
                
            resp.raise_for_status()
            duration = time.time() - start_io
            logger.info("Production snapshot successfully pushed to Vercel Edge (IO: %.2fs).", duration)
        else:
            # Local mode: Graceful skip according to ADD v3.0 Staging Gates policy.
            logger.info("Local mode detected: Skipping cloud upload to protect production integrity.")

        return True

    except Exception as exc:
        logger.error("Web export failed: %s", exc)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # In CI, propagate the error so the workflow fails and notifies the developer.
            raise
        return False

import os
