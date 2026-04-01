from src.workflows.discord_signal_gate import (
    ALLOWED_DISCORD_SIGNAL_SCHEDULES,
    DiscordSignalGateDecision,
    evaluate_discord_signal_gate,
)


def test_manual_dispatch_always_runs():
    decision = evaluate_discord_signal_gate(event_name="workflow_dispatch")

    assert isinstance(decision, DiscordSignalGateDecision)
    assert decision.should_run is True
    assert decision.reason == "manual_dispatch"


def test_allowed_schedule_runs():
    for schedule in ALLOWED_DISCORD_SIGNAL_SCHEDULES:
        decision = evaluate_discord_signal_gate(event_name="schedule", event_schedule=schedule)
        assert decision.should_run is True
        assert decision.reason == f"matched_schedule:{schedule}"


def test_schedule_mismatch_is_rejected():
    decision = evaluate_discord_signal_gate(event_name="schedule", event_schedule="0 0 * * *")

    assert decision.should_run is False
    assert decision.reason == "schedule_mismatch:0 0 * * *"


def test_non_schedule_event_is_rejected():
    decision = evaluate_discord_signal_gate(event_name="push", event_schedule="47 06 * * 1-5")

    assert decision.should_run is False
    assert decision.reason == "unsupported_event:push"
