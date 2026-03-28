"""Discord notification logic for QQQ Monitor signals."""
from __future__ import annotations

import logging
import os
import requests
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import SignalResult

logger = logging.getLogger(__name__)

# Discord Color Constants (HEX to INT)
COLOR_CRISIS = 0x992D22          # Dark Red
COLOR_TRANSITION_STRESS = 0xE67E22 # Orange
COLOR_RICH_TIGHTENING = 0xF1C40F  # Yellow/Gold
COLOR_NEUTRAL = 0x3498DB         # Blue
COLOR_EUPHORIC = 0x2ECC71        # Green
COLOR_DEFAULT = 0x95A5A6         # Grey

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

def send_discord_signal(result: SignalResult, webhook_url: str) -> bool:
    """
    Send a high-fidelity Discord Embed with the current signal result.
    """
    if not webhook_url:
        logger.warning("No Discord webhook URL provided, skipping notification.")
        return False

    regime = result.tier0_regime or "NEUTRAL"
    color = REGIME_COLORS.get(regime, COLOR_DEFAULT)
    emoji = _get_regime_emoji(regime)
    
    # Portfolio display
    t = result.target_allocation
    portfolio_str = (
        f"**QQQ:** `{t.target_qqq_pct*100:.1f}%` | "
        f"**QLD:** `{t.target_qld_pct*100:.1f}%` | "
        f"**Cash:** `{t.target_cash_pct*100:.1f}%`"
    )

    # Risk & Deployment
    risk_state = result.risk_state.value if result.risk_state else "NORMAL"
    deploy_mode = result.deployment_action.get("deploy_mode", "BASE")
    
    # Embed Structure
    embed = {
        "title": f"QQQ Monitor v8.2 | Signal Report - {result.date}",
        "description": f"**Market Regime:** {emoji} `{regime}`\n\n> {result.explanation}",
        "color": color,
        "fields": [
            {
                "name": "🎯 Target Beta",
                "value": f"`{result.target_beta:.2f}x`",
                "inline": True
            },
            {
                "name": "🛡️ Risk State",
                "value": f"`{risk_state}`",
                "inline": True
            },
            {
                "name": "🚀 Entry Pace",
                "value": f"`{deploy_mode}`",
                "inline": True
            },
            {
                "name": "📊 Recommended Portfolio",
                "value": portfolio_str,
                "inline": False
            },
            {
                "name": "💰 Current Price",
                "value": f"`${result.price:,.2f}`",
                "inline": True
            },
            {
                "name": "📈 Signal Score",
                "value": f"`{result.final_score}/100`",
                "inline": True
            }
        ],
        "footer": {
            "text": f"Precision Decision Engine | Registry: {result.registry_version or 'v8.2'} | Confidence: {result.confidence.upper()}"
        },
        "timestamp": f"{result.date}T16:17:00Z" # Approximate push time
    }

    payload = {
        "username": "QQQ Monitor AI",
        "avatar_url": "https://raw.githubusercontent.com/yutaofr/qqq-buyer-monitor/main/docs/images/logo?raw=true", # Fallback if exists
        "embeds": [embed]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Successfully sent signal to Discord.")
        return True
    except Exception as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        return False
