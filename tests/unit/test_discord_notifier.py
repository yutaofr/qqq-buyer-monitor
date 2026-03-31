"""Unit tests for the v11.5 Bayesian Discord notifier."""
from __future__ import annotations

from datetime import date

from src.models import SignalResult, TargetAllocationState
from src.output.discord_notifier import send_discord_signal


def _v11_result() -> SignalResult:
    return SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        target_beta=0.91,
        probabilities={"MID_CYCLE": 0.82, "LATE_CYCLE": 0.15, "BUST": 0.03},
        entropy=0.17,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.10, 0.90, 0.0, 0.90),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="v11.5 Bayesian Conductor: beta=0.91x | entropy=0.170 | regime=MID_CYCLE (82.0%)",
        metadata={"deployment_readiness": 0.64}
    )


def test_discord_notification_uses_v11_contract(monkeypatch):
    captured: dict = {}

    class _Response:
        status_code = 204
        def raise_for_status(self) -> None: return None

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _Response()

    monkeypatch.setattr("src.output.discord_notifier.requests.post", fake_post)

    ok = send_discord_signal(_v11_result(), "https://example.test/webhook")

    assert ok is True
    embed = captured["json"]["embeds"][0]
    assert "V11.5" in embed["title"]
    assert "🎯 Target Beta: `0.91x`" in embed["description"]
    assert "Bayesian Regime:** ⚖️ `MID_CYCLE`" in embed["description"]
    assert "Entropy:** `0.170`" in embed["description"]

    # Check fields
    field_names = [f["name"] for f in embed["fields"]]
    assert "📊 Posterior Distribution" in field_names
    assert "🛡️ Execution Audit" in field_names
    assert "📎 Reference Allocation" in field_names
