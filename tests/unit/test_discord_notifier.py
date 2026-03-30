from __future__ import annotations

from datetime import date

from src.models import (
    Signal,
    SignalDetail,
    SignalResult,
    TargetAllocationState,
    Tier1Result,
    Tier2Result,
)
from src.models.deployment import DeploymentState
from src.models.risk import RiskState
from src.output.cli import build_runtime_logic_trace, build_v8_explanation
from src.output.discord_notifier import send_discord_signal


def _detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _runtime_result() -> SignalResult:
    t1 = Tier1Result(
        score=50,
        drawdown_52w=_detail("dd"),
        ma200_deviation=_detail("ma"),
        vix=_detail("vix"),
        fear_greed=_detail("fg"),
        breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "yf", 0, 0)
    result = SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        signal=Signal.WATCH,
        final_score=110,
        tier1=t1,
        tier2=t2,
        explanation="placeholder",
        target_allocation=TargetAllocationState(0.60, 0.30, 0.10, 0.50),
        confidence="high",
        data_quality={
            "credit_spread": {"usable": True},
            "erp": {"usable": True},
            "vix": {"usable": True},
        },
    )
    result.cycle_regime = "LATE_CYCLE"
    result.tier0_regime = "RICH_TIGHTENING"
    result.risk_state = RiskState.RISK_REDUCED
    result.deployment_state = DeploymentState.DEPLOY_BASE
    result.selected_candidate_id = "reduced-limited-001"
    result.registry_version = "2026-03-24-v7.0-r1"
    result.raw_target_beta = 0.80
    result.target_beta = 0.50
    result.target_exposure_ceiling = 0.80
    result.target_cash_floor = 0.20
    result.qld_share_ceiling = 0.10
    result.should_adjust = False
    result.rebalance_action = {"reason": "upshift_confirmation"}
    result.deployment_action = {
        "deploy_mode": "BASE",
        "reason": "rich_tightening_base",
        "path": "qqq_only_new_cash",
    }
    result.risk_reasons = [{"rule": "single_stress", "tier0_regime": "RICH_TIGHTENING"}]
    result.cycle_reasons = [{"rule": "late_cycle"}]
    result.deployment_reasons = [{"rule": "rich_tightening_base", "path": "qqq_only_new_cash"}]
    result.feature_values = {
        "credit_spread": 321.0,
        "erp": 2.02,
        "price_vs_ma200": -0.03,
        "net_liquidity": 5818.97,
        "liquidity_roc": 0.78,
        "vix": 31.1,
        "fear_greed": 10.0,
        "rolling_drawdown": 0.113,
        "tactical_stress_score": 52,
    }
    result.v11_probabilities = {"MID_CYCLE": 0.8, "BUST": 0.2}
    result.v11_entropy = 0.3
    result.v11_execution = {"target_bucket": "QQQ", "lock_active": False}
    result.engine_version = "v11"
    result.logic_trace = build_runtime_logic_trace(result)
    result.explanation = build_v8_explanation(result)
    return result


def test_discord_notification_uses_v11_contract(monkeypatch):
    captured: dict = {}

    class _Response:
        status_code = 204
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("src.output.discord_notifier.requests.post", fake_post)

    ok = send_discord_signal(_runtime_result(), "https://example.test/webhook")

    assert ok is True
    embed = captured["json"]["embeds"][0]
    assert captured["url"] == "https://example.test/webhook"
    assert "V11" in embed["title"]
    assert "🎯 Target Beta" in embed["description"]

    # Check summary header
    assert "**Incremental Pacing:** 🏠 `DEPLOY_BASE`" in embed["description"]

    field_names = [field["name"] for field in embed["fields"]]
    assert "🧭 Detailed Decision Path" in field_names
    assert "📎 Reference Allocation" in field_names
    assert "🛡️ Execution Audit" in field_names

    decision_value = next(field["value"] for field in embed["fields"] if field["name"] == "🧭 Detailed Decision Path")
    reference_value = next(field["value"] for field in embed["fields"] if field["name"] == "📎 Reference Allocation")
    audit_value = next(field["value"] for field in embed["fields"] if field["name"] == "🛡️ Execution Audit")

    # Check decision path
    assert "Posterior Regime:** `RICH_TIGHTENING`" in decision_value
    assert "Entropy Penalty:** `0.300`" in decision_value
    assert "Beta Advisory:** `0.80x` → **`0.50x`**" in decision_value
    assert "Execution Guard:** `QQQ` (🔓 **ACTIVE**)" in decision_value
    assert "增量资金入场节奏:** 🏠 `DEPLOY_BASE`" in decision_value

    # Check execution audit
    assert "增量资金节奏:** 🏠 `DEPLOY_BASE`" in audit_value

    assert "non-binding" in reference_value
    assert "QQQ=30.0%" in reference_value


def test_discord_notification_uses_v10_contract(monkeypatch):
    captured: dict = {}

    class _Response:
        status_code = 204
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("src.output.discord_notifier.requests.post", fake_post)

    result = _runtime_result()
    result.engine_version = "v10"
    result.deployment_state = DeploymentState.DEPLOY_FAST

    ok = send_discord_signal(result, "https://example.test/webhook")

    assert ok is True
    embed = captured["json"]["embeds"][0]
    assert "V10" in embed["title"]

    # Check summary header
    assert "**Incremental Pacing:** 🚀 `DEPLOY_FAST`" in embed["description"]

    field_names = [field["name"] for field in embed["fields"]]
    assert "🛡️ Technical Execution Audit" in field_names
    assert "🧭 Detailed Decision Path" in field_names

    audit_value = next(field["value"] for field in embed["fields"] if field["name"] == "🛡️ Technical Execution Audit")
    decision_value = next(field["value"] for field in embed["fields"] if field["name"] == "🧭 Detailed Decision Path")

    assert "增量资金节奏:** 🚀 `DEPLOY_FAST`" in audit_value
    assert "增量资金入场节奏:** 🚀 `DEPLOY_FAST`" in decision_value


def test_discord_notification_pacing_fallback(monkeypatch):
    captured: dict = {}

    class _Response:
        status_code = 204
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("src.output.discord_notifier.requests.post", fake_post)

    result = _runtime_result()
    result.deployment_state = None
    result.deployment_action = {"deploy_mode": "SLOW"}

    ok = send_discord_signal(result, "https://example.test/webhook")

    assert ok is True
    embed = captured["json"]["embeds"][0]
    assert "**Incremental Pacing:** 🐢 `DEPLOY_SLOW`" in embed["description"]
