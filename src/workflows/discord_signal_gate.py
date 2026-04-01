"""Decision gate for the Discord daily signal workflow."""
from __future__ import annotations

from dataclasses import dataclass

ALLOWED_DISCORD_SIGNAL_SCHEDULES: frozenset[str] = frozenset(
    {
        "47 06 * * 1-5",  # 14:47 Beijing
        "17 15,16 * * 1-5",  # 17:17 Paris (DST aware)
    }
)


@dataclass(frozen=True, slots=True)
class DiscordSignalGateDecision:
    """Structured outcome for the Discord workflow verification gate."""

    should_run: bool
    reason: str


def evaluate_discord_signal_gate(
    *,
    event_name: str | None,
    event_schedule: str | None = None,
) -> DiscordSignalGateDecision:
    """Return whether the Discord signal workflow should proceed.

    The gate is intentionally based on GitHub event metadata rather than the
    runner's wall clock. Manual dispatches always pass. Scheduled runs only pass
    when the cron expression matches one of the approved notification windows.
    """
    normalized_event = str(event_name or "").strip().lower()
    normalized_schedule = str(event_schedule or "").strip()

    if normalized_event == "workflow_dispatch":
        return DiscordSignalGateDecision(True, "manual_dispatch")

    if normalized_event != "schedule":
        return DiscordSignalGateDecision(False, f"unsupported_event:{normalized_event or 'unknown'}")

    if normalized_schedule in ALLOWED_DISCORD_SIGNAL_SCHEDULES:
        return DiscordSignalGateDecision(True, f"matched_schedule:{normalized_schedule}")

    if not normalized_schedule:
        return DiscordSignalGateDecision(False, "missing_schedule_metadata")

    return DiscordSignalGateDecision(False, f"schedule_mismatch:{normalized_schedule}")
