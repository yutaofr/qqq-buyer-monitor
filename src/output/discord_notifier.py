"""Discord notification logic for QQQ v11.5 Bayesian Monitor."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from src.models import SignalResult

logger = logging.getLogger(__name__)

# Discord Color Constants
COLOR_NEUTRAL = 0x3498DB
COLOR_CRISIS = 0x992D22
COLOR_EUPHORIC = 0x2ECC71
COLOR_LOCKED = 0x7289DA
COLOR_DEFAULT = 0x95A5A6
COLOR_STRESS = 0xE67E22

REGIME_COLORS = {
    "MID_CYCLE": COLOR_NEUTRAL,
    "BUST": COLOR_CRISIS,
    "CAPITULATION": COLOR_EUPHORIC,
    "RECOVERY": COLOR_EUPHORIC,
    "LATE_CYCLE": COLOR_STRESS,
}


def _get_regime_emoji(regime: str | None) -> str:
    if regime == "BUST":
        return "🚨"
    if regime == "LATE_CYCLE":
        return "🧯"
    if regime in ["CAPITULATION", "RECOVERY"]:
        return "💎"
    return "⚖️"


def _format_beta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _discord_timestamp(value: object) -> str:
    """Return an RFC3339 timestamp that Discord accepts for embeds."""
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

    if isinstance(value, date):
        dt = datetime.combine(value, time(16, 17), tzinfo=UTC)
        return dt.isoformat().replace("+00:00", "Z")

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_discord_payload(result: SignalResult) -> dict:
    """Build a Discord payload for v11 probabilistic signals."""
    display_regime = result.stable_regime
    color = REGIME_COLORS.get(display_regime, COLOR_DEFAULT)
    macro_emoji = _get_regime_emoji(display_regime)

    metadata = result.metadata or {}
    deployment_readiness = metadata.get("deployment_readiness", 0.0)
    
    # Check behavioral guard lock in logic trace or metadata if available
    lock_active = False
    target_bucket = "n/a"
    for trace in result.logic_trace:
        if trace.get("step") == "behavioral_guard":
            guard_result = trace.get("result", {})
            lock_active = guard_result.get("lock_active", False)
            target_bucket = guard_result.get("target_bucket", "n/a")

    if lock_active:
        color = COLOR_LOCKED

    summary_header = (
        f"### 🎯 Target Beta: `{_format_beta(result.target_beta)}`\n"
        f"**Bayesian Regime:** {macro_emoji} `{display_regime}`\n"
        f"**Entropy:** `{result.entropy:.3f}` | **Lock:** `{'🔒 LOCKED' if lock_active else '🔓 ACTIVE'}`"
    )

    description = (
        f"{summary_header}\n\n"
        "> v11.5 概率优先连续建议；后验决定方向，信息熵惩罚控制缩放，行为守卫负责离散执行。\n\n"
        f"**Briefing:** {result.explanation}"
    )

    title = f"QQQ V11.5 | Bayesian Decision - {result.date}"

    # Probabilities Distribution
    sorted_probs = sorted(result.probabilities.items(), key=lambda x: x[1], reverse=True)
    prob_str = "\n".join([f"`{k:12}`: `{v:.1%}`" for k, v in sorted_probs])
    
    fields = [
        {
            "name": "📊 Posterior Distribution",
            "value": prob_str,
            "inline": False,
        },
        {
            "name": "🛡️ Execution Audit",
            "value": (
                f"**Bucket:** `{target_bucket}`\n"
                f"**Readiness:** `{deployment_readiness:.1%}`\n"
                f"**Entropy Penalty:** `{result.entropy:.3f}`"
            ),
            "inline": False,
        },
        {
            "name": "📎 Reference Allocation",
            "value": (
                f"QQQ={result.target_allocation.target_qqq_pct * 100:.1f}% | "
                f"QLD={result.target_allocation.target_qld_pct * 100:.1f}% | "
                f"Cash={result.target_allocation.target_cash_pct * 100:.1f}%"
            ),
            "inline": False,
        },
        {
            "name": "💰 Price",
            "value": f"`${result.price:,.2f}`",
            "inline": True,
        },
    ]

    embed = {
        "title": title[:256],
        "description": description[:4096],
        "color": int(color),
        "fields": fields,
        "footer": {"text": "Bayesian-Core v11.5 | Numerical Integrity Verified"},
        "timestamp": _discord_timestamp(result.date),
    }

    return {
        "username": "QQQ Monitor AI",
        "avatar_url": "https://raw.githubusercontent.com/yutaofr/qqq-buyer-monitor/main/docs/images/logo?raw=true",
        "embeds": [embed],
    }


def send_discord_signal(result: SignalResult, webhook_url: str) -> bool:
    """Send a Discord embed for the v11.5 Bayesian signal."""
    if not webhook_url:
        return False

    payload = build_discord_payload(result)
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        return False
