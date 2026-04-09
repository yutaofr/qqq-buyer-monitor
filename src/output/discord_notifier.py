"""Discord notification logic for QQQ Bayesian Monitor."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time
from typing import TYPE_CHECKING

import requests

from src.regime_topology import ACTIVE_REGIME_ORDER, canonicalize_regime_name, merge_regime_weights
from src.constants import ENGINE_VERSION

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
    "RECOVERY": COLOR_EUPHORIC,
    "LATE_CYCLE": COLOR_STRESS,
}


def _get_regime_emoji(regime: str | None) -> str:
    if regime == "BUST":
        return "🚨"
    if regime == "LATE_CYCLE":
        return "🧯"
    if regime == "RECOVERY":
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
    """Build a Discord payload with full transparency."""
    display_regime = canonicalize_regime_name(result.stable_regime) or result.stable_regime
    color = REGIME_COLORS.get(display_regime, COLOR_DEFAULT)
    macro_emoji = _get_regime_emoji(display_regime)

    metadata = result.metadata or {}
    is_floor_active = bool(metadata.get("is_floor_active", False))
    hydration_anchor = str(metadata.get("hydration_anchor", "2018-01-01"))
    raw_beta_pre_floor = metadata.get("raw_target_beta_pre_floor", result.target_beta)

    deployment_readiness = metadata.get("deployment_readiness", 0.0)
    deployment_state = str(metadata.get("deployment_state", "DEPLOY_BASE"))
    execution_bucket = str(metadata.get("execution_bucket", "n/a"))
    raw_regime = (
        canonicalize_regime_name(metadata.get("raw_regime", display_regime)) or display_regime
    )
    price_topology = dict(metadata.get("price_topology", {}) or {})
    forensic_snapshot_path = metadata.get("forensic_snapshot_path")

    if is_floor_active:
        color = COLOR_STRESS

    probabilities = merge_regime_weights(
        result.probabilities,
        regimes=ACTIVE_REGIME_ORDER,
        include_zeros=False,
    )

    # Check behavioral guard lock
    lock_active = False
    for trace in result.logic_trace:
        if trace.get("step") == "behavioral_guard":
            guard_result = trace.get("result", {})
            lock_active = guard_result.get("lock_active", False)
            execution_bucket = guard_result.get("target_bucket", execution_bucket)

    if lock_active:
        color = COLOR_LOCKED

    # Local definitions for fields to satisfy Ruff F821
    protected_beta = metadata.get("protected_beta", result.target_beta)
    overlay_beta = metadata.get("overlay_beta", result.target_beta)
    overlay_mode = str(metadata.get("overlay_mode", "FULL"))
    beta_overlay_multiplier = metadata.get("beta_overlay_multiplier", 1.0)
    deployment_overlay_multiplier = metadata.get("deployment_overlay_multiplier", 1.0)
    overlay_state = str(metadata.get("overlay_state", "NEUTRAL"))

    title_prefix = "[BETA FLOOR TRIGGERED] " if is_floor_active else ""
    summary_header = (
        f"### {title_prefix}🎯 Target Beta: `{_format_beta(result.target_beta)}`\n"
        f"**Bayesian Regime:** {macro_emoji} `{display_regime}`\n"
        f"**Entropy:** `{result.entropy:.3f}` | **Lock:** `{'🔒 LOCKED' if lock_active else '🔓 ACTIVE'}`"
    )

    if is_floor_active:
        summary_header += f"\n> ⚠️ **Physical Protection Active:** Raw Beta was `{_format_beta(raw_beta_pre_floor)}`"

    description = (
        f"{summary_header}\n\n"
        "> 概率核心决定方向；执行 overlay 只条件化动作，不改写后验。\n\n"
        f"**Briefing:** {result.explanation}"
    )
    title = f"QQQ {ENGINE_VERSION} | Bayesian Decision - {result.date}"

    # Probabilities Distribution
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    prob_str = "\n".join([f"`{k:12}`: `{v:.1%}`" for k, v in sorted_probs])

    fields = [
        {
            "name": f"🔭 Ensemble Implementation Options ({ENGINE_VERSION})",
            "value": (
                f"**Verdict:** `{metadata.get('v14_ensemble_verdict', 'NEUTRAL')}`\n"
                f"1️⃣ **Standard (Official):** `{metadata.get('v14_standard_beta', result.target_beta):.2f}x`\n"
                f"2️⃣ **Protective (S4):** `{metadata.get('v14_s4_protective_beta', 0.5):.2f}x` (0.5 Floor)\n"
                f"3️⃣ **Aggressive (S5):** `{metadata.get('v14_s5_aggressive_beta', result.target_beta):.2f}x` (1.25 Ceiling)\n"
                "> 💡 **Choice is up to the User.** Final decision calibrated via Panorama Ensemble."
            ),
            "inline": False,
        },
        {
            "name": "📊 Posterior Distribution",
            "value": prob_str,
            "inline": False,
        },
        {
            "name": "🛡️ Execution Audit",
            "value": (
                f"**Stable Regime:** `{result.stable_regime}`\n"
                f"**Raw Regime:** `{raw_regime}`\n"
                f"**Bucket:** `{execution_bucket}`\n"
                f"**Deployment:** `{deployment_state}`\n"
                f"**Readiness:** `{deployment_readiness:.1%}`\n"
                f"**Entropy Penalty:** `{result.entropy:.3f}`\n"
                f"**Protected Beta:** `{_format_beta(protected_beta)}`\n"
                f"**Overlay Beta:** `{_format_beta(overlay_beta)}`\n"
                f"**Overlay Mode:** `{overlay_mode}`\n"
                f"**Beta Multiplier:** `{float(beta_overlay_multiplier):.2f}x`\n"
                f"**Pace Multiplier:** `{float(deployment_overlay_multiplier):.2f}x`\n"
                f"**Overlay State:** `{overlay_state}`\n"
                f"**Topology:** `{price_topology.get('regime', 'MID_CYCLE')}` @ `{float(price_topology.get('confidence', 0.0)):.1%}`\n"
                f"**Forensics:** `{'snapshot_saved' if forensic_snapshot_path else 'in_memory_only'}`"
            ),
            "inline": False,
        },
        {
            "name": "🧭 v14 Diagnostic Audit",
            "value": (
                f"**Tractor (SPY Macro):** `{metadata.get('v14_baseline_prob', 0.0):.1%}` | Status: `{metadata.get('v14_baseline_status', 'success')}`\n"
                f"**Sidecar (QQQ Tech):**  `{metadata.get('v14_sidecar_prob', 0.0):.1%}` | Status: `{metadata.get('v14_sidecar_status', 'success')}`"
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
        "footer": {"text": f"{ENGINE_VERSION} Neural-Orthogonal | Prior Anchor: {hydration_anchor}"},
        "timestamp": _discord_timestamp(result.date),
    }

    return {
        "username": "QQQ Monitor AI",
        "avatar_url": "https://raw.githubusercontent.com/yutaofr/qqq-buyer-monitor/main/docs/images/logo?raw=true",
        "embeds": [embed],
    }


def send_discord_signal(result: SignalResult, webhook_url: str) -> bool:
    """Send a Discord embed for the current Bayesian signal."""
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
