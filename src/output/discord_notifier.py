"""Discord notification logic for v10 cycle-aware runtime signals."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from src.models import SignalResult

logger = logging.getLogger(__name__)

# Discord Color Constants (HEX to INT)
COLOR_CRISIS = 0x992D22
COLOR_TRANSITION_STRESS = 0xE67E22
COLOR_RICH_TIGHTENING = 0xF1C40F
COLOR_NEUTRAL = 0x3498DB
COLOR_EUPHORIC = 0x2ECC71
COLOR_LOCKED = 0x7289DA  # Discord Blurple for locks
COLOR_DEFAULT = 0x95A5A6

REGIME_COLORS = {
    "CRISIS": COLOR_CRISIS,
    "TRANSITION_STRESS": COLOR_TRANSITION_STRESS,
    "RICH_TIGHTENING": COLOR_RICH_TIGHTENING,
    "NEUTRAL": COLOR_NEUTRAL,
    "EUPHORIC": COLOR_EUPHORIC,
    # v11 Bayesian Posteriors
    "MID_CYCLE": COLOR_NEUTRAL,
    "BUST": COLOR_CRISIS,
    "CAPITULATION": COLOR_EUPHORIC,
    "RECOVERY": COLOR_EUPHORIC,
    "LATE_CYCLE": COLOR_TRANSITION_STRESS,
}


def _get_regime_emoji(regime: str | None) -> str:
    if regime in ["CRISIS", "BUST"]:
        return "🚨"
    if regime in ["TRANSITION_STRESS", "LATE_CYCLE"]:
        return "🧯"
    if regime in ["RICH_TIGHTENING", "REDUCED"]:
        return "🛡️"
    if regime in ["EUPHORIC", "CAPITULATION", "RECOVERY"]:
        return "💎"
    return "⚖️"


def _get_deployment_emoji(state: str | None) -> str:
    if not state:
        return "❓"
    if "FAST" in state:
        return "🚀"
    if "BASE" in state:
        return "🏠"
    if "SLOW" in state:
        return "🐢"
    if "PAUSE" in state:
        return "⏸️"
    if "RECOVER" in state:
        return "🩹"
    return "🔘"


def _format_beta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _build_v11_decision_path(result: SignalResult) -> str:
    execution = result.v11_execution
    lock_status = "🔒 **LOCKED**" if execution.get("lock_active") else "🔓 **ACTIVE**"
    deploy_state = _get_deployment_state_str(result)
    deploy_emoji = _get_deployment_emoji(deploy_state)
    
    return (
        f"🔘 **Posterior Regime:** `{result.tier0_regime or 'n/a'}`\n"
        f"↳ **Entropy Penalty:** `{result.v11_entropy:.3f}`\n"
        f"↳ **Beta Advisory:** `{_format_beta(result.raw_target_beta)}` → **`{_format_beta(result.target_beta)}`**\n"
        f"↳ **Execution Guard:** `{execution.get('target_bucket', 'n/a')}` ({lock_status})\n"
        f"↳ **增量资金入场节奏:** {deploy_emoji} `{deploy_state}`\n"
        f"↳ **Lock Reason:** `{execution.get('reason', 'n/a')}`"
    )


def _build_decision_path(result: SignalResult) -> str:
    if result.engine_version == "v11":
        return _build_v11_decision_path(result)
        
    raw_beta = result.raw_target_beta if result.raw_target_beta is not None else result.target_beta
    risk_state = result.risk_state.value if result.risk_state else "n/a"
    deploy_state = _get_deployment_state_str(result)
    deploy_emoji = _get_deployment_emoji(deploy_state)
    return (
        f"🔘 **Tier-0 (Macro):** `{result.tier0_regime or 'n/a'}`\n"
        f"↳ **Cycle (Tactical):** `{result.cycle_regime or 'n/a'}`\n"
        f"↳ **Risk Gate:** `{risk_state} (beta<={_format_beta(result.target_exposure_ceiling)})`\n"
        f"↳ **Candidate Selection:** `{result.selected_candidate_id or 'n/a'}`\n"
        f"↳ **Beta Advisory:** `{_format_beta(raw_beta)}` → **`{_format_beta(result.target_beta)}`**\n"
        f"↳ **增量资金入场节奏:** {deploy_emoji} `{deploy_state}`"
    )


def _build_reference_path(result: SignalResult) -> str:
    target = result.target_allocation
    return (
        f"QQQ={target.target_qqq_pct * 100:.1f}% | "
        f"QLD={target.target_qld_pct * 100:.1f}% | "
        f"Cash={target.target_cash_pct * 100:.1f}% "
        "(non-binding reference path)"
    )


def _get_deployment_state_str(result: SignalResult) -> str:
    if result.deployment_state:
        return result.deployment_state.value
    
    # Fallback to deployment_action dict (common in some runtime paths)
    mode = result.deployment_action.get("deploy_mode")
    if mode:
        return f"DEPLOY_{mode}"
    
    return "n/a"


def build_discord_payload(result: SignalResult) -> dict:
    """Build a Discord payload that matches the v10/v11 decision contract."""
    is_v11 = result.engine_version == "v11"
    
    macro_regime = result.tier0_regime or "NEUTRAL"
    color = REGIME_COLORS.get(macro_regime, COLOR_DEFAULT)
    macro_emoji = _get_regime_emoji(macro_regime)
    
    execution = result.v11_execution if is_v11 else {}
    lock_active = execution.get("lock_active", False)
    if lock_active:
        color = COLOR_LOCKED

    deploy_state = _get_deployment_state_str(result)
    deploy_emoji = _get_deployment_emoji(deploy_state)

    # MOBILE OPTIMIZED SUMMARY
    if is_v11:
        summary_header = (
            f"### 🎯 Target Beta: `{_format_beta(result.target_beta)}`\n"
            f"**Bayesian Regime:** {macro_emoji} `{macro_regime}`\n"
            f"**Incremental Pacing:** {deploy_emoji} `{deploy_state}`\n"
            f"**Entropy:** `{result.v11_entropy:.3f}` | **Lock:** `{'🔒 LOCKED' if lock_active else '🔓 ACTIVE'}`"
        )
    else:
        cycle_regime = result.cycle_regime or "NEUTRAL"
        cycle_emoji = _get_regime_emoji(cycle_regime)
        summary_header = (
            f"### 🎯 Target Beta: `{_format_beta(result.target_beta)}`\n"
            f"**Macro Regime:** {macro_emoji} `{macro_regime}`\n"
            f"**Tactical Cycle:** {cycle_emoji} `{cycle_regime}`\n"
            f"**Incremental Pacing:** {deploy_emoji} `{deploy_state}`"
        )

    contract_desc = (
        "> v11 概率优先连续建议；后验决定方向，信息熵惩罚控制缩放，行为守卫负责离散执行。" if is_v11 else
        "> 系统输出目标 Beta 信号；用户自行决定资产配置比例，参考路径不具备强制约束力。"
    )
    description = f"{summary_header}\n\n{contract_desc}\n\n**Briefing:** {result.explanation}"

    title = f"QQQ {result.engine_version.upper()} | Runtime Decision - {result.date}"
    
    fields = []
    if is_v11:
        # Probabilities Distribution
        sorted_probs = sorted(result.v11_probabilities.items(), key=lambda x: x[1], reverse=True)
        prob_str = "\n".join([f"`{k:12}`: `{v:.1%}`" for k, v in sorted_probs])
        fields.append({
            "name": "📊 Posterior Distribution",
            "value": prob_str,
            "inline": False,
        })
        
        fields.append({
            "name": "🛡️ Execution Audit",
            "value": (
                f"**Bucket:** `{execution.get('target_bucket', 'n/a')}`\n"
                f"**Action:** `{result.should_adjust}`\n"
                f"**增量资金节奏:** {deploy_emoji} `{deploy_state}`\n"
                f"**Lock Reason:** `{execution.get('reason', 'n/a')}`"
            ),
            "inline": False,
        })
    else:
        risk_state = result.risk_state.value if result.risk_state else "n/a"
        fields.append({
            "name": "🛡️ Technical Execution Audit",
            "value": (
                f"**Risk Gate:** `{risk_state}`\n"
                f"**增量资金节奏:** {deploy_emoji} `{deploy_state}`\n"
                f"**Candidate:** `{result.selected_candidate_id or 'n/a'}`"
            ),
            "inline": False,
        })

    fields.extend([
        {
            "name": "🧭 Detailed Decision Path",
            "value": _build_decision_path(result),
            "inline": False,
        },
        {
            "name": "📎 Reference Allocation",
            "value": f"`{_build_reference_path(result)}`",
            "inline": False,
        },
        {
            "name": "💰 Price",
            "value": f"`${result.price:,.2f}`",
            "inline": True,
        },
        {
            "name": "📈 Score",
            "value": f"`{result.final_score}/100`",
            "inline": True,
        },
    ])

    # Format date to string if it's a timestamp object
    try:
        if hasattr(result.date, "isoformat"):
            # If it's a datetime/timestamp object, use its isoformat
            iso_timestamp = result.date.isoformat()
            if "Z" not in iso_timestamp and "+" not in iso_timestamp:
                iso_timestamp += "Z"
        else:
            # Fallback for string dates
            date_str = str(result.date)[:10]
            iso_timestamp = f"{date_str}T16:17:00Z"
    except Exception:
        import datetime
        iso_timestamp = datetime.datetime.now().isoformat() + "Z"

    # Sanitize fields: Discord rejects empty strings or nulls in field values
    for field in fields:
        if not field.get("value"):
            field["value"] = "n/a"
        if not field.get("name"):
            field["name"] = "-"

    embed = {
        "title": str(title)[:256],
        "description": str(description)[:4096],
        "color": int(color),
        "fields": fields[:25],  # Discord limit: 25 fields
        "footer": {
            "text": str(
                f"{'Bayesian-Core' if is_v11 else 'Target-Beta-First'} | "
                f"Registry: {result.registry_version or ('v11_static' if is_v11 else 'n/a')} | "
                f"Quality: {result.v11_quality_audit.get('quality_score', 1.0) if is_v11 else 'HIGH'}"
            )[:2048]
        },
        "timestamp": iso_timestamp,
    }

    return {
        "username": "QQQ Monitor AI",
        "avatar_url": (
            "https://raw.githubusercontent.com/yutaofr/qqq-buyer-monitor/main/docs/images/logo?raw=true"
        ),
        "embeds": [embed],
    }


def send_discord_signal(result: SignalResult, webhook_url: str) -> bool:
    """Send a Discord embed aligned with the v10/v11 runtime decision contract."""
    if not webhook_url:
        logger.warning("No Discord webhook URL provided, skipping notification.")
        return False

    payload = build_discord_payload(result)

    try:
        import json
        logger.debug("Discord Payload: %s", json.dumps(payload, indent=2))
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 204:  # Discord returns 204 No Content on success
            resp.raise_for_status()
        logger.info("Successfully sent signal to Discord.")
        return True
    except Exception as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        # Log response content for 400 errors
        if hasattr(exc, "response") and exc.response is not None:
            logger.error("Discord Error Response: %s", exc.response.text)
        return False
