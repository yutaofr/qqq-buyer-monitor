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

# v8.2 Decision Logic Reference (Formula + Explanation)
_LOGIC_CATALOG = {
    # Tier-0 Macro
    "tier0_crisis": {
        "formula": "Spread >= 650 || ERP < 1.0%",
        "explanation": "系统性信用枯竭或风险溢价极度缺失，进入熔断模式。"
    },
    "tier0_rich_tightening": {
        "formula": "Spread >= 450 || ERP < 2.5%",
        "explanation": "估值性价比降低或融资极度收紧，审慎减少敞口。"
    },
    "tier0_transition_stress": {
        "formula": "Credit Stress (Transition)",
        "explanation": "处于信用扩张与收缩的转换期，波动率中枢抬升，需动态防御。"
    },
    "tier0_euphoric": {
        "formula": "Spread < 350 && ERP > 4.5%",
        "explanation": "宏观环境处于极度贪婪后期，估值修复完毕，需预防均值回归。"
    },
    # Risk Controller (Class A stress hierarchy)
    "triple_stress": {
        "formula": "Accel && !Liq && Stress",
        "explanation": "【三重压力并发】信用加速 + 流动性枯竭 + 融资压力同时亮红灯。-> 强制避险 (上限 0.5x)"
    },
    "dual_stress": {
        "formula": "Stress Count >= 2 || Spread >= 600",
        "explanation": "【双重压力并发】触发两项信号或利差触及 600bps 警戒线。-> 强化防御 (上限 0.7x)"
    },
    "single_stress": {
        "formula": "Stress Count == 1 || Spread > 500",
        "explanation": "【单边恶化】满足一项信号或利差 > 500bps。-> 适度减仓 (上限 0.8x)"
    },
    "clean_macro": {
        "formula": "No Stress Signals",
        "explanation": "环境清洁。依据 Tier-0 或信用趋势决定基准 (1.0x) 或 进攻 (1.2x) 状态。"
    },
    "drawdown_budget_breached": {
        "formula": "Drawdown >= 30%",
        "explanation": "触及组合最大回撤预算硬约束。-> 强制避险 (上限 0.5x)"
    },
    # Deployment Controller (DCA Rhythm)
    "tactical_stress_pause": {
        "formula": "Tactical Stress >= 70",
        "explanation": "短线交易情绪过热或结构性失衡，暂停增量入场。"
    },
    "missing_credit_spread_pause": {
        "formula": "Credit Spread Is None",
        "explanation": "底层信用数据缺失，基于审慎原则停止所有交易指令。"
    },
    "deep_drawdown_pause": {
        "formula": "Drawdown >= 25% || Spread >= 650",
        "explanation": "净值深幅回撤或利差进入危机区，停止增量入场以保留余粮。"
    },
    "left_tail_fast": {
        "formula": "Drawdown >= 12% & 20D Return <= -8%",
        "explanation": "【左侧确认】满足大级别回撤补偿逻辑，启动 2.0x 加速抄底。"
    },
    "pullback_fast": {
        "formula": "Drawdown >= 8% & 5D Return <= 0.0%",
        "explanation": "【浅调加速】满足短期回撤补偿条件，利用波动率提升入场节奏。"
    },
    "stress_slow": {
        "formula": "Macro Stress || DD >= 15%",
        "explanation": "受外部环境压力或净值回撤影响，将入场节奏降至 0.5x 以平滑风险。"
    },
    "risk_defense_slow": {
        "formula": "Risk State = DEFENSE",
        "explanation": "跟随风控模块进入防御姿态，自动将增量节奏下调至 0.5x。"
    },
    "risk_reduced_slow": {
        "formula": "Risk State = REDUCED",
        "explanation": "跟随风控模块进入减仓姿态，增量入场同步放缓至 0.5x。"
    },
    "rich_tightening_base": {
        "formula": "T0=RICH && DD < 15%",
        "explanation": "【估值收紧】宏观虽然收紧但暂无实质回撤，维持 1.0x 基准节奏观察。"
    },
    "blood_chip_crisis_override": {
        "formula": "Crisis && Panic && Value",
        "explanation": "【血筹特例】虽然处于危机制度，但战术指标触发极端超卖，开启左侧入场。"
    },
    "risk_ceiling": {
        "formula": "Proposed > Ceiling",
        "explanation": "入场节奏受限于更高的风控等级或宏观顶层约束。"
    },
    "default_base": {
        "formula": "Standard Path",
        "explanation": "无特殊偏差信号，按基准配置计划 1.0x 稳步推进。"
    }
}

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
    if beta <= 1.05: return "90-100% (满仓)"
    return "110-120% (进攻/杠杆)"

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
        
        # Resolve mappings with MUST-HAVE integrity (Fail-Closed)
        regime_key = str(result.tier0_regime)
        deploy_key = result.deployment_action["deploy_mode"]
        
        # Accessing with [] to raise KeyError if missing - system should failure rather than mask
        regime_info = REGIME_MAP[regime_key]
        deploy_info = DEPLOY_MAP[deploy_key]

        # Final Validation of core target beta (AC-3 Data Truthfulness)
        if result.target_beta is None:
            raise ValueError(f"CRITICAL DATA GAP: result.target_beta is None at {now_utc}")

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
                "fidelity": "高 (可靠)"
            },
            "evidence": {
                "risk_state": str(result.risk_state),
                "risk_reasons": result.risk_reasons,
                "deploy_reasons": result.deployment_reasons,
                "factors": {
                    "macro": {
                        "credit_spread": result.feature_values.get("credit_spread"),
                        "erp": result.feature_values.get("erp"),
                        "net_liquidity": result.feature_values.get("net_liquidity"),
                        "liquidity_roc": result.feature_values.get("liquidity_roc"),
                    },
                    "tactical": {
                        "vix": result.feature_values.get("vix"),
                        "fear_greed": result.feature_values.get("fear_greed"),
                        "rolling_drawdown": result.feature_values.get("rolling_drawdown"),
                        "tactical_stress": result.feature_values.get("tactical_stress_score"),
                    }
                },
                "node_traces": []
            }
        }

        # Populate node traces for the Evidence Facts Table
        traces = []
        
        # 1. Tier-0 Node Trace
        t0_reason = next((r for r in result.risk_reasons if "tier0" in r.get("rule", "")), None)
        if t0_reason:
            rule_id = t0_reason["rule"]
            # FAIL FAST: use [] to raise KeyError if rule_id is missing from catalog
            info = _LOGIC_CATALOG[rule_id]
            traces.append({
                "node": "Tier-0 宏观指挥官",
                "trace_type": "MACRO",
                "rule": rule_id,
                "formula": info["formula"],
                "explanation": info["explanation"],
                "result": t0_reason["tier0_regime"]
            })

        # 2. Risk Node Trace
        # Detect if Risk was Vetoed by Tier-0
        is_risk_veto = any("tier0_" in r.get("rule", "") for r in result.risk_reasons)
        risk_reason = next((r for r in result.risk_reasons if ("tier0_" not in r.get("rule", "") or not is_risk_veto)), None)
        if not risk_reason and result.risk_reasons:
            risk_reason = result.risk_reasons[0]
        
        if risk_reason:
            rule_id = risk_reason["rule"]
            # FAIL FAST
            info = _LOGIC_CATALOG[rule_id]
            formula = info["formula"]
            explanation = info["explanation"]
            
            if is_risk_veto:
                formula = f"[VETO] Inherit Tier-0 ({result.tier0_regime})"
                explanation = f"受顶层宏观制度 ({result.tier0_regime}) 强约束，Risk 节点强制进入防御模式。"

            traces.append({
                "node": "Risk 风险控制器",
                "trace_type": "VETO" if is_risk_veto else "SIGNAL",
                "rule": rule_id,
                "formula": formula,
                "explanation": explanation,
                "result": str(result.risk_state).split(".")[-1]
            })

        # 3. Deployment Node Trace
        deploy_reason = result.deployment_reasons[0] if result.deployment_reasons else None
        if deploy_reason:
            rule_id = deploy_reason["rule"]
            is_deploy_veto = ("ceiling" in rule_id)
            # FAIL FAST
            info = _LOGIC_CATALOG[rule_id]
            formula = info["formula"]
            explanation = info["explanation"]
            
            if is_deploy_veto:
                formula = "[VETO] Risk/Macro Ceiling"
                explanation = "入场节奏受限于更高的风控等级或宏观顶层约束，进入保值模式。"

            traces.append({
                "node": "Deploy 部署引擎",
                "trace_type": "VETO" if is_deploy_veto else "TACTICAL",
                "rule": rule_id,
                "formula": formula,
                "explanation": explanation,
                "result": deploy_info["label"]
            })
        
        payload["evidence"]["node_traces"] = traces

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
