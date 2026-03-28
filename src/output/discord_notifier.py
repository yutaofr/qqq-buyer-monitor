"""Discord notification logic for v9 target-beta-first runtime signals."""
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
COLOR_DEFAULT = 0x95A5A6

REGIME_COLORS = {
    "CRISIS": COLOR_CRISIS,
    "TRANSITION_STRESS": COLOR_TRANSITION_STRESS,
    "RICH_TIGHTENING": COLOR_RICH_TIGHTENING,
    "NEUTRAL": COLOR_NEUTRAL,
    "EUPHORIC": COLOR_EUPHORIC,
}


def _get_regime_emoji(regime: str | None) -> str:
    if regime == "CRISIS":
        return "🚨"
    if regime == "TRANSITION_STRESS":
        return "🧯"
    if regime == "RICH_TIGHTENING":
        return "🛡️"
    if regime == "EUPHORIC":
        return "💎"
    return "⚖️"


def _format_beta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _build_decision_path(result: SignalResult) -> str:
    raw_beta = result.raw_target_beta if result.raw_target_beta is not None else result.target_beta
    risk_state = result.risk_state.value if result.risk_state else "n/a"
    deploy_state = result.deployment_state.value if result.deployment_state else "n/a"
    return (
        f"Tier-0({result.tier0_regime or 'n/a'}) -> "
        f"Risk({risk_state}, beta<={_format_beta(result.target_exposure_ceiling)}, "
        f"qld<={_format_pct(result.qld_share_ceiling)}) -> "
        f"Candidate({result.selected_candidate_id or 'n/a'}) -> "
        f"Advisory({_format_beta(raw_beta)}->{_format_beta(result.target_beta)}) -> "
        f"Deployment({deploy_state})"
    )


def _build_reference_path(result: SignalResult) -> str:
    target = result.target_allocation
    return (
        f"QQQ={target.target_qqq_pct * 100:.1f}% | "
        f"QLD={target.target_qld_pct * 100:.1f}% | "
        f"Cash={target.target_cash_pct * 100:.1f}% "
        "(non-binding reference path)"
    )


def build_discord_payload(result: SignalResult) -> dict:
    """Build a Discord payload that matches the v9 decision contract."""
    regime = result.tier0_regime or "NEUTRAL"
    color = REGIME_COLORS.get(regime, COLOR_DEFAULT)
    emoji = _get_regime_emoji(regime)
    risk_state = result.risk_state.value if result.risk_state else "n/a"
    deploy_state = result.deployment_state.value if result.deployment_state else "n/a"
    contract_desc = (
        "**Decision Contract:** `target_beta`\n"
        "系统输出的是目标 Beta 信号；用户自行决定资产配置比例，参考路径仅用于说明一种实现方式。"
    )
    description = f"{contract_desc}\n\n> {result.explanation}"

    embed = {
        "title": f"QQQ Monitor v9.0 | Target-Beta Signal - {result.date}",
        "description": f"**Market Regime:** {emoji} `{regime}`\n\n{description}",
        "color": color,
        "fields": [
            {
                "name": "🎯 Target Beta Contract",
                "value": f"`{_format_beta(result.target_beta)}`",
                "inline": True,
            },
            {
                "name": "🛡️ Risk Gate",
                "value": (
                    f"`{risk_state}`\n"
                    f"`beta<={_format_beta(result.target_exposure_ceiling)} | "
                    f"qld<={_format_pct(result.qld_share_ceiling)}`"
                ),
                "inline": True,
            },
            {
                "name": "🚀 New Cash Pace",
                "value": f"`{deploy_state}`\n`QQQ-only new cash`",
                "inline": True,
            },
            {
                "name": "🧪 Candidate",
                "value": f"`{result.selected_candidate_id or 'n/a'}`",
                "inline": True,
            },
            {
                "name": "🧭 Decision Path",
                "value": _build_decision_path(result),
                "inline": False,
            },
            {
                "name": "📎 Reference Path",
                "value": _build_reference_path(result),
                "inline": False,
            },
            {
                "name": "💰 Current Price",
                "value": f"`${result.price:,.2f}`",
                "inline": True,
            },
            {
                "name": "📈 Signal Score",
                "value": f"`{result.final_score}/100`",
                "inline": True,
            },
        ],
        "footer": {
            "text": (
                "Target-Beta-First | "
                f"Registry: {result.registry_version or 'n/a'} | "
                f"Confidence: {result.confidence.upper()}"
            )
        },
        "timestamp": f"{result.date}T16:17:00Z",
    }

    return {
        "username": "QQQ Monitor AI",
        "avatar_url": (
            "https://raw.githubusercontent.com/yutaofr/qqq-buyer-monitor/main/docs/images/logo?raw=true"
        ),
        "embeds": [embed],
    }


def send_discord_signal(result: SignalResult, webhook_url: str) -> bool:
    """Send a Discord embed aligned with the v9 runtime decision contract."""
    if not webhook_url:
        logger.warning("No Discord webhook URL provided, skipping notification.")
        return False

    payload = build_discord_payload(result)

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Successfully sent signal to Discord.")
        return True
    except Exception as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        return False
