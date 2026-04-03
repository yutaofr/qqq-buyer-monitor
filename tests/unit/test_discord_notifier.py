"""Unit tests for the v12.0 Bayesian Discord notifier."""
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
        priors={"MID_CYCLE": 0.50, "LATE_CYCLE": 0.50, "BUST": 0.00},
        entropy=0.17,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.10, 0.90, 0.0, 0.90),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="v12.0 Bayesian Conductor: beta=0.91x | entropy=0.170 | regime=MID_CYCLE (82.0%)",
        metadata={
            "deployment_readiness": 0.64,
            "protected_beta": 0.94,
            "overlay_beta": 0.91,
            "overlay_mode": "NEGATIVE_ONLY",
            "beta_overlay_multiplier": 0.97,
            "deployment_overlay_multiplier": 1.06,
            "overlay_state": "REWARD",
        }
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
    assert "QQQ" in embed["title"]
    assert "🎯 Target Beta: `0.91x`" in embed["description"]
    assert "Bayesian Regime:** ⚖️ `MID_CYCLE`" in embed["description"]
    assert "Entropy:** `0.170`" in embed["description"]

    # Check fields
    field_names = [f["name"] for f in embed["fields"]]
    assert "📊 Posterior Distribution" in field_names
    assert "🛡️ Execution Audit" in field_names
    assert "📎 Reference Allocation" in field_names
    execution_field = next(field for field in embed["fields"] if field["name"] == "🛡️ Execution Audit")
    assert "Overlay Mode" in execution_field["value"]
    assert "Protected Beta" in execution_field["value"]
    assert "Overlay Beta" in execution_field["value"]
    assert "Pace Multiplier" in execution_field["value"]
